
# pages/analyze.py
import streamlit as st
import os
import json
import pandas as pd
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile

# Import your manifest loader (adjust if it's located elsewhere)
from modules.parser_utils import load_manifest

# Toggle: use in-memory ZIPs (True) or write ZIPs to disk in user_downloads (False)
USE_IN_MEMORY_ZIP = True


def _create_zip_in_memory(file_list) -> bytes:
    """Create a ZIP in memory and return its bytes."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zipf:
        for file in file_list:
            p = Path(file)
            if p.exists():
                zipf.write(p, arcname=p.name)
    buffer.seek(0)
    return buffer.getvalue()


def _create_zip_on_disk(zip_path: Path, file_list) -> Path:
    """Create a ZIP on disk at zip_path and return the path."""
    zip_path.parent.mkdir(exist_ok=True)
    with ZipFile(zip_path, "w") as zipf:
        for file in file_list:
            p = Path(file)
            if p.exists():
                zipf.write(p, arcname=p.name)
    return zip_path


def run():
    st.header("Blackboard Log Tools")
    st.subheader("📊 Analyze Converted Logs")

    # Root where conversions live
    conversions_root = Path("./bb_logs/conversions")
    if not conversions_root.exists():
        st.error("Conversion folder not found. Please run a conversion first.")
        st.stop()

    # List available conversion subfolders
    all_dirs = [
        f for f in os.listdir(conversions_root)
        if (conversions_root / f).is_dir()
    ]
    if not all_dirs:
        st.warning("No converted folders found. Please convert logs first.")
        st.stop()

    # Select conversion folder
    selected_dir = st.selectbox("Select conversion folder", all_dirs, key="analyze_selected_dir")
    manifest_path = conversions_root / selected_dir / "converted_files.json"

    # Context panel
    st.markdown(f"**Selected Folder:** `{selected_dir}`")
    st.markdown(f"**Manifest Path:** `{manifest_path}`")

    if not manifest_path.exists():
        st.error(f"Manifest not found at: {manifest_path}")
        st.stop()

    # Load manifest
    try:
        manifest = load_manifest(manifest_path)
        if not manifest:
            st.warning("Manifest is empty. No files to analyze.")
            st.stop()
    except Exception as e:
        st.error(f"Failed to load manifest: {e}")
        st.stop()

    # Build DataFrame
    df = pd.DataFrame(manifest)
    st.markdown(f"### 🗂️ Total Files: `{len(df)}`")

    # Defensive: ensure expected columns exist
    expected_cols = {"path", "host", "log_type"}
    missing = expected_cols - set(df.columns)
    if missing:
        st.warning(f"Manifest is missing expected column(s): {', '.join(sorted(missing))}. "
                   f"Available columns: {', '.join(df.columns)}")

    # Prepare columns safely
    host_series = df["host"] if "host" in df.columns else pd.Series([], dtype=str)
    type_series = df["log_type"] if "log_type" in df.columns else pd.Series([], dtype=str)

    # Two-column layout: left = summaries/tables, right = actions
    left, right = st.columns([2, 1])

    with left:
        st.markdown("### 🖥️ File Count by Host")
        host_df = host_series.value_counts().reset_index()
        if not host_df.empty:
            host_df.columns = ["Host", "File Count"]
            st.data_editor(
                host_df,
                column_config={"File Count": st.column_config.NumberColumn("File Count")},
                use_container_width=True,
                disabled=True,
            )
        else:
            st.info("No host data available.")

        st.markdown("### 📄 File Count by Log Type")
        type_df = type_series.value_counts().reset_index()
        if not type_df.empty:
            type_df.columns = ["Log Type", "File Count"]
            st.data_editor(
                type_df,
                column_config={"File Count": st.column_config.NumberColumn("File Count")},
                use_container_width=True,
                disabled=True,
            )
        else:
            st.info("No log type data available.")

    with right:
        st.markdown("### 📥 Download Files by Host")
        host_options = sorted(host_series.dropna().unique().tolist())
        if host_options:
            selected_host = st.selectbox("Select Host", host_options, key="analyze_host_select")
            host_files = df[df.get("host", "") == selected_host]["path"].tolist()

            if not host_files:
                st.info("No files for selected host.")
            else:
                if USE_IN_MEMORY_ZIP:
                    if st.button("Create Host ZIP", use_container_width=True, key="btn_host_zip_mem"):
                        try:
                            zip_bytes = _create_zip_in_memory(host_files)
                            st.download_button(
                                label="Download Host Files",
                                data=zip_bytes,
                                file_name=f"{selected_host}_files.zip",
                                mime="application/zip",
                                use_container_width=True,
                            )
                            st.success(f"In-memory ZIP ready for host: {selected_host}")
                        except Exception as e:
                            st.exception(e)
                else:
                    # Disk-based ZIP in user_downloads
                    user_dl = Path("user_downloads")
                    host_zip_path = user_dl / f"{selected_host}_files.zip"
                    col_a, col_b = st.columns([1, 1])
                    with col_a:
                        if st.button("Prepare Host ZIP", use_container_width=True, key="btn_host_zip_disk"):
                            try:
                                zip_path = _create_zip_on_disk(host_zip_path, host_files)
                                st.success(f"Created host ZIP: {zip_path.name}")
                            except Exception as e:
                                st.exception(e)
                    with col_b:
                        if host_zip_path.exists():
                            with open(host_zip_path, "rb") as fh:
                                st.download_button(
                                    "Download Host Files",
                                    fh,
                                    file_name=host_zip_path.name,
                                    use_container_width=True,
                                )

        else:
            st.info("No hosts available in manifest.")

        st.markdown("### 📥 Download Files by Log Type")
        type_options = sorted(type_series.dropna().unique().tolist())
        if type_options:
            selected_type = st.selectbox("Select Log Type", type_options, key="analyze_type_select")
            type_files = df[df.get("log_type", "") == selected_type]["path"].tolist()

            if not type_files:
                st.info("No files for selected log type.")
            else:
                if USE_IN_MEMORY_ZIP:
                    if st.button("Create Log Type ZIP", use_container_width=True, key="btn_type_zip_mem"):
                        try:
                            zip_bytes = _create_zip_in_memory(type_files)
                            st.download_button(
                                label="Download Log Type Files",
                                data=zip_bytes,
                                file_name=f"{selected_type}_files.zip",
                                mime="application/zip",
                                use_container_width=True,
                            )
                            st.success(f"In-memory ZIP ready for log type: {selected_type}")
                        except Exception as e:
                            st.exception(e)
                else:
                    # Disk-based ZIP in user_downloads
                    user_dl = Path("user_downloads")
                    type_zip_path = user_dl / f"{selected_type}_files.zip"
                    col_c, col_d = st.columns([1, 1])
                    with col_c:
                        if st.button("Prepare Log Type ZIP", use_container_width=True, key="btn_type_zip_disk"):
                            try:
                                zip_path = _create_zip_on_disk(type_zip_path, type_files)
                                st.success(f"Created type ZIP: {zip_path.name}")
                            except Exception as e:
                                st.exception(e)
                    with col_d:
                        if type_zip_path.exists():
                            with open(type_zip_path, "rb") as fh:
                                st.download_button(
                                    "Download Log Type Files",
                                    fh,
                                    file_name=type_zip_path.name,
                                    use_container_width=True,
                                )

        else:
            st.info("No log types available in manifest.")

        # Optional housekeeping button for disk mode
        if not USE_IN_MEMORY_ZIP:
            st.markdown("### 🧹 Housekeeping")
            user_dl = Path("user_downloads")
            if st.button("Clear user_downloads ZIPs", use_container_width=True, key="btn_clear_dl"):
                try:
                    if user_dl.exists():
                        for f in user_dl.glob("*.zip"):
                            f.unlink()
                    st.success("Cleared user_downloads ZIPs.")
                except Exception as e:
                    st.exception(e)
