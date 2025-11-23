# analyze_utils.py — Minimal utilities for log analysis

import json
from pathlib import Path
from collections import Counter
from zipfile import ZipFile
from typing import List
import pandas as pd

def load_manifest(manifest_path):
    """Load converted_files.json and return list of file paths."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

def create_zip(zip_path: Path, file_list: List[str]):
    """Create a zip file from a list of file paths."""
    with ZipFile(zip_path, 'w') as zipf:
        for file in file_list:
            if Path(file).exists():
                zipf.write(file, arcname=Path(file).name)

def summarize_by_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Summarize file counts by a given column."""
    summary_df = df[column].value_counts().reset_index()
    summary_df.columns = [column.capitalize(), "File Count"]
    return summary_df