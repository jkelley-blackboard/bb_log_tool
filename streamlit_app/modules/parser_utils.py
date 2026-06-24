# ─────────────────────────────────────────────────────────────
# Section 1: Imports
# ─────────────────────────────────────────────────────────────
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

# ─────────────────────────────────────────────────────────────
# Section 2: Manifest Utilities
# ─────────────────────────────────────────────────────────────
def load_manifest(manifest_path):
    """Load converted_files.json and return list of file paths."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

def summarize_files(file_paths):
    """Return summary statistics from file paths."""
    total_files = len(file_paths)
    extensions = Counter(Path(f).suffix for f in file_paths)
    hosts = Counter(Path(f).parts[-2] for f in file_paths if len(Path(f).parts) > 1)
    return {
        "total_files": total_files,
        "extensions": dict(extensions),
        "hosts": dict(hosts)
    }

def count_log_types(file_paths):
    """Detect and count log types from file paths."""
    types = [detect_log_type(f) or "unknown" for f in file_paths]
    return dict(Counter(types))

# ─────────────────────────────────────────────────────────────
# Section 3: Log Type Definitions
# ─────────────────────────────────────────────────────────────
LOG_FIELDS: Dict[str, List[str]] = {
    "authentication": ["timestamp", "evt_name", "authnprovider", "dhost", "src_ip", "duid", "duser"],
    "email": [],
    "schema": [],
    "security": ["timestamp", "user", "action", "status", "ip_address"],
    "services": ["timestamp", "service_name", "status", "message"],
    "sqlerror": [],
    "bbcms": ["timestamp", "event", "user", "course_id", "item_id"],
    "plugins": [],
    "saml": [],
    "partner_cloud": ["timestamp", "action", "entity", "status"],
    "partner_cloud_tasks": [],
    "consulting_central": [],
    "achievements": [],
    "data_integration": ["timestamp", "job_name", "status", "details"],
    "bb_ultra_ui": ["timestamp", "user", "action", "component"],
    "collab_ultra": ["timestamp", "event", "user", "course_id", "item_id"],
    "foundations_cx": [],
    "software_updates": ["timestamp", "component", "version", "status"],
    "application_log": ["timestamp", "component", "event", "message"],
    "safeassign": ["timestamp", "assignment_id", "user_id", "score", "status"],
    "plugins_bb_learn_analytics": [],
    "plugins_mobile": [],
    "plugins_scormengine": [],
    "bb_access": ["client_ip", "host_ip", "connector", "timestamp", "method", "path", "protocol", "status", "size", "referer", "user_agent", "sev", "resp_size"],
    "remote_admin_access": [],
    "catalina_log": ["timestamp", "level", "message"],
    "gc_log": ["timestamp", "gc_type", "duration", "memory_before", "memory_after"],
    "stdout_stderr": ["timestamp", "level", "message"],
    "activemq_broker": [],
    "content_exchange": [],
    "update_tools": [],
    "ws_common": []
}

# ─────────────────────────────────────────────────────────────
# Section 4: Filename Detection
# ─────────────────────────────────────────────────────────────
LOG_FILE_TYPES: Dict[str, str] = {
    r".*bb-authentication-log": "authentication",
    r".*bb-email-log": "email",
    r".*bb-schema-log": "schema",
    r".*bb-security-log": "security",
    r".*bb-services-log": "services",
    r".*bb-sqlerror-log": "sqlerror",
    r".*bbcms_log": "bbcms",
    r".*bb-plugins-log": "plugins",
    r".*bb-saml-log": "saml",
    r".*x-bbgs-partner-cloud": "partner_cloud",
    r".*x-bbgs-partner-cloud.tasks": "partner_cloud",
    r".*x-bbgs-consulting-central": "consulting_central",
    r".*x-bbgs-consulting-central-grade-export": "consulting_central",
    r".*bb-achievements": "achievements",
    r".*data-integration": "data_integration",
    r".*bb-ultra-ui": "bb_ultra_ui",
    r".*collab-ultra": "collab_ultra",
    r".*bb-foundations-cx": "foundations_cx",
    r".*software-updates": "software_updates",
    r".*application": "application_log",
    r".*safeassign-log": "safeassign",
    r".*learn-analytics": "plugins_bb_learn_analytics",
    r".*Bb-mobile-log": "plugins_mobile",
    r".*scormengine": "plugins_scormengine",
    r".*bb-access-log": "bb_access",
    r".*bb-remote-admin-access-log": "remote_admin_access",
    r".*catalina-log": "catalina_log",
    r".*gc": "gc_log",
    r".*stdout-stderr": "stdout_stderr",
    r".*activemq-broker": "activemq_broker",
    r".*activemq": "activemq_broker",
    r".*invoke": "content_exchange",
    r".*bb-xythos-log": "update_tools",
    r".*pushupdate-tool-log": "update_tools",
    r".*update-tool-log": "update_tools",
    r".*WS_common": "ws_common"
}

def get_log_type_from_filename(filename: str) -> Optional[str]:
    for pattern, log_type in LOG_FILE_TYPES.items():
        if re.search(pattern, filename, re.IGNORECASE):
            return log_type
    return None

def detect_log_type(filepath: str) -> Optional[str]:
    return get_log_type_from_filename(Path(filepath).name)

def get_log_fields(log_type: str) -> List[str]:
    return LOG_FIELDS.get(log_type, [])

# ─────────────────────────────────────────────────────────────
# Section 5: Log Entry Parsers
# ─────────────────────────────────────────────────────────────
def parse_authentication(entry: dict) -> Optional[dict]:
    message = entry.get("message", "")
    parsed: Dict[str, str] = {}
    for pair in message.split("\n"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            parsed[key.strip()] = val.strip()
    if "timestamp" in parsed:
        try:
            parsed["timestamp"] = datetime.strptime(parsed["timestamp"], "%b %d %Y %H:%M:%S.%f %Z")
        except Exception:
            pass
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS["authentication"]}

def parse_bb_access(entry: dict) -> Optional[dict]:
    message = entry.get("message", "")
    pattern = (
        r'(?P<client_ip>\S+)\s+'
        r'(?P<host_ip>\S+)\s+'
        r'(?P<connector>\S+)\s+-\s+'
        r'(?:\S+\s+)?'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\S+)\s+(?P<path>.*?)\s+(?P<protocol>\S+)"\s+'
        r'(?P<status>\d+)\s+'
        r'(?P<size>\S+)\s+'
        r'"(?P<referer>[^"]*)"\s+'
        r'"(?P<user_agent>[^"]*)"\s*'
        r'(?P<sev>\S+)\s+'
        r'(?P<resp_size>\S+)'
    )
    m = re.match(pattern, message)
    if not m:
        return None
    parsed = m.groupdict()
    if "timestamp" in parsed:
        try:
            parsed["timestamp"] = datetime.strptime(parsed["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
        except Exception:
            pass
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS["bb_access"]}

def parse_generic(entry: dict, log_type: str) -> Optional[dict]:
    message = entry.get("message", "")
    parsed: Dict[str, str] = {}
    for pair in message.split("\n"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            parsed[key.strip()] = val.strip()
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS.get(log_type, [])}

# ─────────────────────────────────────────────────────────────
# Section 6: Dispatch Table
# ─────────────────────────────────────────────────────────────
LOG_PARSERS: Dict[str, callable] = {
    "authentication": parse_authentication,
    "bb_access": parse_bb_access,
    **{k: lambda e, t=k: parse_generic(e, t) for k in LOG_FIELDS if k not in ["authentication", "bb_access"]}
}

def parse_log_entry(entry: dict, log_type: str, file_path: Optional[str] = None) -> Optional[dict]:
    parser = LOG_PARSERS.get(log_type)
    if not parser:
        return {
            "_file_path": file_path,
            "_file_name": Path(file_path).name if file_path else None,
            "raw_message": entry.get("message"),
            "host": entry.get("host"),
            "path": entry.get("path"),
        }
    parsed = parser(entry)
    if parsed is None:
        return None
    parsed.update({
        "_file_path": file_path,
        "_file_name": Path(file_path).name if file_path else None,
        "raw_message": entry.get("message"),
        "host": entry.get("host"),
        "path": entry.get("path"),
    })
    return parsed