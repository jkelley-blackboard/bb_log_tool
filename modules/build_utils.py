# modules/build_utils.py
from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional, Iterable

import pandas as pd

from modules.parser_utils import parse_log_entry, get_log_type_from_filename

# ===========================
# Logging
# ===========================

def setup_logger(log_file_path: Optional[str] = None):
    if log_file_path is None:
        log_file_path = f"./tool_logs/build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    logger = logging.getLogger("bb_build")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
        sh = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(fmt); sh.setFormatter(fmt)
        logger.addHandler(fh); logger.addHandler(sh)
    return logger

logger = setup_logger()

# ===========================
# Path normalization & index reading
# ===========================

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

    # Repo-root relative? (common for indexes that start with bb_logs/...)
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

# ===========================
# Explicit selection helpers
# ===========================

def normalize_dir(path_str: str) -> Tuple[bool, Optional[Path], str]:
    try:
        if not path_str:
            return False, None, "Empty path."
        p = Path(os.path.expandvars(path_str)).expanduser()
        p = p.resolve()
        if not p.exists():
            return False, None, f"Path does not exist: {p}"
        if not p.is_dir():
            return False, None, f"Path is not a directory: {p}"
        return True, p, f"OK: {p}"
    except Exception as ex:
        return False, None, f"Error normalizing path: {ex}"


def list_first_level_subdirs(root_dir: Path) -> List[Path]:
    subs: List[Path] = []
    try:
        for item in root_dir.iterdir():
            if item.is_dir():
                subs.append(item)
    except Exception:
        return []
    return sorted(subs, key=lambda p: p.name.lower())


def validate_conversion_run_dir(run_dir: Path) -> Dict[str, Any]:
    idx_path = run_dir / "converted_files.json"
    report: Dict[str, Any] = {
        "run_dir": str(run_dir),
        "idx_path": str(idx_path),
        "idx_exists": idx_path.exists(),
        "idx_entries": 0,
        "missing_files": [],
        "outside_files": [],
        "extra_json_files": [],
        "ok": False,
        "error": None,
    }
    if not idx_path.exists():
        report["error"] = "converted_files.json not found in the selected directory."
        return report

    try:
        idx = read_converted_index(str(idx_path))
        files = list(idx.get("files", []))
        report["idx_entries"] = len(files)

        idx_set = set(os.path.normpath(fp) for fp in files)
        base = os.path.normpath(str(run_dir))

        for fp in files:
            nf = os.path.normpath(fp)
            if not os.path.exists(nf):
                report["missing_files"].append(nf)
            if not nf.startswith(base + os.sep):
                report["outside_files"].append(nf)

        actual_jsons: List[str] = []
        for p in run_dir.rglob("*.json"):
            if p.name == "converted_files.json":
                continue
            actual_jsons.append(os.path.normpath(str(p)))
        actual_set = set(actual_jsons)
        extra = sorted(actual_set - idx_set)
        report["extra_json_files"] = extra

        report["ok"] = report["idx_exists"] and not report["missing_files"] and not report["outside_files"]
        return report
    except Exception as ex:
        report["error"] = f"Failed to read/validate index: {ex}"
        return report

# ===========================
# Inventory & file selection
# ===========================

def build_type_inventory(idx_path: str) -> Tuple[Dict[str, List[str]], List[str], List[str]]:
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


def filter_converted_files_by_type_and_dir(converted_file_path: str, selected_dir: str, selected_type: str) -> List[str]:
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

# ===========================
# Streaming JSON reader (for json-distributed)
# ===========================

def _iter_json_records(fh) -> Iterable[dict]:
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

# ===========================
# Session-scoped DuckDB build
# ===========================

import uuid, hashlib, time

def get_or_create_session_id() -> str:
    return os.environ.get("BB_SEARCH_SESSION_ID") or str(uuid.uuid4())


def _default_db_path(conv_dir: str, log_type: str, session_id: Optional[str] = None) -> Path:
    sid = session_id or get_or_create_session_id()
    return Path(conv_dir) / ".searchdb" / sid / f"{log_type}.duckdb"


