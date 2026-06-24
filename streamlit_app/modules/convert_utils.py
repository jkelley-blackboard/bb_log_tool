
# modules/convert_utils.py
import os
import json
import gzip
import shutil
import logging
import re
from datetime import datetime
from pathlib import Path
import streamlit as st
from modules.parser_utils import detect_log_type

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
    writer_type = None  # Always flat
    with FileWriter(output_dir, writer_type) as writer:
        for path in file_paths:
            convert_file(path, writer)

def generate_enriched_manifest(output_path):
    """Create enriched converted_files.json with metadata."""
    enriched_manifest = []
    host_pattern = re.compile(r"ip-\d+-\d+-\d+-\d+\.ec2\.internal")
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    for root, _, files in os.walk(output_path):
        for f in files:
            full_path = str(Path(root) / f)
            parts = full_path.split("\\")
            host = next((p for p in parts if host_pattern.fullmatch(p)), None)
            log_type = detect_log_type(full_path) or "unknown"
            date_match = date_pattern.search(f)
            timestamp = date_match.group(1) if date_match else None
            enriched_manifest.append({
                "path": full_path,
                "host": host,
                "log_type": log_type,
                "timestamp": timestamp
            })

    manifest_path = Path(output_path) / "converted_files.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(enriched_manifest, mf, indent=2)
    logging.info(f"Enriched manifest saved to: {manifest_path}")
    return manifest_path

def convert_logs(*, source_path, output_path, output_type="flat", use_streamlit=False, log_file_path=None):
    """Convert downloaded Blackboard logs into flat format."""
    os.makedirs(output_path, exist_ok=True)
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

    decompressed_files = []
    for i, f in enumerate(all_files):
        decompressed = decompress_file(f)
        decompressed_files.append(decompressed)
        if use_streamlit and total_files > 0:
            progress_bar.progress(min((i + 1) / total_files, 1.0))

    convert_flat_or_legacy(decompressed_files, output_path, output_type)

    manifest_path = generate_enriched_manifest(output_path)

    logger.info("=== Conversion Completed ===")
    logger.info(f"Total files converted: {len(decompressed_files)}")
    logger.info(f"Execution log saved to: {log_file_path}")
    logger.info(f"JSON manifest saved to: {manifest_path}")

    if use_streamlit:
        st.success(f"Conversion finished for {total_files} files.")
        st.text(f"Execution log saved to: {log_file_path}")
        st.text(f"JSON manifest saved to: {manifest_path}")
