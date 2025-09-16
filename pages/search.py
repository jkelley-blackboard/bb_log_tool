# pages/search.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List
import streamlit as st
import pandas as pd

from modules.parser_utils import LOG_FIELDS, get_log_fields  # UI needs fields to render filters
from modules.search_utils import (
    get_conversion_subdirs_with_metadata,
    get_default_conversion_dir,
    build_type_inventory,
    filter_converted_files_by_type_and_dir,
    load_and_parse_logs,
    filter_logs,
)

def run():
    st.set_page_config(page_title="BB Log Search", layout="wide")
    st.title("BB Log Search")

    # -----------------------------
    # Layout: two columns
    # -----------------------------
    col1, col2 = st.columns([1, 2])

    CONV_ROOT = "./bb_logs/conversions"

    # ---- Discovery (cached) ----
    @st.cache_data(show_spinner=False)
    def _list_runs(root: str):
        return get_conversion_subdirs_with_metadata(root)

    runs = _list_runs(CONV_ROOT)
    if not runs:
        with col1:
            st.header("Search Inputs")
            st.error("No converted directories with `converted_files.json` found under bb_logs/conversions.")
        with col2:
            st.header("Index Inventory (no file I/O)")
            st.info("Add a conversion run that includes `converted_files.json` to proceed.")
        return

    def _label_for(dir_path: str) -> str:
        try:
            rel = str(Path(dir_path).resolve().relative_to(Path(CONV_ROOT).resolve()))
        except Exception:
            rel = Path(dir_path).name
        idx = Path(dir_path) / "converted_files.json"
        mtime = idx.stat().st_mtime if idx.exists() else 0
        return f"{rel} — {pd.to_datetime(mtime, unit='s'):%Y-%m-%d %H:%M:%S}"

    labels = [_label_for(d) for d, _ in runs]
    label_to_dir = {lab: d for lab, (d, _) in zip(labels, runs)}
    default_dir = get_default_conversion_dir(CONV_ROOT)
    default_label = next((lab for lab, d in label_to_dir.items() if d == default_dir), labels[0])

    with col1:
        st.header("Search Inputs")

        selected_label = st.selectbox(
            "Select Converted Directory",
            options=labels,
            index=labels.index(default_label) if default_label in labels else 0,
        )
        selected_dir = label_to_dir[selected_label]
        idx_path = os.path.join(selected_dir, "converted_files.json")
        idx_exists = os.path.exists(idx_path)

        st.caption("The log type list will populate after the index is scanned.")

        # ---- Inventory from index only (cached) ----
        @st.cache_data(show_spinner=False)
        def _inventory(idx_path: str, idx_mtime: float):
            return build_type_inventory(idx_path)

        by_type: Dict[str, List[str]] = {}
        unknown_files: List[str] = []
        all_files: List[str] = []
        available_types: List[str] = []

        if idx_exists:
            idx_mtime = Path(idx_path).stat().st_mtime
            by_type, unknown_files, all_files = _inventory(idx_path, idx_mtime)
            available_types = sorted(by_type.keys())

        # ---- Gated log-type select ----
        selected_type = st.selectbox(
            "Select Log Type",
            options=available_types if available_types else ["(No types discovered yet)"],
            index=0,
            disabled=(not idx_exists or len(available_types) == 0),
            help="This list is built from the index only. No files are opened yet.",
        )

        # ---- Filters UI (no file I/O) ----
        st.subheader("Filters")
        search_fields = get_log_fields(selected_type) if selected_type in LOG_FIELDS else []
        field_filters = {}
        for i in range(0, len(search_fields), 3):
            cols = st.columns(3)
            for j, field in enumerate(search_fields[i:i + 3]):
                field_filters[field] = cols[j].text_input(field, key=f"f_{field}")

        include_noisy = st.checkbox("Include noisy records", value=False)

        # ---- Search button gated by type presence ----
        search_button = st.button(
            "Search",
            type="primary",
            disabled=(not idx_exists or len(available_types) == 0 or selected_type not in available_types),
        )

    with col2:
        st.header("Index Inventory (no file I/O)")
        if not idx_exists:
            st.info("Select a conversion directory that contains `converted_files.json` to see an inventory.")
        else:
            c1, c2m, c3 = st.columns(3)
            with c1:
                st.metric("Files in index", f"{len(all_files):,}")
            with c2m:
                st.metric("Typed files", f"{sum(len(v) for v in by_type.values()):,}")
            with c3:
                st.metric("Unknown type files", f"{len(unknown_files):,}")

            if by_type:
                counts = (
                    pd.DataFrame([{"log_type": k, "file_count": len(v)} for k, v in sorted(by_type.items())])
                    .sort_values(["file_count", "log_type"], ascending=[False, True])
                )
                st.dataframe(counts, use_container_width=True, height=280)

            if unknown_files:
                with st.expander("Files with unidentified type"):
                    df_unknown = pd.DataFrame({"file": unknown_files})
                    st.dataframe(df_unknown, use_container_width=True, height=240)
                    st.download_button(
                        "Download unknown file list",
                        data=df_unknown.to_csv(index=False).encode("utf-8"),
                        file_name="unknown_type_files.csv",
                        mime="text/csv",
                    )

        # -------- Actual search only after click --------
        if search_button:
            @st.cache_data(show_spinner=True)
            def _match_files(idx_path: str, dir_path: str, lt: str):
                return filter_converted_files_by_type_and_dir(idx_path, dir_path, lt)

            @st.cache_data(show_spinner=True)
            def _parse(dir_path: str, lt: str, noisy: bool):
                files = _match_files(idx_path, dir_path, lt)
                return files, load_and_parse_logs(files, lt, include_noisy=noisy)

            files, parsed_entries = _parse(selected_dir, selected_type, include_noisy)
            if not files:
                st.warning(f"No files found for log type '{selected_type}' in '{selected_dir}'")
                return

            filtered_entries = filter_logs(parsed_entries, filters=field_filters)

            st.subheader("Search Results")
            st.write(f"Found **{len(filtered_entries)}** matching entries in **{len(files)}** file(s).")

            if filtered_entries:
                df = pd.DataFrame(filtered_entries)
                if "timestamp" in df.columns:
                    df["timestamp"] = df["timestamp"].astype("string")
                    df = df.sort_values("timestamp", na_position="last")

                meta_cols = [c for c in ["_file_name", "_file_path"] if c in df.columns]
                main_cols = [c for c in df.columns if c not in meta_cols]
                df = df[main_cols + meta_cols]
                st.dataframe(df, use_container_width=True, height=520)

                st.download_button(
                    "Download CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="search_results.csv",
                    mime="text/csv",
                )
                st.download_button(
                    "Download JSON",
                    data=df.to_json(orient="records", indent=2).encode("utf-8"),
                    file_name="search_results.json",
                    mime="application/json",
                )

            with st.expander("Preview first 50 JSON entries"):
                for row in filtered_entries[:50]:
                    st.json(row)
