# Streamlit App

A lightweight, Streamlit-based utility for **downloading**, **converting**, and **analyzing** Blackboard session logs.

---

## ✨ What it does

- **Download**: Authenticates and collects the .gz logs based on time/date range inputs.  Dry run option calculates total file size and time to download approximation.

- **Convert**: Decompresses/converts the downloaded `.txt`/`.gz` logs into per-host, per-path text files mirroring the Blackboard server's own log layout, and generates an **enriched manifest** (`converted_files.json`) per conversion folder.

- **Analyze**: Presents simple counts by **host** and **log type** from `converted_files.json`, and lets you **download ZIPs** of files by host or log type.

---

## 🧱 Layout

```
bb_log_tool.py
pages/
  download.py
  convert.py
  analyze.py
modules/
  webdav_client.py
  download_utils.py
  convert_utils.py
  parser_utils.py
requirements.txt
```

Running the app creates these alongside it:

```
bb_logs/
  downloads/
    <hostabbr>_<YYYYMMDDHH_start>_<YYYYMMDDHH_end>/
      2026.2.5.14.ip-10-146-230-16.ec2.internal.txt  # original WebDAV filenames, unmodified
  conversions/
    <selected_download_subfolder>_convert/
      <host>/<original server path>/...              # per-host, per-path text logs
      converted_files.json
tool_logs/
  downloads_YYYYMMDD_HHMMSS.log
  converting_YYYYMMDD_HHMMSS.log
```

> The **Convert** page looks for subfolders under `bb_logs/downloads/` and writes its output to `bb_logs/conversions/<selected>_convert/`.

---

## 🚀 Quick Start

### 1) Install prerequisites (Python 3.11+ recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

> The app uses only local file I/O and WebDAV—no database required.

### 2) Run the app

```bash
streamlit run bb_log_tool.py
```

> Run it from inside this directory so the `bb_logs/` and `tool_logs/` output folders land here rather than at the repo root.

Streamlit will open a browser tab. Use the **sidebar** to navigate between:

- **Download Logs**
- **Convert Logs**
- **Analyze Logs**

---

## ⚙️ Usage

### A) Download Logs

1. **Host**: e.g., `https://nahe.blackboard.com`
2. **Username / Password**: WebDAV credentials for that host.
3. **Server Time Zone**: defaults to your local timezone; set this to the Blackboard server's timezone so the start/end hour selectors line up with the server's UTC offset.
4. **Start / End date and hour**: Defaults to the most recent hour that should be available (server time minus the ~4-hour log delay).
5. **Base Download Folder**: defaults to `./bb_logs/downloads`.

The remote path is hardcoded to `bbcswebdav/internal/logs/<year>/<month>/<day>/<hour>/` (see `modules/download_utils.py::build_remote_path`) — it is not user-configurable in the UI.

The tool will create a subfolder named:

```
<hostabbr>_<YYYYMMDDHH_start>_<YYYYMMDDHH_end>/
```

Files are saved into that folder under their original WebDAV filename — nothing is renamed, and no catalog/manifest file is written at download time (the manifest is generated later, at conversion time).

> Connection is verified via WebDAV root listing. If your environment uses different auth, adjust credentials in the **Download Logs** UI.

---

### B) Convert Logs (Flat Only)

1. Select a **downloaded subfolder** under `bb_logs/downloads`.
2. The page shows the **Final Conversion Folder** (e.g., `bb_logs/conversions/<selected>_convert`).
3. Click **Convert Logs**.

Outputs:
- **conversion folder**:
- **`converted_files.json`**: enriched manifest (path, host, log_type, timestamp)

> Gzipped (`.gz`) files are decompressed on the fly; originals are removed after decompression.

---

### C) Analyze Logs

1. Select a **conversion folder** (the `_convert` subfolder).
2. See summary tables:
   - Count by **Host**
   - Count by **Log Type**
3. Optionally download **ZIPs** of files by host or log type.

> By default the page builds ZIPs in memory (nothing touches disk). If `USE_IN_MEMORY_ZIP` in `pages/analyze.py` is set to `False`, ZIPs are written to `user_downloads/` instead, and a manual "Clear user_downloads ZIPs" button appears for housekeeping.

---

## 🔧 Configuration Notes

- **WebDAV client**: Uses `webdav3.client.Client` (`modules/webdav_client.py`).
  - The downloader calls `client.info()` per file to size it, then `client.download_sync(...)` when not in dry-run mode.
- **Remote path**: Hardcoded to `bbcswebdav/internal/logs/YYYY/MM/DD/HH/`, walked one hour at a time between the selected start/end. There is no folder-count or filename-pattern validation — a large date range just means more WebDAV `list()` calls.

---

## 🛠️ Troubleshooting

- **“Unable to connect to WebDAV”**
  Check host format (`https://...`), credentials, and whether your WebDAV root listing is permitted.

- **Download preview shows an old date**
  The destination folder preview is derived from Start/End date inputs and Host. Update inputs and the preview updates immediately.

- **Convert doesn’t list my downloaded folder**
  Ensure the Download page wrote into `./bb_logs/downloads/<subfolder>/`. The Convert page lists first-level subfolders under `bb_logs/downloads/`.

---

## 🧪 Development Tips

- **Reset session**: Use the sidebar “Utilities → Reset session” to clear `st.session_state`.
- **Logs**: See `./tool_logs/downloads_*.log` and `./tool_logs/converting_*.log`.
- **Package imports**: Both `modules/` and `pages/` include `__init__.py` so dynamic imports work.

---

## 📦 Requirements

See `requirements.txt` for installable packages. The tool assumes **Python 3.11+**.
