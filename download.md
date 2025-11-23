## 📄 `download.py` — Streamlit GUI for Blackboard Log Downloads

### Overview
This module provides a user-friendly Streamlit interface for downloading Blackboard session logs via WebDAV. It supports timezone-aware date range selection, dry-run previews, and automatic folder naming based on host and time range.

### Features
- Streamlit-based GUI with two-column layout
- Timezone detection and selection
- Start/end date and hour inputs
- Dry run mode to preview files before downloading
- Automatic folder naming using host and UTC timestamps
- Health check via `/webapps/portal/healthCheck`
- Download logs using WebDAV
- Execution logging to `./tool_logs`
- Folder clearing with locked file detection

### Usage
Run the Streamlit app:

```bash
streamlit run download.py
```

### Dependencies
- `streamlit`
- `requests`
- `tzlocal`
- `zoneinfo`
- `webdav3`
- `logging`
- `shutil`, `os`, `datetime`, `re`

### Notes
- Logs are available ~4 hours after creation.
- Downloaded logs are stored in `./bb_logs/downloads/{host}_{start}_{end}`.
- Clearing the download folder skips locked files and reports them.

---

## 📄 `download_utils.py` — WebDAV Utilities for Log Management

### Overview
This module provides backend utilities for listing, downloading, and estimating download time for Blackboard logs stored on a WebDAV server.

### Functions

#### `build_remote_path(dt, offset_hours=4)`
Generates a WebDAV folder path based on a datetime and offset.

#### `list_files_by_datetime(client, start_dt, end_dt, offset_hours=4)`
Lists all files between two datetimes, returning both found files and missing directories.

#### `download_files(client, files, download_dir, dry_run=True)`
Downloads files to a local folder. Supports dry-run mode for previewing.

#### `estimate_network_speed(client, file_path)`
Downloads a single file to a temp location to measure speed.

#### `estimate_total_download_time(client, files)`
Estimates total download time based on the first file's speed.

### Dependencies
- `os`, `time`, `tempfile`, `datetime`
- `webdav3.client.Client`

### Notes
- All downloads use `client.download_sync()` from `webdav3`.
- Dry-run mode avoids actual downloads but still calculates size and time.

