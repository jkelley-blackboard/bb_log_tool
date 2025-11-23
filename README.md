# Blackboard Log Tool (bb_log_tool)

A lightweight, Streamlit-based utility for **downloading**, **converting**, and **analyzing** Blackboard session logs.  

---

## ✨ What it does

- **Download**: Authenticates and collects the .gz logs based on time/date range inputs.  Dry run option calculates total file size and time to download approximation. 

- **Convert**: Converts the downloaded `.txt`/`.gz` logs into a **flat JSON Lines** file (`converted_flat.jsonl`) and generates an **enriched manifest** (`converted_files.json`) per conversion folder.

- **Analyze**: Presents simple counts by **host** and **log type** from `converted_files.json`, and lets you **download ZIPs** of files by host or log type.

---

## 🧱 Folder Structure

After running the app, you’ll typically see:

```
bb_logs/
  downloads/
    <hostabbr>_<YYMMDD_start>_<YYMMDD_end>/
      251123__6_1_1.log  # example file(s) renamed from sessiondebuglogs
      downloaded_catalog.json
  conversions/
    <selected_download_subfolder>_convert/
      converted_flat.jsonl
      converted_files.json
tool_logs/
  downloads_YYYYMMDD_HHMMSS.log
  converting_YYYYMMDD_HHMMSS.log
pages/
  download.py
  convert.py
  analyze.py
modules/
  webdav_client.py
  download_utils.py
  convert_utils.py
  parser_utils.py
bb_log_tool.py
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

Streamlit will open a browser tab. Use the **sidebar** to navigate between:

- **Download Logs**
- **Convert Logs**
- **Analyze Logs**

---

## ⚙️ Usage

### A) Download Logs

1. **Host**: e.g., `https://nahe.blackboard.com`  
2. **Base Path**: `/bbcswebdav/internal/sessiondebuglogs`  
3. **Start / End date**: Use calendar pickers (inclusive).
4. **Base Download Folder**: defaults to `./bb_logs/downloads`.

The tool will create a subfolder named:

```
<hostabbr>_<YYMMDD_start>_<YYMMDD_end>/
```

Inside that folder it will save:
- Renamed logs: `{YYMMDD}_{user_id}_{log_number}.log`
- **`downloaded_catalog.json`** (source/dest, simple header metadata)

> Connection is verified via WebDAV root listing. If your environment uses different auth or a non-standard path, adjust in **Download Logs** UI.

---

### B) Convert Logs (Flat Only)

1. Select a **downloaded subfolder** under `bb_logs/downloads`.
2. The page shows the **Final Conversion Folder** (e.g., `bb_logs/conversions/<selected>_convert`).
3. Click **Convert to Flat**.

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

> The page clears `user_downloads` ZIPs at session start for housekeeping.

---

## 🔧 Configuration Notes

- **WebDAV client**: Uses `webdav3.client.Client`.  
  - The downloader calls `client.download(remote_path=..., local_path=...)` and falls back to `client.download_sync(...)` if needed.
- **Date handling**: Dates are normalized to `datetime.date` to avoid comparison bugs.
- **YYMMDD folder validation**: Non-YYMMDD leaf names under `base_path` trigger an error (by design).
- **Max folders**: Defensively guards against >35 YYMMDD folders (per trust rule).

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
