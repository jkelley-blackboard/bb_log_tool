import os
import time
import tempfile
from datetime import timedelta
from webdav3.client import Client

def build_remote_path(dt, offset_hours=4):
    """
    Build the WebDAV folder path for a given datetime, applying hour offset.
    Example: bbcswebdav/internal/logs/2025/09/15/04
    """
    dt_adj = dt + timedelta(hours=offset_hours)
    return f"bbcswebdav/internal/logs/{dt_adj.year}/{dt_adj.month:02d}/{dt_adj.day:02d}/{dt_adj.hour:02d}"

def list_files_by_datetime(client: Client, start_dt, end_dt, offset_hours=4):
    """
    List all files in WebDAV server between start_dt (inclusive) and end_dt (exclusive).
    Returns a tuple: (list_of_files, list_of_missing_dirs)
    """
    files = []
    missing_dirs = []
    current = start_dt

    while current < end_dt:
        dir_path = build_remote_path(current, offset_hours)
        try:
            dir_files = client.list(dir_path)
            for f in dir_files:
                files.append(f"{dir_path}/{f.lstrip('/')}")
        except Exception as e:
            missing_dirs.append(dir_path)
        current += timedelta(hours=1)

    return files, missing_dirs

def download_files(client: Client, files, download_dir, dry_run=True):
    """
    Download files from WebDAV server to a local folder.
    Returns (processed_files_list, total_size_bytes)
    """
    os.makedirs(download_dir, exist_ok=True)
    processed_files = []
    total_size = 0

    for f in files:
        try:
            info = client.info(f)
            size = int(info.get('size', 0))
            total_size += size
            processed_files.append(f)

            if not dry_run:
                local_path = os.path.join(download_dir, os.path.basename(f))
                client.download_sync(remote_path=f, local_path=local_path)
        except Exception as e:
            print(f"[DEBUG] Failed to process {f}: {e}")
            continue

    return processed_files, total_size

def estimate_network_speed(client: Client, file_path):
    """
    Measure download speed by downloading one file to a temporary path.
    Returns (bytes_per_second, file_size_bytes) or (None, None) on failure.
    """
    try:
        size_bytes = int(client.info(file_path).get('size', 0))
        if size_bytes == 0:
            return None, None

        tmp_fd, tmp_path = tempfile.mkstemp()
        os.close(tmp_fd)  # Windows-friendly

        try:
            start_time = time.time()
            client.download_sync(remote_path=file_path, local_path=tmp_path)
            elapsed = time.time() - start_time
        finally:
            os.remove(tmp_path)

        speed = size_bytes / elapsed if elapsed > 0 else 0
        return (speed, size_bytes) if speed > 0 else (None, None)

    except Exception as e:
        print(f"[DEBUG] Failed speed estimation for {file_path}: {e}")
        return None, None

def estimate_total_download_time(client: Client, files):
    """
    Estimate total download time for all files using network speed of the first file.
    Returns a dict: {total_size_bytes, total_size_mb, estimated_seconds}
    """
    if not files:
        return None

    speed, _ = estimate_network_speed(client, files[0])
    if not speed or speed == 0:
        return None

    try:
        total_size = sum(int(client.info(f).get('size', 0)) for f in files)
        total_size_mb = total_size / (1024 * 1024)
        estimated_seconds = total_size / speed

        return {
            "total_size_bytes": total_size,
            "total_size_mb": total_size_mb,
            "estimated_seconds": estimated_seconds
        }
    except Exception as e:
        print(f"[DEBUG] Failed to estimate total download time: {e}")
        return None