def _ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def _hash_event(source_file: str, line_no: Optional[int], ts: Any, message: str) -> str:
    h = hashlib.blake2s(digest_size=16)
    h.update((source_file or "").encode("utf-8", "ignore"))
    h.update(str(line_no or "").encode("utf-8"))
    h.update(str(ts or "").encode("utf-8"))
    h.update((message or "").encode("utf-8", "ignore"))
    return h.hexdigest()


def create_or_overwrite_search_db(
    conv_dir: str,
    log_type: str,
    files: List[str],
    *,
    include_noisy: bool = False,
    db_path: Optional[str] = None,
    batch_rows: int = 100_000,
) -> Dict[str, Any]:
    import duckdb  # runtime import

    out_path = Path(db_path) if db_path else _default_db_path(conv_dir, log_type, None)
    _ensure_dir(out_path)

    t0 = time.time()
    if out_path.exists():
        out_path.unlink()

    con = duckdb.connect(str(out_path))

    con.execute("""
        CREATE TABLE events (
            event_id       TEXT PRIMARY KEY,
            ts             TIMESTAMP,
            log_type       TEXT,
            host           TEXT,
            user_id        TEXT,
            course_id      TEXT,
            endpoint       TEXT,
            status         TEXT,
            severity       TEXT,
            message        TEXT,
            is_noise       BOOLEAN,
            source_file    TEXT,
            source_line    BIGINT
        )
    """)

    total_rows = 0
    batch: List[Dict[str, Any]] = []

    for f in files:
        line_no = 0
        try:
            with open(f, "r", encoding="utf-8") as fh:
                for rec in _iter_json_records(fh):
                    line_no += 1
                    parsed = parse_log_entry(rec, log_type, file_path=f)
                    if parsed is None and not include_noisy:
                        continue
                    row = parsed if parsed is not None else rec
                    ts = row.get("timestamp")
                    msg = row.get("raw_message") or row.get("message") or ""
                    ev_id = _hash_event(f, line_no, ts, msg)
                    batch.append({
                        "event_id": ev_id,
                        "ts": ts,
                        "log_type": log_type,
                        "host": row.get("host"),
                        "user_id": row.get("user") or row.get("duser") or row.get("user_id"),
                        "course_id": row.get("course_id"),
                        "endpoint": row.get("path"),
                        "status": row.get("status"),
                        "severity": row.get("sev") or row.get("level"),
                        "message": msg,
                        "is_noise": parsed is None,
                        "source_file": f,
                        "source_line": line_no
                    })
                    if len(batch) >= batch_rows:
                        df = pd.DataFrame(batch)
                        con.execute("INSERT INTO events SELECT * FROM df")
                        total_rows += len(df)
                        batch.clear()
        except Exception as ex:
            logger.error(f"Failed to load {f}: {ex}")

    if batch:
        df = pd.DataFrame(batch)
        con.execute("INSERT INTO events SELECT * FROM df")
        total_rows += len(df)
        batch.clear()

    # Optional: FTS index over message
    try:
        con.execute("INSTALL fts; LOAD fts;")
        con.execute("PRAGMA create_fts_index('events','event_id','message',stemmer='porter',stopwords='english',overwrite=1)")
        fts_built = True
    except Exception as ex:
        logger.warning(f"FTS not built: {ex}")
        fts_built = False

    # Meta
    con.execute("""
        CREATE TABLE IF NOT EXISTS meta(
            created_at TIMESTAMP, conv_dir TEXT, log_type TEXT,
            file_count BIGINT, row_count BIGINT, include_noisy BOOLEAN, fts BOOLEAN
        )
    """)
    con.execute(
        "INSERT INTO meta VALUES (now(), ?, ?, ?, ?, ?, ?)",
        [str(conv_dir), log_type, len(files), total_rows, include_noisy, fts_built]
    )
    con.close()

    return {
        "db_path": str(out_path),
        "row_count": total_rows,
        "file_count": len(files),
        "seconds": round(time.time() - t0, 2),
        "fts": fts_built,
    }
