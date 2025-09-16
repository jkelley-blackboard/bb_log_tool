import json
import logging
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Default output base (can be overridden externally)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_base = Path.cwd() / f"indiv_converts_{timestamp}"

# Use module logger (no file handlers created here)
logger = logging.getLogger(__name__)

def normalize_filename(name: str) -> str:
    return re.sub(r'\W+', '_', name).strip("_") + ".json"

def convert_logs(file_path):
    """
    Process a single JSON log file and output grouped JSON files by host and path.
    Returns a list (relative to output_base) of files created by this run.
    """
    bad_lines = []
    summary = defaultdict(int)
    created_files = []

    try:
        with file_path.open("r", encoding="utf-8") as f:
            writers = {}
            first_entry = {}
            buffer = ""

            for lineno, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue

                buffer += stripped

                # Not a json object start -> bad line, reset buffer
                if not buffer.startswith("{"):
                    bad_lines.append((lineno, buffer))
                    buffer = ""
                    continue

                # Wait until buffer ends with '}' to attempt parse
                if not buffer.endswith("}"):
                    continue

                # Try parse
                try:
                    record = json.loads(buffer)
                    buffer = ""
                except json.JSONDecodeError:
                    bad_lines.append((lineno, buffer))
                    buffer = ""
                    continue

                # Validate required fields
                if not all(k in record for k in ("message", "path", "host")):
                    bad_lines.append((lineno, json.dumps(record)))
                    continue

                # Remove BOM if present in first message
                if lineno == 1 and isinstance(record["message"], str):
                    record["message"] = record["message"].lstrip('\ufeff')

                host = record["host"]
                # Normalize path relative to a base prefix if present
                rel_path = Path(record["path"].replace("/usr/local/blackboard/", ""))
                dest_folder = output_base / host / rel_path.parent
                dest_folder.mkdir(parents=True, exist_ok=True)
                dest_file = dest_folder / normalize_filename(rel_path.name)

                try:
                    if dest_file not in writers:
                        f_handle = dest_file.open("w", encoding="utf-8")
                        f_handle.write("[\n")
                        writers[dest_file] = f_handle
                        first_entry[dest_file] = True
                        # Record the created file relative to output_base
                        try:
                            created_files.append(str(dest_file.relative_to(output_base)))
                        except Exception:
                            # fallback to absolute if relative fails
                            created_files.append(str(dest_file))

                    summary[host] += 1
                    f_handle = writers[dest_file]

                    if not first_entry[dest_file]:
                        f_handle.write(",\n")

                    f_handle.write(json.dumps({
                        "message": record["message"],
                        "path": record["path"],
                        "host": record["host"]
                    }))
                    first_entry[dest_file] = False

                except Exception as e:
                    bad_lines.append((lineno, json.dumps(record)))
                    logger.exception("Error writing line %s for file %s: %s", lineno, file_path, e)

            # Close all writer handles
            for f_handle in writers.values():
                try:
                    f_handle.write("\n]\n")
                    f_handle.close()
                except Exception:
                    logger.exception("Failed closing writer handle")

    except Exception as e:
        # Log full stack trace and return empty list to indicate failure for this file
        logger.exception("Failed to process file %s: %s", file_path, e)
        return []

    # Emit summary info to shared logger (no file handlers created here)
    logger.info("=== json-distributed Conversion Completed for file: %s ===", file_path)
    for host, count in summary.items():
        logger.info("%s: %s entries", host, count)

    if bad_lines:
        logger.info("=== Bad Lines Report (first 10) ===")
        for lineno, content in bad_lines[:10]:
            logger.info("  Line %s: %s", lineno, content)
        logger.info("Total bad lines: %s", len(bad_lines))
    else:
        logger.info("No bad lines encountered.")

    return created_files
