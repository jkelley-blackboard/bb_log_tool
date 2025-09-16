# ./pages/search.py

import streamlit as st
from pathlib import Path
import os
import json

from modules.parser_utils import LOG_FIELDS, parse_log_entry, get_log_fields, get_log_type_from_filename
from modules.search_utils import (
    get_conversion_subdirs_with_metadata,
    filter_converted_files_by_type_and_dir,
    filter_logs
)

def run():
    st.set_page_config(page_title="BB Log Search", layout="wide")
    st.title("BB Log Search")

    # -----------------------------
    # Layout: two columns
    # -----------------------------
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("Search Inputs")

        # Load available converted directories after page layout
        converted_dirs = get_conversion_subdirs_with_metadata(source_path="./bb_logs/conversions")
        if not converted_dirs:
            st.error("No converted directories with converted_files.json found.")
            return

        dir_options = {Path(d).name: (d, data) for d, data in converted_dirs}
        selected_label = st.selectbox("Select Converted Directory", options=list(dir_options.keys()))
        selected_dir, converted_data = dir_options[selected_label]

        # Select log type
        selected_type = st.selectbox("Select Log Type", options=list(LOG_FIELDS.keys()))

        # Get matching files
        converted_file_path = os.path.join(selected_dir, "converted_files.json")
        matching_files = filter_converted_files_by_type_and_dir(
            converted_file_path, selected_dir, selected_type
        )

        if not matching_files:
            st.warning(f"No files found for log type '{selected_type}' in directory '{selected_dir}'")
            return

        # Display filter inputs
        st.subheader("Filters")
        search_fields = get_log_fields(selected_type)
        field_filters = {}
        for i in range(0, len(search_fields), 3):
            cols = st.columns(3)
            for j, field in enumerate(search_fields[i:i + 3]):
                field_filters[field] = cols[j].text_input(field)

        include_noisy = st.checkbox("Include noisy records", value=False)
        search_button = st.button("Search")

    with col2:
        st.header("Search Results")
        results_container = st.empty()

        if search_button:
            parsed_entries = []
            for f in matching_files:
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        entries = json.load(fh)
                    for e in entries:
                        parsed = parse_log_entry(e, selected_type, file_path=f)
                        if include_noisy or parsed is not None:
                            parsed_entries.append(parsed if parsed is not None else e)
                except Exception as ex:
                    st.error(f"Failed to load {f}: {ex}")

            filtered_entries = filter_logs(parsed_entries, filters=field_filters)
            results_container.write(f"Found {len(filtered_entries)} matching entries")
            for entry in filtered_entries:
                results_container.json(entry)
