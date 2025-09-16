# modules/search_utils.py
from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional, Iterable

from modules.parser_utils import parse_log_entry, get_log_type_from_filename

# ----------------------------
# Logging
# ----------------------------
def setup_logger(log_file_path: Optional[str] = None):
    if log_file_path is None:
        log_file_path = f"./tool_logs/searching_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    logger = logging.getLogger("bb_search")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
        sh = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(fmt); sh.setFormatter(fmt)
        logger.addHandler(fh); logger.addHandler(sh)
    return logger

logger = setup_logger()

# ----------------------------
# Path normalization & index reading
# ----------------------------

def _norm_sep(p: str) -> str:
    """Normalize path separators and strip quotes."""
    p = p.strip().strip('"').strip("'")
    p = p.replace("\\", os.sep).replace("/", os.sep)
    return os.path.normpath(p)


def _abs_from_index_entry(entry: Any, base_dir: str) -> Optional[str]:
    """
    Resolve token from converted_files.json to an absolute, normalized path.
    Supports:
      - absolute paths
      - repo-root relative tokens starting with 'bb_logs/...'
      - paths already containing the run directory segment
      - run-relative tokens (default)
    """
    if isinstance(entry, str):
        p = entry
    elif isinstance(entry, dict):
        p = entry.get("path") or entry.get("file") or entry.get("filepath")
    else:
        return None
    if not p:
        return None

    p_norm = _norm_sep(str(p))
    if os.path.isabs(p_norm):
        return p_norm

    # Repo-root relative? (common in your sample)
    if p_norm.split(os.sep)[0].lower() == "bb_logs":
        return _norm_sep(os.path.join(os.getcwd(), p_norm))

    # If token already embeds the run folder, do NOT join with base_dir again
    run_name = os.path.basename(_norm_sep(base_dir))
    if run_name and (os.sep + run_name + os.sep) in (os.sep + p_norm + os.sep):
        return _norm_sep(os.path.join(os.getcwd(), p_norm))

    # Default: relative to run dir
    return _norm_sep(os.path.join(base_dir, p_norm))


def read_converted_index(converted_file_path: str) -> Dict[str, Any]:
    """
    Tolerant reader for converted_files.json. Supports:
      - JSON: { "files": [...]} or { "converted": [...] } or top-level list
      - Fallback: whitespace-separated paths
    Returns { "files": [abs_paths...], "raw": original_or_None }.
    """
    base_dir = os.path.dirname(converted_file_path)
    try:
        with open(converted_file_path, "r", encoding="utf-8") as f:
            text = f.read()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            tokens = re.split(r"\s+", text.strip())
            files = []
            for t in tokens:
                abs_p = _abs_from_index_entry(t, base_dir)
                if abs_p:
                    files.append(abs_p)
            return {"files": files, "raw": None}

        # JSON branch
        if isinstance(data, dict):
            items = data.get("files") or data.get("converted")
            if not isinstance(items, list):
                items = next((v for v in data.values() if isinstance(v, list)), [])
        elif isinstance(data, list):
            items = data
        else:
            items = []

        files = []
        for it in items:
            abs_p = _abs_from_index_entry(it, base_dir)
            if abs_p:
                files.append(abs_p)
        return {"files": files, "raw": data}

    except Exception as e:
        logger.error(f"Error reading index {converted_file_path}: {e}")
        return {"files": [], "raw": None}

# ----------------------------
# Discovery
# ----------------------------

def get_conversion_subdirs_with_metadata(source_path: str) -> List[Tuple[str, dict]]:
    """
    Recursively find subdirectories containing a converted_files.json.
    Returns a list of (dir_path, parsed_json_or_empty_dict), newest-first by index mtime.
    """
    logger.info(f"Starting recursive discovery under: {source_path}")
    if not os.path.isdir(source_path):
        logger.warning(f"Provided source path is not a directory: {source_path}")
        return []

    hits: List[Tuple[str, dict, float]] = []
    for root, _dirs, files in os.walk(source_path):
        if "converted_files.json" in files:
            idx_path = os.path.join(root, "converted_files.json")
            data = read_converted_index(idx_path).get("raw") or {}
            try:
                mtime = os.path.getmtime(idx_path)
            except Exception:
                mtime = 0.0
            hits.append((root, data, mtime))

    hits.sort(key=lambda t: t[2], reverse=True)
    logger.info(f"Found {len(hits)} conversion directories with converted_files.json")
    return [(d, data) for d, data, _ in hits]


def get_default_conversion_dir(source_path: str) -> Optional[str]:
    subdirs = get_conversion_subdirs_with_metadata(source_path)
    return subdirs[0][0] if subdirs else None

# ----------------------------
# Inventory (index-only)
# ----------------------------

