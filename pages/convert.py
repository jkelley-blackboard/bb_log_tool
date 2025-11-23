import streamlit as st
from modules.convert_utils import convert_logs
import os
import shutil
from datetime import datetime

def run():
    st.set_page_config(page_title="BB Log Converter", layout="wide")
    st.header("Blackboard Log Tools")
    st.subheader("⚙️ Convert Downloaded Logs")

    # Two-column layout
    left_col, right_col = st.columns([2, 3])

    # ==========================
    # LEFT COLUMN - INPUTS & BUTTONS
    # ==========================
    with left_col:
        downloads_root = "./bb_logs/downloads"
        all_dirs = [f for f in os.listdir(downloads_root) if os.path.isdir(os.path.join(downloads_root, f))]

        if not all_dirs:
            st.warning("No downloaded log folders found. Please download logs first.")
        else:
            selected_subdir = st.selectbox("Select downloaded logs folder", all_dirs)
            source_dir = os.path.join(downloads_root, selected_subdir)
            folder_name = os.path.basename(selected_subdir)

            default_conversion_root = "./bb_logs/conversions"
            conversion_root = st.text_input(
                "Base Conversion Folder",
                value=default_conversion_root,
                help="Override the default folder where converted logs will be saved."
            )

            final_conversion_path = os.path.join(conversion_root, f"{folder_name}_convert")
            st.markdown(f"**Final Conversion Folder:** `{final_conversion_path}`")

            output_type = 'flat'  # Hardcoded to flat

            button_col_left, button_col_right = st.columns([1, 1])
            convert_btn = button_col_left.button("Convert Logs", use_container_width=True)
            clear_btn = button_col_right.button("Clear All Conversions", use_container_width=True)

            st.markdown("""
            **Help / Tips:**
            - Ensure you select the correct downloaded logs folder.
            - The output folder will be created automatically; avoid overwriting important data.
            - Output format is now fixed to **flat**.
            - Check that your selected start/end date and hour match the logs you downloaded.
            - Conversion logs will be saved in ./tool_logs.
            """, unsafe_allow_html=True)

    # ==========================
    # RIGHT COLUMN - OUTPUT MESSAGES
    # ==========================
    with right_col:
        if not all_dirs:
            st.info("Awaiting logs to be downloaded.")
        else:
            if convert_btn:
                if not os.path.exists(source_dir):
                    st.error(f"Source folder does not exist: {source_dir}")
                else:
                    os.makedirs(final_conversion_path, exist_ok=True)
                    log_file_path = f"./tool_logs/converting_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                    os.makedirs("./tool_logs", exist_ok=True)

                    with st.spinner("Converting logs..."):
                        convert_logs(
                            source_path=source_dir,
                            output_path=final_conversion_path,
                            output_type=output_type,
                            use_streamlit=True,
                            log_file_path=log_file_path
                        )
                    st.success(f"Conversion completed successfully! Files saved to `{final_conversion_path}`")
                    st.text(f"Execution log saved to: {log_file_path}")

            if clear_btn:
                if os.path.exists(conversion_root):
                    try:
                        for filename in os.listdir(conversion_root):
                            file_path = os.path.join(conversion_root, filename)
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        st.success(f"All conversions cleared from: {conversion_root}")
                    except Exception as e:
                        st.error(f"Failed to clear conversions: {e}")
                else:
                    st.warning("No conversion folder found to clear.")