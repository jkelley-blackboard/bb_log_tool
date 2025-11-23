import streamlit as st
import os
import json
import pandas as pd
from pathlib import Path
from zipfile import ZipFile
from modules.parser_utils import load_manifest

def run():
    # Clear user_downloads folder at session start
    download_dir = Path("user_downloads")
    if not download_dir.exists():
        download_dir.mkdir()
    else:
        for f in download_dir.glob("*.zip"):
            f.unlink()

    # UI layout
    st.set_page_config(page_title="Analyze Converted Logs", layout="wide")
    st.header("Blackboard Log Tools")
    st.subheader("📊 Analyze Converted Logs")

    conversions_root = "./bb_logs/conversions"
    if not Path(conversions_root).exists():
        st.error("Conversion folder not found. Please run a conversion first.")
        st.stop()

    all_dirs = [f for f in os.listdir(conversions_root) if os.path.isdir(os.path.join(conversions_root, f))]
    if not all_dirs:
        st.warning("No converted folders found. Please convert logs first.")
        st.stop()

    selected_dir = st.selectbox("Select conversion folder", all_dirs)
    manifest_path = Path(conversions_root) / selected_dir / "converted_files.json"

    st.markdown(f"**Selected Folder:** `{selected_dir}`")
    st.markdown(f"**Manifest Path:** `{manifest_path}`")

    if not manifest_path.exists():
        st.error(f"Manifest not found at: {manifest_path}")
        st.stop()

    try:
        manifest = load_manifest(manifest_path)
        if not manifest:
            st.warning("Manifest is empty. No files to analyze.")
            st.stop()
    except Exception as e:
        st.error(f"Failed to load manifest: {e}")
        st.stop()

    df = pd.DataFrame(manifest)
    st.markdown(f"### 📁 Total Files: `{len(df)}`")

    # Two-column layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🖥️ File Count by Host")
        host_df = df['host'].value_counts().reset_index()
        host_df.columns = ['Host', 'File Count']
        st.data_editor(host_df, column_config={"File Count": st.column_config.NumberColumn("File Count")}, use_container_width=True, disabled=True)

        st.markdown("### 📄 File Count by Log Type")
        type_df = df['log_type'].value_counts().reset_index()
        type_df.columns = ['Log Type', 'File Count']
        st.data_editor(type_df, column_config={"File Count": st.column_config.NumberColumn("File Count")}, use_container_width=True, disabled=True)

    with col2:
        st.markdown("### 📥 Download Files by Host")
        selected_host = st.selectbox("Select Host", host_df['Host'])
        host_files = df[df['host'] == selected_host]['path'].tolist()
        host_zip_path = download_dir / f"{selected_host}_files.zip"
        with ZipFile(host_zip_path, 'w') as zipf:
            for file in host_files:
                if Path(file).exists():
                    zipf.write(file, arcname=Path(file).name)
        with open(host_zip_path, "rb") as f:
            st.download_button("Download Host Files", f, file_name=host_zip_path.name)

        st.markdown("### 📥 Download Files by Log Type")
        selected_type = st.selectbox("Select Log Type", type_df['Log Type'])
        type_files = df[df['log_type'] == selected_type]['path'].tolist()
        type_zip_path = download_dir / f"{selected_type}_files.zip"
        with ZipFile(type_zip_path, 'w') as zipf:
            for file in type_files:
                if Path(file).exists():
                    zipf.write(file, arcname=Path(file).name)
        with open(type_zip_path, "rb") as f:
            st.download_button("Download Log Type Files", f, file_name=type_zip_path.name)