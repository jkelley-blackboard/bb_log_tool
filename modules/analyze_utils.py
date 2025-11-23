# modules/analyze_utils.py
"""
Utilities for Analyze page:
- load_manifest: read converted_files.json
- create_zip: create a ZIP on disk under user_downloads
- summarize_by_column: return a simple counts dataframe
"""
import json
from pathlib import Path
from zipfile import ZipFile
from typing import List
import pandas as pd


def load_manifest(manifest_path: Path | str):
    """Load converted_files.json and return the parsed JSON."""
    p = Path(manifest_path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def create_zip(zip_path: Path, file_list: List[str]) -> Path:
    """
    Create a zip file on disk from a list of file paths.
    Returns the path to the created ZIP.
    """
    zip_path.parent.mkdir(exist_ok=True)
    with ZipFile(zip_path, "w") as zipf:
        for file in file_list:
            fp = Path(file)
            if fp.exists():
                zipf.write(fp, arcname=fp.name)
    return zip_path


def summarize_by_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Summarize file counts by a given column."""
    summary_df = df[column].value_counts().reset_index()
    summary_df.columns = [column.capitalize(), "File Count"]
    return summary_df
