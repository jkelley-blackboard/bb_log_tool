## 📄 `convert.py` — Streamlit GUI for Blackboard Log Conversion

### Overview
This module provides a Streamlit interface for converting downloaded Blackboard logs into a flat format. It allows users to select a previously downloaded folder, specify a conversion destination, and initiate the conversion process with progress feedback and logging.

### Features
- Streamlit-based GUI with two-column layout
- Dropdown to select downloaded log folder
- Configurable conversion output folder
- Conversion to flat format using backend utilities
- Execution logging to `./tool_logs`
- Manifest generation (`converted_files.json`)
- Option to clear all converted folders

### Usage
Run the Streamlit app:

```bash
streamlit run convert.py
```

### Dependencies
- `streamlit`
- `os`, `shutil`, `datetime`
- `convert_utils.convert_logs`

### Notes
- Output format is currently fixed to `flat`.
- Converted logs are saved in `./bb_logs/conversions/{folder}_convert`.
- Manifest includes host, log type, and timestamp metadata.

---

## 📄 `convert_utils.py` — Log Conversion Utilities

### Overview
This module handles the backend logic for converting Blackboard logs from `.txt` or `.gz` format into a structured flat format. It supports decompression, conversion, metadata enrichment, and logging.

### Functions

#### `decompress_file(file_path)`
Decompresses `.gz` files and deletes the original. Returns the decompressed path.

#### `convert_flat_or_legacy(file_paths, output_dir, output_type)`
Uses `convertlogs.py` to convert each file into the specified format (currently flat only).

#### `generate_enriched_manifest(output_path)`
Creates a `converted_files.json` manifest with metadata:
- `path`: full file path
- `host`: extracted from filename
- `log_type`: detected via `parser_utils.detect_log_type`
- `timestamp`: extracted from filename

#### `convert_logs(...)`
Main entry point for conversion. Handles:
- Decompression
- Conversion
- Manifest generation
- Logging
- Optional Streamlit progress bar

### Dependencies
- `os`, `json`, `gzip`, `shutil`, `logging`, `re`, `datetime`, `pathlib`
- `streamlit` (optional)
- `parser_utils.detect_log_type`
- `convertlogs.FileWriter`, `convert_file`

### Notes
- Manifest is saved to `converted_files.json` in the output folder.
- Execution logs are saved to `./tool_logs`.