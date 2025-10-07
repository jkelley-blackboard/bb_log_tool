from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# -----------------------------
# 1) Field catalog per log type
# -----------------------------
LOG_FIELDS: Dict[str, List[str]] = {
    # ─── Root-Level Logs ─────────────────────────────
    "authentication": ["timestamp", "evt_name", "authnprovider", "dhost", "src_ip", "duid", "duser"],
    "email": [],
    "schema": [],
    "security": ["timestamp", "user", "action", "status", "ip_address"],
    "services": ["timestamp", "service_name", "status", "message"],
    "sqlerror": [],
    "bbcms": ["timestamp", "event", "user", "course_id", "item_id"],
    "plugins": [],
    "saml": [],

    # ─── Partner Cloud ───────────────────────────────
    "partner_cloud": ["timestamp", "action", "entity", "status"],
    "partner_cloud_tasks": [],

    # ─── Consulting Central ──────────────────────────
    "consulting_central": [],

    # ─── Custom ──────────────────────────────────────
    "achievements": [],

    # ─── Data Integration ────────────────────────────
    "data_integration": ["timestamp", "job_name", "status", "details"],

    # ─── Plugins ─────────────────────────────────────
    "bb_ultra_ui": ["timestamp", "user", "action", "component"],
    "collab_ultra": ["timestamp", "event", "user", "course_id", "item_id"],
    "foundations_cx": [],
    "software_updates": ["timestamp", "component", "version", "status"],
    "application_log": ["timestamp", "component", "event", "message"],
    "safeassign": ["timestamp", "assignment_id", "user_id", "score", "status"],
    "plugins_bb_learn_analytics": [],
    "plugins_mobile": [],
    "plugins_scormengine": [],

    # ─── Tomcat ──────────────────────────────────────
    "bb_access": ["client_ip", "host_ip", "connector", "timestamp", "method", "path", "protocol", "status", "size", "referer", "user_agent", "sev", "resp_size"],
    "remote_admin_access": [],
    "catalina_log": ["timestamp", "level", "message"],
    "gc_log": ["timestamp", "gc_type", "duration", "memory_before", "memory_after"],
    "stdout_stderr": ["timestamp", "level", "message"],

    # ─── ActiveMQ Broker ─────────────────────────────
    "activemq_broker": [],

    # ─── Content Exchange ────────────────────────────
    "content_exchange": [],

    # ─── Update Tools ────────────────────────────────
    "update_tools": [],

    # ─── WS ──────────────────────────────────────────
    "ws_common": []
}


# -----------------------------
# 2) Filename → type mapping
# -----------------------------
LOG_FILE_TYPES: Dict[str, str] = {
    # ─── Root-Level Logs ─────────────────────────────
    r".*bb-authentication-log": "authentication",
    r".*bb-email-log": "email",
    r".*bb-schema-log": "schema",
    r".*bb-security-log": "security",
    r".*bb-services-log": "services",
    r".*bb-sqlerror-log": "sqlerror",
    r".*bbcms_log": "bbcms",
    r".*bb-plugins-log": "plugins",
    r".*bb-saml-log": "saml",

    # ─── Partner Cloud ───────────────────────────────
    r".*x-bbgs-partner-cloud": "partner_cloud",
    r".*x-bbgs-partner-cloud.tasks": "partner_cloud",

    # ─── Consulting Central ──────────────────────────
    r".*x-bbgs-consulting-central": "consulting_central",
    r".*x-bbgs-consulting-central-grade-export": "consulting_central",

    # ─── Custom ──────────────────────────────────────
    r".*bb-achievements": "achievements",

    # ─── Data Integration ────────────────────────────
    r".*data-integration": "data_integration",

    # ─── Plugins ─────────────────────────────────────
    r".*bb-ultra-ui": "bb_ultra_ui",
    r".*collab-ultra": "collab_ultra",
    r".*bb-foundations-cx": "foundations_cx",
    r".*software-updates": "software_updates",
    r".*application": "application_log",
    r".*safeassign-log": "safeassign",
    r".*learn-analytics": "plugins_bb_learn_analytics",
    r".*Bb-mobile-log": "plugins_mobile",
    r".*scormengine": "plugins_scormengine",

    # ─── Tomcat ──────────────────────────────────────
    r".*bb-access-log": "bb_access",
    r".*bb-remote-admin-access-log": "remote_admin_access",
    r".*catalina-log": "catalina_log",
    r".*gc": "gc_log",
    r".*stdout-stderr": "stdout_stderr",

    # ─── ActiveMQ Broker ─────────────────────────────
    r".*activemq-broker": "activemq_broker",
    r".*activemq": "activemq_broker",

    # ─── Content Exchange ────────────────────────────
    r".*invoke": "content_exchange",

    # ─── Update Tools ────────────────────────────────
    r".*bb-xythos-log": "update_tools",
    r".*pushupdate-tool-log": "update_tools",
    r".*update-tool-log": "update_tools",

    # ─── WS ──────────────────────────────────────────
    r".*WS_common": "ws_common"
}


# -----------------------------
# 3) Parsers
# -----------------------------
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

import re
from datetime import datetime
from typing import Optional

def parse_bb_access(entry: dict) -> Optional[dict]:
    message = entry.get("message", "")
    
    # Improved pattern: quote-aware, optional fields
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

    # Convert timestamp to datetime
    if "timestamp" in parsed:
        try:
            parsed["timestamp"] = datetime.strptime(parsed["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
        except Exception:
            pass

    # Ensure only expected fields are returned
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS["bb_access"]}

def parse_generic(entry: dict, log_type: str) -> Optional[dict]:
    message = entry.get("message", "")
    parsed: Dict[str, str] = {}
    for pair in message.split("\n"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            parsed[key.strip()] = val.strip()
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS.get(log_type, [])}

# -----------------------------
# 4) Dispatch & helpers
# -----------------------------
LOG_PARSERS: Dict[str, callable] = {
    "authentication": parse_authentication,
    "bb_access": parse_bb_access,
    **{k: lambda e, t=k: parse_generic(e, t) for k in LOG_FIELDS if k not in ["authentication", "bb_access"]}
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