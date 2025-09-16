import os
import json
import gzip
import shutil
import logging
from datetime import datetime
from pathlib import Path
import streamlit as st

def decompress_file(file_path):
    """Decompress .gz files and remove originals."""
    if file_path.endswith('.gz'):
        decompressed_path = file_path.rstrip('.gz')
        with gzip.open(file_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        return decompressed_path
    return file_path

def convert_flat_or_legacy(file_paths, output_dir, output_type):
    from modules.convertlogs import FileWriter, convert_file
    writer_type = None if output_type == "flat" else "json"
    with FileWriter(output_dir, writer_type) as writer:
        for path in file_paths:
            convert_file(path, writer)

def convert_distributed(file_paths, output_dir):
    from modules import json_to_json_distributed as distributed_module
    distributed_module.output_base = Path(output_dir)  # Override default output path
    for path in file_paths:
        distributed_module.convert_logs(Path(path))

def convert_logs(*, source_path, output_path, output_type="flat", use_streamlit=False, log_file_path=None):
    """Convert downloaded Blackboard logs into selected format."""
    os.makedirs(output_path, exist_ok=True)

    # Setup logging
    if log_file_path is None:
        log_file_path = f"./tool_logs/converting_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file_path, mode='w'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("=== Conversion Started ===")
    logger.info(f"Source folder: {source_path}")
    logger.info(f"Output folder: {output_path}")
    logger.info(f"Output type: {output_type}")

    # Gather all .txt and .gz files
    all_files = [
        os.path.join(source_path, f)
        for f in os.listdir(source_path)
        if f.endswith(('.txt', '.gz'))
    ]
    total_files = len(all_files)

    if use_streamlit:
        st.text(f"Files to convert: {total_files}")
        st.text(f"Converting logs in: {source_path} → {output_path}")
        progress_bar = st.progress(0)

    # Decompress all .gz files
    decompressed_files = []
    for i, f in enumerate(all_files):
        decompressed = decompress_file(f)
        decompressed_files.append(decompressed)
        if use_streamlit and total_files > 0:
            progress_bar.progress(min((i + 1) / total_files, 1.0))

    # Convert logs based on type
    if output_type == "json-distributed":
        convert_distributed(decompressed_files, output_path)
    else:
        convert_flat_or_legacy(decompressed_files, output_path, output_type)

    # Generate JSON manifest of all converted files
    converted_paths = []
    for root, _, files in os.walk(output_path):
        for f in files:
            converted_paths.append(str(Path(root) / f))
    manifest_path = Path(output_path) / "converted_files.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(converted_paths, mf, indent=2)
    logger.info(f"JSON manifest of converted files saved to: {manifest_path}")

    # Final logging
    logger.info("=== Conversion Completed ===")
    logger.info(f"Total files converted: {len(converted_paths)}")
    logger.info(f"Execution log saved to: {log_file_path}")

    if use_streamlit:
        st.success(f"Conversion finished for {total_files} files.")
        st.text(f"Execution log saved to: {log_file_path}")
        st.text(f"JSON manifest saved to: {manifest_path}")
