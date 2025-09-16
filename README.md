# Blackboard Log Converter Tool

This is a Python-based Streamlit application designed to simplify the processing and analysis of Blackboard Learn log files.

## 🚀 Overview

The application consists of three main components:

1. **Log Package Downloader**
   - Uses WebDAV to connect to a Blackboard deployment.
   - Downloads log packages based on a user-specified date range.

2. **Log Conversion**
   - Converts downloaded logs into three formats:
     - `flat`: Flattened key-value structure.
     - `json-legacy`: JSON format using Anthology's `convertlogs.py` module.
     - `json-distributed`: Hybrid format (Work In Progress).

3. **Search and Filtering**
   - Provides various search methods tailored to the selected format and log type.
   - Enables host filtering and keyword-based queries.

## 🛠 Technologies Used

- Python
- Streamlit
- WebDAV client
- Anthology's `convertlogs.py` module

## 📦 Future Enhancements

- Complete implementation of `json-distributed` format.
- Advanced search capabilities across distributed logs.
- Export and visualization features.

