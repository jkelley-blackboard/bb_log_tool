# pages/build.py
from __future__ import annotations

from pathlib import Path
import streamlit as st
import pandas as pd

from modules.build_utils import (
    normalize_dir,
    list_first_level_subdirs,
    validate_conversion_run_dir,
    build_type_inventory,
    filter_converted_files_by_type_and_dir,
    create_or_overwrite_search_db,
)


def run():
    st.set_page_config(page_title="BB Logs — Build DB", layout="wide")
    st.title("BB Logs — Build DB")

    col1, col2 = st.columns([1, 2])

    # LEFT: Controls
    with col1:
        st.header("Select source")
        c_root, c_btn = st.columns([5, 2])
        default_root = st.session_state.get("root_input", str(Path("./bb_logs/conversions")))
        with c_root:
            root_input = st.text_input("Root directory", value=default_root)
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
                    for k in ("root_abs","subdirs","candidate_run_dir","run_validation",
                               "confirmed_source_dir","confirmed_idx_path","selected_type",
                               "search_db_path","search_db_meta"):
                        st.session_state.pop(k, None)

        # Run picker
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

        # Validate and type selection
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
                @st.cache_data(show_spinner=False)
                def _inventory(idx_path: str, idx_mtime: float):
                    return build_type_inventory(idx_path)
                by_type, unknown_files, all_files = _inventory(str(idx_path), idx_path.stat().st_mtime)
                available_types = sorted(by_type.keys())

                if available_types:
                    display_options = [placeholder_label] + available_types
                    chosen = st.selectbox("Log type", options=display_options, index=0)
                    if chosen != placeholder_label:
                        selected_type = chosen
                        st.session_state["selected_type"] = selected_type
                        st.session_state["confirmed_source_dir"] = str(run_dir)
                        st.session_state["confirmed_idx_path"] = str(idx_path)
                else:
                    st.session_state.pop("selected_type", None)
                    st.session_state.pop("confirmed_source_dir", None)
                    st.session_state.pop("confirmed_idx_path", None)
            else:
                st.session_state.pop("selected_type", None)
                st.session_state.pop("confirmed_source_dir", None)
                st.session_state.pop("confirmed_idx_path", None)

        # Build controls
        confirmed_dir = st.session_state.get("confirmed_source_dir")
        idx_path = st.session_state.get("confirmed_idx_path")
        selected_type = st.session_state.get("selected_type")

        if confirmed_dir and idx_path and selected_type:
            st.header("Build session DB")
            include_noisy = st.checkbox("Include noisy records in DB", value=False)
            if st.button("Create / Overwrite search database", type="primary"):
                with st.spinner("Building session search DB…"):
                    files_for_type = filter_converted_files_by_type_and_dir(idx_path, confirmed_dir, selected_type)
                    if not files_for_type:
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
        else:
            st.header("Build session DB")
            st.caption("Select a **log type** to enable DB build.")

    # RIGHT: Messages/analysis
    with col2:
        st.header("Status & analysis")

        if st.session_state.get("root_msg"):
            if st.session_state.get("root_ok"):
                st.success(st.session_state["root_msg"])
            else:
                st.error(st.session_state["root_msg"])

        if st.session_state.get("candidate_run_dir"):
            st.write("**Selected run:**", st.session_state["candidate_run_dir"])

        rv = st.session_state.get("run_validation")
        if rv:
            m1, m2, m3 = st.columns(3)
            m1.metric("Index present", "Yes" if rv.get("idx_exists") else "No")
            m2.metric("Index entries", str(rv.get("idx_entries", 0)))
            m3.metric("Missing/Outside", f"{len(rv.get('missing_files', []))}/{len(rv.get('outside_files', []))}")
            if rv.get("ok"):
                st.success("Run is valid.")
            else:
                st.warning("Run validation failed.")
            with st.expander("Validation details"):
                st.json(rv)

        # Type inventory summary
        confirmed_dir = st.session_state.get("confirmed_source_dir")
        idx_path = st.session_state.get("confirmed_idx_path")
        if confirmed_dir and idx_path and Path(idx_path).exists():
            @st.cache_data(show_spinner=False)
            def _inventory(idx_path: str, idx_mtime: float):
                return build_type_inventory(idx_path)
            by_type, unknown_files, all_files = _inventory(idx_path, Path(idx_path).stat().st_mtime)
            s1, s2, s3 = st.columns(3)
            s1.metric("Files in index", f"{len(all_files):,}")
            s2.metric("Typed files", f"{sum(len(v) for v in by_type.values()):,}")
            s3.metric("Unknown file type", f"{len(unknown_files):,}")
            if unknown_files:
                with st.expander("Files with unidentified type"):
                    st.dataframe(pd.DataFrame({"file": unknown_files}), use_container_width=True, height=200)
            if by_type:
                counts = (
                    pd.DataFrame([{"log_type": k, "file_count": len(v)} for k, v in sorted(by_type.items())])
                    .sort_values(["file_count", "log_type"], ascending=[False, True])
                )
                st.dataframe(counts, use_container_width=True, height=240)

        if st.session_state.get("last_build_warning"):
            st.warning(st.session_state["last_build_warning"])

        db_meta = st.session_state.get("search_db_meta")
        db_path = st.session_state.get("search_db_path")
        if db_meta and db_path:
            st.info(
                f"**DB ready:** `{db_path}`  \n" \
                f"**rows:** {db_meta['row_count']:,}  •  **files:** {db_meta['file_count']}  •  " \
                f"**build:** {db_meta['seconds']}s  •  **fts:** {db_meta['fts']}"
            )
