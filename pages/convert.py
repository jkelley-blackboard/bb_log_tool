import streamlit as st
from modules.unified_converter import convert_logs
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
        st.markdown('<div class="custom-column">', unsafe_allow_html=True)

        # Select folder with downloaded logs
        downloads_root = "./bb_logs/downloads"
        all_dirs = [
            f for f in os.listdir(downloads_root)
            if os.path.isdir(os.path.join(downloads_root, f))
        ]

        if not all_dirs:
            st.warning("No downloaded log folders found. Please download logs first.")
        else:
            selected_subdir = st.selectbox("Select downloaded logs folder", all_dirs)
            source_dir = os.path.join(downloads_root, selected_subdir)
            folder_name = os.path.basename(selected_subdir)

            # --- Base Conversion Folder ---
            default_conversion_root = "./bb_logs/conversions"
            conversion_root = st.text_input(
                "Base Conversion Folder",
                value=default_conversion_root,
                help="Override the default folder where converted logs will be saved."
            )

            # --- Final Destination Folder ---
            final_conversion_path = os.path.join(conversion_root, f"{folder_name}_convert")
            st.markdown(f"**Final Conversion Folder:** `{final_conversion_path}`")

            # Select output type
            output_type = st.selectbox("Output type", ["flat", "json-legacy", "json-distributed"])

            # Action buttons
            button_col_left, button_col_right = st.columns([1, 1])
            convert_btn = button_col_left.button("Convert Logs", use_container_width=True)
            clear_btn = button_col_right.button("Clear All Conversions", use_container_width=True,
                                                help="Deletes the entire base conversion folder and all subfolders.")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("""
            <div style="background-color:#f0f0f0; padding:10px; border-radius:5px;">
            <b>Help / Tips:</b><br>
            - Ensure you select the correct downloaded logs folder.<br>
            - The output folder will be created automatically; avoid overwriting important data.<br>
            - Choose the output type that matches your use case:<br>
            &nbsp;&nbsp;&nbsp;• <b>flat</b> – human readable per log type and server.<br>
            &nbsp;&nbsp;&nbsp;• <b>json-legacy</b> – one big JSON per server.<br>
            &nbsp;&nbsp;&nbsp;• <b>json-distributed</b> – hybrid. Individual JSON versions of each log file.<br>
            - Check that your selected start/end date and hour match the logs you downloaded.<br>
            - Conversion logs will be saved in ./tool_logs.
            </div>
            """, unsafe_allow_html=True)

    # ==========================
    # RIGHT COLUMN - OUTPUT MESSAGES
    # ==========================
    with right_col:
        st.markdown('<div class="custom-column right-column">', unsafe_allow_html=True)

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
                        # Iterate over all items in the root directory
                        for filename in os.listdir(conversion_root):
                            file_path = os.path.join(conversion_root, filename)
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)  # remove file or link
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)  # remove subdirectory
                        st.success(f"All conversions cleared from: {conversion_root}")
                    except Exception as e:
                        st.error(f"Failed to clear conversions: {e}")
                else:
                    st.warning("No conversion folder found to clear.")

        st.markdown('</div>', unsafe_allow_html=True)
