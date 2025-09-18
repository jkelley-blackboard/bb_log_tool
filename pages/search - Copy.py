# pages/search.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List
import streamlit as st
import pandas as pd

from modules.parser_utils import LOG_FIELDS, get_log_fields
from modules.search_utils import (
    normalize_dir,
    list_first_level_subdirs,
    validate_conversion_run_dir,
    build_type_inventory,
    filter_converted_files_by_type_and_dir,
    create_or_overwrite_search_db,
    query_structured,
    query_fts,
)


def run():
    st.set_page_config(page_title="BB Log Search", layout="wide")
    st.title("BB Log Search")

    # -----------------------------
    # Layout: two columns
    # -----------------------------
    col1, col2 = st.columns([1, 2])

    # ╭──────────────────────────────────────────────────────────────╮
    # │ LEFT: Controls only                                          │
    # ╰──────────────────────────────────────────────────────────────╯
    with col1:
        st.header("Source selection")

        # A) Root input + Get folders (combined, controls only)
        c_root, c_btn = st.columns([5, 2])
        default_root = st.session_state.get("root_input", str(Path("./bb_logs/conversions")))
        with c_root:
            root_input = st.text_input(
                "Root directory",
                value=default_root,
                help="Absolute or relative path. On Windows, use a full path like C:\\...\\bb_log_tool\\bb_logs\\conversions",
            )
        with c_btn:
            if st.button("Get folders", use_container_width=True):
                ok, abs_root, msg = normalize_dir(root_input)
                st.session_state["root_input"] = root_input
                st.session_state["root_ok"] = ok
                st.session_state["root_msg"] = msg
                if ok:
                    st.session_state["root_abs"] = str(abs_root)
                    subs = list_first_level_subdirs(abs_root)
                    st.session_state["subdirs"] = [str(p) for p in subs]
                else:
                    # Reset downstream state if the root is not valid
                    for k in (
                        "root_abs",
                        "subdirs",
                        "candidate_run_dir",
                        "run_validation",
                        "confirmed_source_dir",
                        "confirmed_idx_path",
                        "selected_type",
                        "search_db_path",
                        "search_db_meta",
                    ):
                        st.session_state.pop(k, None)

        # B) Run selection (first-level only)
        subdirs = st.session_state.get("subdirs", [])
        run_dir = None
        if subdirs:
            labels = [Path(p).name for p in subdirs]
            prev_label = st.session_state.get("run_label")
            index = labels.index(prev_label) if prev_label in labels else 0
            run_label = st.selectbox("Run folder", options=labels, index=index)
            st.session_state["run_label"] = run_label
            run_dir = Path(subdirs[labels.index(run_label)])
            st.session_state["candidate_run_dir"] = str(run_dir)
        else:
            # No runs listed yet → nothing else in left column until user clicks Get folders
            pass

        # C) Log type selector appears ONLY if the selected run validates OK
        #    (We do the validation here, but all messages/analysis render in RIGHT column.)
        selected_type = None
        placeholder_label = "— Select log type —"
        if run_dir:
            idx_path = run_dir / "converted_files.json"

            @st.cache_data(show_spinner=False)
            def _validate_dir(path_str: str, idx_mtime: float):
                return validate_conversion_run_dir(Path(path_str))

            report = _validate_dir(str(run_dir), idx_path.stat().st_mtime if idx_path.exists() else 0.0)
            st.session_state["run_validation"] = report

            if report.get("ok"):
                # Build inventory (types), to inform selector; analysis renders in RIGHT col
                @st.cache_data(show_spinner=False)
                def _inventory(idx_path: str, idx_mtime: float):
                    return build_type_inventory(idx_path)

                inv_by_type, inv_unknown, inv_all = _inventory(str(idx_path), idx_path.stat().st_mtime)
                available_types = sorted(inv_by_type.keys())

                if available_types:
                    # Do NOT preselect: add a placeholder option
                    display_options = [placeholder_label] + available_types
                    chosen = st.selectbox("Log type", options=display_options, index=0)
                    if chosen != placeholder_label:
                        selected_type = chosen
                        st.session_state["selected_type"] = selected_type
                        st.session_state["confirmed_source_dir"] = str(run_dir)
                        st.session_state["confirmed_idx_path"] = str(idx_path)
                else:
                    # No types => no selector
                    st.session_state.pop("selected_type", None)
                    st.session_state.pop("confirmed_source_dir", None)
                    st.session_state.pop("confirmed_idx_path", None)
            else:
                # Validation failed => clear any previous confirmed/type state
                st.session_state.pop("selected_type", None)
                st.session_state.pop("confirmed_source_dir", None)
                st.session_state.pop("confirmed_idx_path", None)

        # D) Build DB & Search controls appear ONLY after a type is selected
        confirmed_dir = st.session_state.get("confirmed_source_dir")
        idx_path = st.session_state.get("confirmed_idx_path")
        selected_type = st.session_state.get("selected_type")

        if confirmed_dir and idx_path and selected_type:
            st.header("Build session DB & Search")
            include_noisy = st.checkbox("Include noisy records in DB", value=False)

            build_clicked = st.button("Create / Overwrite search database", type="primary")
            if build_clicked:
                with st.spinner("Building session search DB…"):
                    files_for_type = filter_converted_files_by_type_and_dir(idx_path, confirmed_dir, selected_type)
                    if not files_for_type:
                        # Message will be shown in RIGHT column below
                        st.session_state["last_build_warning"] = f"No files found for {selected_type} in {confirmed_dir}"
                        st.session_state.pop("search_db_path", None)
                        st.session_state.pop("search_db_meta", None)
                    else:
                        meta = create_or_overwrite_search_db(
                            conv_dir=confirmed_dir,
                            log_type=selected_type,
                            files=files_for_type,
                            include_noisy=include_noisy,
                        )
                        st.session_state["search_db_path"] = meta["db_path"]
                        st.session_state["search_db_meta"] = meta
                        st.session_state.pop("last_build_warning", None)

            # Structured & FTS inputs (results render in RIGHT column)
            db_path = st.session_state.get("search_db_path")

            st.subheader("Structured search")
            c1, c2, c3 = st.columns(3)
            with c1:
                start_ts = st.text_input("Start timestamp", placeholder="YYYY-MM-DD HH:MM:SS")
            with c2:
                end_ts = st.text_input("End timestamp", placeholder="YYYY-MM-DD HH:MM:SS")
            with c3:
                limit = st.number_input("Max rows", min_value=100, max_value=10000, value=2000, step=100)
            u_e = st.columns(2)
            with u_e[0]:
                user_like = st.text_input("User contains", placeholder="e.g., jkelley")
            with u_e[1]:
                endpoint_like = st.text_input("Endpoint contains", placeholder="e.g., /learn/api/public/v1/")
            run_structured = st.button("Run structured search", disabled=not db_path)

            st.subheader("Free‑text search (FTS)")
            fts_q = st.text_input("Query text", placeholder='e.g., "timeout OR 504"')
            run_fts = st.button("Run FTS search", disabled=(not db_path or not fts_q))

            # Stash triggers so RIGHT column can execute & render results
            st.session_state["__run_structured__"] = bool(run_structured)
            st.session_state["__structured_args__"] = dict(
                db_path=db_path,
                start_ts=start_ts or None,
                end_ts=end_ts or None,
                user_like=user_like or None,
                endpoint_like=endpoint_like or None,
                limit=int(limit),
            )
            st.session_state["__run_fts__"] = bool(run_fts)
            st.session_state["__fts_args__"] = dict(db_path=db_path, fts_q=fts_q or "", limit=1000)

        else:
            # Hide build/search controls until a type is selected
            st.header("Build session DB & Search")
            st.caption("Select a **log type** to enable DB build and search controls.")

    # ╭──────────────────────────────────────────────────────────────╮
    # │ RIGHT: All confirmations, analysis & results                 │
    # ╰──────────────────────────────────────────────────────────────╯
    with col2:
        st.header("Status, analysis & results")

        # Root status message
        if st.session_state.get("root_msg"):
            if st.session_state.get("root_ok"):
                st.success(st.session_state["root_msg"])
            else:
                st.error(st.session_state["root_msg"])

        # Selected run + validation
        if st.session_state.get("candidate_run_dir"):
            st.write("**Selected run:**", st.session_state["candidate_run_dir"])

        rv = st.session_state.get("run_validation")
        if rv:
            # Compact validation metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Index present", "Yes" if rv.get("idx_exists") else "No")
            m2.metric("Index entries", str(rv.get("idx_entries", 0)))
            m3.metric("Missing/Outside", f"{len(rv.get('missing_files', []))}/{len(rv.get('outside_files', []))}")

            if rv.get("ok"):
                st.success("Run is valid.")
            else:
                st.warning("Run validation failed. Fix issues or select another folder.")

            with st.expander("Validation details"):
                st.json(rv)

        # Type inventory (after successful validation)
        inv_summary_rendered = False
        confirmed_dir = st.session_state.get("confirmed_source_dir")
        idx_path = st.session_state.get("confirmed_idx_path")
        if confirmed_dir and idx_path and Path(idx_path).exists():
            # Recompute inventory using cache key (mtime) so the right panel matches actual files
            @st.cache_data(show_spinner=False)
            def _inventory(idx_path: str, idx_mtime: float):
                return build_type_inventory(idx_path)

            inv_by_type, inv_unknown, inv_all = _inventory(idx_path, Path(idx_path).stat().st_mtime)
            inv_summary_rendered = True

            s1, s2, s3 = st.columns(3)
            s1.metric("Files in index", f"{len(inv_all):,}")
            s2.metric("Typed files", f"{sum(len(v) for v in inv_by_type.values()):,}")
            s3.metric("Unknown file type", f"{len(inv_unknown):,}")

            if inv_unknown:
                with st.expander("Files with unidentified type"):
                    st.dataframe(pd.DataFrame({"file": inv_unknown}), use_container_width=True, height=200)

            if inv_by_type:
                counts = (
                    pd.DataFrame([{"log_type": k, "file_count": len(v)} for k, v in sorted(inv_by_type.items())])
                    .sort_values(["file_count", "log_type"], ascending=[False, True])
                )
                st.dataframe(counts, use_container_width=True, height=240)

        # DB status and build warnings
        if st.session_state.get("last_build_warning"):
            st.warning(st.session_state["last_build_warning"])

        db_path = st.session_state.get("search_db_path")
        db_meta = st.session_state.get("search_db_meta")
        if db_path and db_meta:
            st.info(
                f"**DB ready:** `{db_path}`  \n"
                f"**rows:** {db_meta['row_count']:,}  •  "
                f"**files:** {db_meta['file_count']}  •  "
                f"**build:** {db_meta['seconds']}s  •  "
                f"**fts:** {db_meta['fts']}"
            )

        # Execute and render results here (RIGHT column)
        results_container = st.empty()

        # Structured search
        if st.session_state.get("__run_structured__"):
            args = st.session_state.get("__structured_args__", {})
            if args.get("db_path"):
                with st.spinner("Querying (structured)…"):
                    df = query_structured(
                        args["db_path"],
                        start_ts=args.get("start_ts"),
                        end_ts=args.get("end_ts"),
                        host_in=None,  # (host prefilter can be added later)
                        user_like=args.get("user_like"),
                        endpoint_like=args.get("endpoint_like"),
                        include_noisy=False,
                        limit=int(args.get("limit", 2000)),
                    )
                if df.empty:
                    results_container.info("No matches.")
                else:
                    results_container.dataframe(df, use_container_width=True, height=520)

        # FTS search
        if st.session_state.get("__run_fts__"):
            args = st.session_state.get("__fts_args__", {})
            if args.get("db_path") and args.get("fts_q"):
                with st.spinner("Searching text (FTS)…"):
                    df = query_fts(args["db_path"], args["fts_q"], limit=int(args.get("limit", 1000)))
                if df.empty:
                    results_container.info("No matches.")
                else:
                    results_container.dataframe(df, use_container_width=True, height=520)
