# ./modules/search_utils.py
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from modules.parser_utils import parse_log_entry, get_log_type_from_filename

# Setup logging
# Configure and return a logger instance
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

# Load and parse log entries from a list of log files using parser_utils
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

# Filter parsed log entries based on field values and timestamp range
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

# Filter converted files based on selected directory and log type
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
    
def get_conversion_subdirs_with_metadata(source_path):
    """
    Given a source path, return a list of subdirectories that contain a valid converted_files.json,
    along with their parsed metadata.

    Args:
        source_path (str): The base directory to search for conversion subdirectories.

    Returns:
        List[Tuple[str, dict]]: A list of tuples containing the subdirectory path and parsed JSON metadata.
    """
    logger.info("Starting get_conversion_subdirs_with_metadata")
    logger.info(f"Checking source path: {source_path}")

    valid_subdirs = []

    # Check if the source path is a valid directory
    if not os.path.isdir(source_path):
        logger.warning(f"Provided source path is not a directory: {source_path}")
        return []

    # Iterate through subdirectories in the source path
    for subdir in os.listdir(source_path):
        full_path = os.path.join(source_path, subdir)
        logger.info(f"Evaluating subdirectory: {full_path}")

        if os.path.isdir(full_path):
            json_path = os.path.join(full_path, "converted_files.json")
            if os.path.exists(json_path):
                logger.info(f"Found converted_files.json in: {full_path}")
                try:
                    with open(json_path, "r") as f:
                        converted_data = json.load(f)
                    valid_subdirs.append((full_path, converted_data))
                except Exception as e:
                    logger.error(f"Error reading {json_path}: {e}")
            else:
                logger.info(f"No converted_files.json found in: {full_path}")

    logger.info(f"Completed search. Found {len(valid_subdirs)} valid subdirectories.")
    return valid_subdirs
