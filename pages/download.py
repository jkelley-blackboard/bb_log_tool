import streamlit as st
from datetime import datetime, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, available_timezones
import tzlocal
import os
import shutil
import requests
import re
import logging

from modules.webdav_client import get_client, test_connection
from modules.download_utils import (
    list_files_by_datetime,
    download_files,
    estimate_total_download_time
)

def run():
    st.set_page_config(page_title="BB Log Downloader", layout="wide")
    st.header("Blackboard Log Tools")
    st.subheader("⚙️ Download Blackboard Logs")

    # Detect user's local timezone
    try:
        local_tz_name = tzlocal.get_localzone_name()
    except:
        local_tz_name = "UTC"

    # --- Columns ---
    left_col, right_col = st.columns([2, 3])

    # ==========================
    # LEFT COLUMN - INPUTS
    # ==========================
    with left_col:
        # --- Host / Username / Password ---
        host_col, user_col, pw_col = st.columns([3, 2, 2])
        host_input = host_col.text_input("Host", value=st.session_state.get("host", "https://"),
            help="Enter the Blackboard server URL. Ex: https://myuni.blackboard.com")
        user_input = user_col.text_input("Username", value=st.session_state.get("username", ""))
        pw_input = pw_col.text_input("Password", type="password", value="")

        st.session_state["host"] = host_input
        st.session_state["username"] = user_input

        # --- Server Time Zone ---
        tz_col = st.selectbox(
            "Server Time Zone",
            sorted(available_timezones()),
            index=sorted(available_timezones()).index(local_tz_name)
            if local_tz_name in available_timezones() else sorted(available_timezones()).index("UTC"),
            help="Defaults to your local time. Adjust as needed."
        )
        server_tz = ZoneInfo(tz_col)

        # --- Start / End Date and Hour ---
        now_server = datetime.now(server_tz)
        default_end = now_server - timedelta(hours=4)  # 4-hour log availability delay
        default_start = default_end - timedelta(hours=1)

        start_date_col, start_hour_col = st.columns([2, 1])
        start_date = start_date_col.date_input("Start Date", value=default_start.date())
        start_hour_str = start_hour_col.selectbox(
            "Hour", [f"{h:02d}:00" for h in range(24)], index=default_start.hour, key="start_hour",
            help="Include all logs from this hour"
        )
        start_hour = int(start_hour_str.split(":")[0])

        end_date_col, end_hour_col = st.columns([2, 1])
        end_date = end_date_col.date_input("End Date", value=default_end.date())
        end_hour_str = end_hour_col.selectbox(
            "Hour", [f"{h:02d}:00" for h in range(24)], index=default_end.hour, key="end_hour",
            help="Newest logs are four hours old."
        )
        end_hour = int(end_hour_str.split(":")[0])

        # Build timezone-aware server-local datetimes
        start_dt_server = datetime(start_date.year, start_date.month, start_date.day, start_hour, tzinfo=server_tz)
        end_dt_server = datetime(end_date.year, end_date.month, end_date.day, end_hour, tzinfo=server_tz)

        # Validate end >= start
        if end_dt_server < start_dt_server:
            st.error("End time must be the same as or after Start time (server timezone).")

        # --- Dry Run ---
        dry_run = st.checkbox("Dry Run (no files downloaded)", value=True)

        # --- Custom Download Root Folder ---
        default_download_root = "./bb_logs/downloads"
        download_root = st.text_input(
            "Base Download Folder",
            value=default_download_root,
            help="Base folder where logs will be stored. A subfolder will be generated automatically."
        )

        # --- Calculate Destination Folder Name ---
        parsed = urlparse(host_input)
        host_only = parsed.hostname if parsed.hostname else host_input
        host_abbr = host_only.split('.')[0]  # Shortened host name for folder name

        start_str = start_dt_server.astimezone(ZoneInfo("UTC")).strftime('%Y%m%d%H')
        end_str = end_dt_server.astimezone(ZoneInfo("UTC")).strftime('%Y%m%d%H')
        auto_subfolder_name = f"{host_abbr}_{start_str}_{end_str}"
        final_download_path = os.path.join(download_root, auto_subfolder_name)

        st.markdown(f"**Final Destination Folder:** `{final_download_path}`")

        # --- Action buttons ---
        button_col_left, button_col_right = st.columns([1, 1])
        list_download_btn = button_col_left.button("List or Download Files", use_container_width=True)
        clear_downloads_btn = button_col_right.button("Clear All Downloads", use_container_width=True,
                                                      help="Deletes the entire base download folder and all subfolders.")

        st.markdown("""
            <div style="background-color:#f0f0f0; padding:10px; border-radius:5px;">
            <b>Help / Tips:</b><br>
            - Ensure the host includes the proper domain.<br>
            - Logs become available 4 hours after the hour ends.<br>
            - Select the correct server timezone to match Blackboard.<br>
            - Use Dry Run first to confirm files before downloading.<br>
            - The Final Destination Folder shows where files will be stored.<br>
            </div>
            """, unsafe_allow_html=True)

    # ==========================
    # RIGHT COLUMN - OUTPUT
    # ==========================
    with right_col:
        st.markdown('<div class="right-column">', unsafe_allow_html=True)

        # Health Check
        if host_input:
            health_url = host_input.rstrip("/") + "/webapps/portal/healthCheck"
            try:
                resp = requests.get(health_url, timeout=5)
                resp.raise_for_status()
                match = re.search(r"Time of request:\s*(.+)", resp.text)
                if match:
                    server_time_str = match.group(1).strip()
                    st.info(f"Current Server Time = {server_time_str}")
                else:
                    st.warning("Unable to detect server time from healthCheck.")
            except Exception as e:
                st.warning(f"Could not retrieve server time: {e}")

        if list_download_btn:
            # --- WebDAV Client ---
            client = get_client(host_input, user_input, pw_input)
            ok = test_connection(client)
            if ok is not True:
                st.error(f"WebDAV authentication failed: {ok[1]}")
                st.stop()

            # Convert server-local start/end to UTC
            start_dt_utc = start_dt_server.astimezone(ZoneInfo("UTC")).replace(minute=0, second=0, microsecond=0)
            end_dt_utc_inclusive = end_dt_server.astimezone(ZoneInfo("UTC")).replace(minute=0, second=0, microsecond=0)

            # List files
            end_for_query = end_dt_utc_inclusive + timedelta(hours=1)
            with st.spinner("Processing..."):
                files, missing_dirs = list_files_by_datetime(client, start_dt_utc, end_for_query, 0)
                total_size = sum(int(client.info(f).get("size", 0)) for f in files) if not dry_run else None
                est_time = estimate_total_download_time(client, files) if dry_run and files else None

            server_offset_hours = start_dt_server.utcoffset().total_seconds() / 3600
            st.markdown(f"**Server Time ({tz_col} UTC {int(server_offset_hours):+d})**")
            st.markdown(
                f"**Selected Range:** {start_dt_server.strftime('%Y-%m-%d %H:%M')} → "
                f"{end_dt_server.strftime('%Y-%m-%d %H:%M')}"
            )

            st.success(f"Total files found: {len(files)}")
            if total_size is not None:
                st.success(f"Total size: {total_size / 1_048_576:.2f} MB")

            if est_time:
                minutes = int(est_time["estimated_seconds"] // 60)
                seconds = int(est_time["estimated_seconds"] % 60)
                st.info(
                    f"**Estimated total size:** {est_time['total_size_mb']:.2f} MB\n\n"
                    f"**Estimated download time:** {minutes} minutes {seconds} seconds"
                )

            if missing_dirs:
                st.warning(f"Missing folders: {missing_dirs}")

            # --- Create Final Destination Folder ---
            os.makedirs(final_download_path, exist_ok=True)

            if not dry_run and files:
                with st.spinner("Downloading files..."):
                    processed_files, _ = download_files(client, files, final_download_path, dry_run=False)
                st.success(f"Files downloaded to: `{final_download_path}`")

            # --- Execution Log ---
            os.makedirs("./tool_logs", exist_ok=True)
            log_file = f"./tool_logs/downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            logging.basicConfig(filename=log_file,
                                level=logging.INFO,
                                format='%(asctime)s [%(levelname)s] %(message)s')
            logging.info("=== Blackboard Log Downloader Run ===")
            logging.info(f"Host: {host_input}")
            logging.info(f"Username: {user_input[:2]}***")  # mask username
            logging.info(f"Server TZ: {tz_col}")
            logging.info(f"Range: {start_dt_server} → {end_dt_server}")
            logging.info(f"Dry run: {dry_run}")
            logging.info(f"Files found: {len(files)}")
            logging.info(f"Missing directories: {missing_dirs}")
            logging.info(f"Download folder: {final_download_path if not dry_run else 'N/A'}")

        # --- Clear downloads ---
        if clear_downloads_btn:
            if os.path.exists(download_root):
                try:
                    # Iterate over all items in the download root
                    for filename in os.listdir(download_root):
                        file_path = os.path.join(download_root, filename)
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)  # remove file or link
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)  # remove subdirectory
                    st.success(f"All downloads cleared from: {download_root}")
                except Exception as e:
                    st.error(f"Failed to clear downloads: {e}")
            else:
                st.warning("No download folder found to clear.")

        st.markdown('</div>', unsafe_allow_html=True)
