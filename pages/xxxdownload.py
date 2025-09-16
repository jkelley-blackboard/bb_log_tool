import streamlit as st
from datetime import datetime, timedelta
from modules.download_utils import list_files_by_datetime, download_files, estimate_total_download_time
import os
import shutil
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, available_timezones
import tzlocal  # pip install tzlocal
import requests
import re


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
    # LEFT COLUMN - INPUT & BUTTONS
    # ==========================
    with left_col:
        # --- Host / Username / Password ---
        host_col, user_col, pw_col = st.columns([3, 2, 2])
        host_input = host_col.text_input("Host", value=st.session_state.get("host", "https://"),
            help = "Enter the Blackboard server URL.  Ex  https://myuni.blackboard.com"
        )
        user_input = user_col.text_input("Username", value=st.session_state.get("username", ""))
        pw_input = pw_col.text_input("Password", type="password", value="")

        st.session_state["host"] = host_input
        st.session_state["username"] = user_input

        # --- Server Time Zone ---
        tz_col = st.selectbox(
            "Server Time Zone",
            sorted(available_timezones()),
            index=sorted(available_timezones()).index(local_tz_name)
            if local_tz_name in available_timezones()
            else sorted(available_timezones()).index("UTC"),
            help="Defaults to your local time.  Adjust as needed."
        )
        server_tz = ZoneInfo(tz_col)

        # --- Start / End Date and Hour on the same line ---
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

        # --- Action buttons ---
        button_col_left, button_col_right = st.columns([1, 1])
        list_download_btn = button_col_left.button("List or Download Files", use_container_width=True)
        clear_downloads_btn = button_col_right.button("Clear All Downloads", use_container_width=True,
            help="Deletes the entire download folder."
        )
        
        st.markdown("""
            <div style="background-color:#f0f0f0; padding:10px; border-radius:5px;">
            <b>Help / Tips:</b><br>
            - Make sure the host includes the proper domain.<br>
            - Logs are only available starting 4 hours after the hour ends.<br>
            - Select the server timezone to match Blackboard.<br>
            - Use Dry Run first to see what files will be downloaded.<br>
            </div>
            """, unsafe_allow_html=True)

    # ==========================
    # RIGHT COLUMN - OUTPUT
    # ==========================
    with right_col:
        st.markdown('<div class="right-column">', unsafe_allow_html=True)
        
        # After host_input is entered
        if host_input:
            health_url = host_input.rstrip("/") + "/webapps/portal/healthCheck"
            try:
                resp = requests.get(health_url, timeout=5)
                resp.raise_for_status()
                # Extract Time of request
                match = re.search(r"Time of request:\s*(.+)", resp.text)
                if match:
                    server_time_str = match.group(1).strip()
                    st.info(f"Current Server Time = {server_time_str}")
                else:
                    st.warning("Unable to detect server time from healthCheck.")
            except Exception as e:
                st.warning(f"Could not retrieve server time: {e}")

        if list_download_btn:
            # Ensure scheme prefix for host
            if not host_input.startswith("http"):
                host_input = "https://" + host_input

            client_config = {
                "webdav_hostname": host_input,
                "webdav_login": user_input,
                "webdav_password": pw_input,
            }

            from webdav3.client import Client

            # --- Validate WebDAV connection ---
            try:
                client = Client(client_config)
                # Test by requesting root directory
                client.list("/")
            except Exception as e:
                st.error(f"❌ WebDAV authentication failed: {e}")
                st.stop()  # Do not continue to folder listing or downloading

            # Convert server-local start/end to UTC for folder scanning
            start_dt_utc = start_dt_server.astimezone(ZoneInfo("UTC")).replace(minute=0, second=0, microsecond=0)
            end_dt_utc_inclusive = end_dt_server.astimezone(ZoneInfo("UTC")).replace(minute=0, second=0, microsecond=0)

            # Build list of UTC folders to scan (inclusive)
            folders_utc = []
            cur = start_dt_utc
            while cur <= end_dt_utc_inclusive:
                folders_utc.append(cur)
                cur += timedelta(hours=1)

            # For list_files_by_datetime (end-exclusive)
            end_for_query = end_dt_utc_inclusive + timedelta(hours=1)

            with st.spinner("Processing..."):
                files, missing_dirs = list_files_by_datetime(client, start_dt_utc, end_for_query, 0)
                total_size = sum(int(client.info(f).get("size", 0)) for f in files) if not dry_run else None
                est_time = estimate_total_download_time(client, files) if dry_run and files else None

            # --- Output results ---
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

            # --- Download files if not dry run ---
            if not dry_run and files:
                parsed = urlparse(client_config["webdav_hostname"])
                host_only = parsed.hostname if parsed.hostname else client_config["webdav_hostname"]
                download_folder = os.path.join(
                    ".", "downloads",
                    f"{host_only}_{start_dt_utc.strftime('%Y%m%d_%H')}_{end_dt_utc_inclusive.strftime('%Y%m%d_%H')}"
                )
                os.makedirs(download_folder, exist_ok=True)
                with st.spinner("Downloading files..."):
                    processed_files, _ = download_files(client, files, download_folder, dry_run=False)
                st.success(f"Files downloaded to: `{download_folder}`")

        # --- Clear downloads ---
        if clear_downloads_btn:
            download_root = os.path.join(".", "downloads")
            if os.path.exists(download_root):
                shutil.rmtree(download_root)
                st.success("All downloads cleared.")

        st.markdown('</div>', unsafe_allow_html=True)
