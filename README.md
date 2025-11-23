# Blackboard Log Converter Tool

This is a Python-based Streamlit application designed to simplify the processing and analysis of Blackboard Learn log files.

## 🚀 Overview

The application consists of three main components:

1. **Log Package Downloader**
   - Uses WebDAV to connect to a Blackboard deployment.
   - Downloads log packages based on a user-specified date range.

2. **Log Conversion**
   - Converts downloaded logs into flattened text fileskey-value structure.
     - (considering work to build other formats)

3. **Search and Filtering**
   - Provides various search methods tailored to the selected format and log type.
   - Enables host filtering and keyword-based queries.

## 🛠 Technologies Used

- Python
- Streamlit
- WebDAV client
- Anthology's `convertlogs.py` module

# BB Log Search — Session DB (DuckDB) Add‑On


## What you get
- Two‑column **Streamlit page** (`pages/search.py`) that:
  - Discovers runs via `converted_files.json`
  - Builds a **type inventory** before enabling the log type selector
  - Provides a **Create / Overwrite search database** button
  - Runs **structured queries** and optional **FTS (free‑text)** queries against the DB
- Utilities in `modules/search_utils.py` to:
  - Read the index robustly (JSON or whitespace list)
  - Build inventories by log type
  - Parse json‑distributed logs into a **DuckDB** file (`.searchdb/<session>/<log_type>.duckdb`)
  - Query the DB with structured filters or BM25 (FTS)
- Updated `modules/parser_utils.py` filename patterns to recognize your converted JSON names



## How it works
1. Pick a **conversion directory** (must contain `converted_files.json`).
2. The page scans the index to build a **type inventory** (no file I/O yet).
3. Pick a **log type** → click **Create / Overwrite search database**.
   - This parses the selected files once and writes a session DB here:
     ```
     <conversion_dir>/.searchdb/<session_id>/<log_type>.duckdb
     ```
   - It also tries to build a small **FTS index** over `message`.
4. Run **Structured** or **FTS** searches against the DB.

## Notes
- The DB is **session‑specific** to avoid collisions; feel free to pin a session id via `BB_SEARCH_SESSION_ID` env var if needed.
- For very large runs, consider building only a date window or moving to a Parquet‑backed design later. The current approach is optimized for fast, local exploration with minimal setup.