def build_type_inventory(idx_path: str) -> Tuple[Dict[str, List[str]], List[str], List[str]]:
    """
    Build an inventory of files by inferred log type, using the index only.
    Does NOT open any log files.
    Returns:
      by_type:      {log_type: [file_path, ...]}
      unknown:      [file_path, ...]
      all_files:    [file_path, ...]
    """
    if not os.path.exists(idx_path):
        return {}, [], []

    out = read_converted_index(idx_path)
    files = list(out.get("files", []))

    by_type: Dict[str, List[str]] = {}
    unknown: List[str] = []
    for f in files:
        lt = get_log_type_from_filename(Path(f).name)
        if lt:
            by_type.setdefault(lt, []).append(f)
        else:
            unknown.append(f)

    for k in list(by_type.keys()):
        by_type[k] = sorted(set(by_type[k]))
    unknown = sorted(set(unknown))
    files = sorted(set(files))
    return by_type, unknown, files

# ----------------------------
# File selection
# ----------------------------

def filter_converted_files_by_type_and_dir(converted_file_path: str, selected_dir: str, selected_type: str) -> List[str]:
    """
    Return absolute paths of files within selected_dir that match the selected log type,
    based on filename mapping.
    """
    logger.info(f"Selecting files for type='{selected_type}' in '{selected_dir}' using index '{converted_file_path}'")
    files: List[str] = []
    if os.path.exists(converted_file_path):
        files = read_converted_index(converted_file_path)["files"]

    if not files:
        for root, _dirs, fnames in os.walk(selected_dir):
            for fn in fnames:
                if fn.lower().endswith(".json") and fn != "converted_files.json":
                    files.append(os.path.normpath(os.path.join(root, fn)))

    selected: List[str] = []
    base = os.path.normpath(selected_dir)
    for f in files:
        nf = os.path.normpath(f)
        if nf.startswith(base):
            lt = get_log_type_from_filename(Path(nf).name)
            if lt == selected_type:
                selected.append(nf)

    logger.info(f"Matched {len(selected)} files for type '{selected_type}'")
    return sorted(set(selected))

# ----------------------------
# Parsing & filtering
# ----------------------------

def _iter_json_records(fh) -> Iterable[dict]:
    """
    Yield JSON objects from a file handle that may contain:
      - a JSON array
      - a single JSON object
      - NDJSON (one JSON object per line)
    """
    pos = fh.tell()
    head = fh.read(2048)
    fh.seek(pos)

    stripped = head.lstrip()
    if stripped.startswith("["):
        data = json.load(fh)
        if isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict):
                    yield obj
        elif isinstance(data, dict):
            yield data
        return

    try:
        data = json.load(fh)
        if isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict):
                    yield obj
        elif isinstance(data, dict):
            yield data
        return
    except json.JSONDecodeError:
        fh.seek(0)
        for line in fh:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
            except json.JSONDecodeError:
                continue


def load_and_parse_logs(
    log_files: List[str],
    log_type: str,
    *,
    include_noisy: bool = False,
    max_records: Optional[int] = None,
) -> List[dict]:
    """
    Read + parse logs for the given type. Supports JSON array, object, or NDJSON.
    Returns parsed dicts; includes raw/noisy only if include_noisy=True.
    """
    logger.info(f"Loading {len(log_files)} files; log_type={log_type}; include_noisy={include_noisy}")
    out: List[dict] = []
    for f in log_files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                for rec in _iter_json_records(fh):
                    parsed = parse_log_entry(rec, log_type, file_path=f)
                    if parsed is None and not include_noisy:
                        continue
                    out.append(parsed if parsed is not None else rec)
                    if max_records and len(out) >= max_records:
                        break
        except Exception as ex:
            logger.error(f"Failed to load {f}: {ex}")
        if max_records and len(out) >= max_records:
            break

    logger.info(f"Parsed {len(out)} entries successfully.")
    return out


def filter_logs(parsed_entries: List[dict], filters: Optional[Dict[str, Any]] = None,
                start_ts: Optional[datetime] = None, end_ts: Optional[datetime] = None) -> List[dict]:
    """
    Substring filter across provided fields; optional timestamp range.
    """
    results: List[dict] = []
    for entry in parsed_entries:
        ts = entry.get("timestamp")
        if ts and start_ts and ts < start_ts:
            continue
        if ts and end_ts and ts > end_ts:
            continue
        if filters:
            matched = True
            for k, v in filters.items():
                if not v:
                    continue
                val = str(entry.get(k, "")).lower()
                if str(v).lower() not in val:
                    matched = False
                    break
            if not matched:
                continue
        results.append(entry)
    logger.info(f"{len(results)} entries matched the filters.")
    return results
