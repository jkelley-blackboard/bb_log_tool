# ./modules/search_utils.py
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from modules.parser_utils import parse_log_entry, get_log_type_from_filename

# Setup logging
def setup_logger(log_file_path=None):
    if log_file_path is None:
        log_file_path = f"./tool_logs/searching_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file_path, mode='w'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

def list_log_directories(base_dir="./bb_logs/conversions"):
    logger.info(f"Scanning for log directories in base directory: {base_dir}")
    if not os.path.exists(base_dir):
        logger.warning(f"Base directory does not exist: {base_dir}")
        return []
    dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    dirs.sort()
    logger.info(f"Found {len(dirs)} subdirectories.")
    return dirs

def find_log_files(log_dir, log_type=None):
    logger.info(f"Searching for log files in directory: {log_dir} with log_type: {log_type}")
    matches = []
    for root, _, files in os.walk(log_dir):
        for f in files:
            if f.endswith(".json"):
                if log_type is None or log_type.lower() in f.lower():
                    matches.append(os.path.join(root, f))
    matches.sort()
    logger.info(f"Found {len(matches)} matching log files.")
    return matches

def load_and_parse_logs(log_files, log_type):
    logger.info(f"Loading and parsing {len(log_files)} log files for log_type: {log_type}")
    parsed_entries = []
    for f in log_files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                entries = json.load(fh)
                for e in entries:
                    parsed = parse_log_entry(e, log_type, file_path=f)
                    if parsed is not None:
                        parsed_entries.append(parsed)
        except Exception as ex:
            logger.error(f"Failed to load {f}: {ex}")
    logger.info(f"Parsed {len(parsed_entries)} entries successfully.")
    return parsed_entries

def filter_logs(parsed_entries, filters=None, start_ts=None, end_ts=None):
    logger.info(f"Filtering {len(parsed_entries)} entries with filters: {filters}, start_ts: {start_ts}, end_ts: {end_ts}")
    results = []
    for entry in parsed_entries:
        ts = entry.get("timestamp")
        if ts and start_ts and ts < start_ts:
            continue
        if ts and end_ts and ts > end_ts:
            continue
        if filters:
            match = all(str(entry.get(k, "")).lower().find(str(v).lower()) != -1 for k, v in filters.items() if v)
            if not match:
                continue
        results.append(entry)
    logger.info(f"{len(results)} entries matched the filters.")
    return results

def filter_converted_files_by_type_and_dir(converted_file_path, selected_dir, selected_type):
    logger.info(f"Filtering converted files from: {converted_file_path} for directory: {selected_dir} and log_type: {selected_type}")
    try:
        with open(converted_file_path, "r", encoding="utf-8") as f:
            all_files = f.read().split()
    except Exception as e:
        logger.error(f"Error loading {converted_file_path}: {e}")
        return []

    matching_files = []
    for f in all_files:
        normalized_path = os.path.normpath(f)
        if normalized_path.startswith(os.path.normpath(selected_dir)):
            log_type = get_log_type_from_filename(Path(f).name)
            if log_type == selected_type:
                matching_files.append(normalized_path)

    logger.info(f"Found {len(matching_files)} matching files.")
    return matching_files

def find_converted_directories(base_dir="./bb_logs/conversions"):
    logger.info(f"Scanning for converted directories in base directory: {base_dir}")
    results = []
    if not os.path.exists(base_dir):
        logger.warning(f"Base directory does not exist: {base_dir}")
        return results

    for subdir in os.listdir(base_dir):
        full_path = os.path.join(base_dir, subdir)
        logger.debug(f"Checking subdir: {full_path}")
        if os.path.isdir(full_path):
            converted_path = os.path.join(full_path, "converted_files.json")
            if os.path.isfile(converted_path):
                logger.info(f"Found converted_files.json in: {full_path}")
                results.append((full_path, converted_path))
            else:
                logger.debug(f"No converted_files.json in: {full_path}")
        else:
            logger.debug(f"Skipping non-directory: {full_path}")

    logger.info(f"Found {len(results)} converted directories.")
    return results
