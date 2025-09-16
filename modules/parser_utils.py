# modules/parser_utils.py
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# -----------------------------
# 1) Field catalog per log type
# -----------------------------
LOG_FIELDS: Dict[str, List[str]] = {
    "authentication": ["timestamp", "evt_name", "authnprovider", "dhost", "src_ip", "duid", "duser"],
    "bb_access": [
        "timestamp", "client_ip", "host_ip", "connector", "method", "path", "protocol",
        "status", "size", "user_agent", "sev", "resp_size"
    ],
    "bbcms": ["timestamp", "event", "user", "course_id", "item_id"],
    "security": ["timestamp", "user", "action", "status", "ip_address"],
    "services": ["timestamp", "service_name", "status", "message"],
    "partner_cloud": ["timestamp", "action", "entity", "status"],
    "safeassign": ["timestamp", "assignment_id", "user_id", "score", "status"],
    "stdout_stderr": ["timestamp", "level", "message"],
    "collab_ultra": ["timestamp", "event", "user", "course_id", "item_id"],
    "software_updates": ["timestamp", "component", "version", "status"],
    "application_log": ["timestamp", "component", "event", "message"],
    "gc_log": ["timestamp", "gc_type", "duration", "memory_before", "memory_after"],
    "catalina_log": ["timestamp", "level", "message"],
    "bb_ultra_ui": ["timestamp", "user", "action", "component"],
    "data_integration": ["timestamp", "job_name", "status", "details"],
}

# -----------------------------
# 2) Filename → type mapping
# -----------------------------
LOG_FILE_TYPES: Dict[str, str] = {
    # Raw .log patterns (kept for completeness)
    r'.*authentication.*\.log$': 'authentication',
    r'.*bb-access.*\.log$': 'bb_access',
    r'.*bbcms.*\.log$': 'bbcms',
    r'.*security.*\.log$': 'security',
    r'.*services.*\.log$': 'services',
    r'.*partner_cloud.*\.log$': 'partner_cloud',
    r'.*safeassign.*\.log$': 'safeassign',
    r'.*stdout_stderr.*\.log$': 'stdout_stderr',
    r'.*collab_ultra.*\.log$': 'collab_ultra',
    r'.*software_updates.*\.log$': 'software_updates',
    r'.*application.*\.log$': 'application_log',
    r'.*gc.*\.log$': 'gc_log',
    r'.*catalina.*\.log$': 'catalina_log',
    r'.*bb_ultra_ui.*\.log$': 'bb_ultra_ui',
    r'.*data_integration.*\.log$': 'data_integration',
}

# Converted JSON filename patterns (match your sample names)
LOG_FILE_TYPES.update({
    r'.*bb_access_log.*_txt\.json$': 'bb_access',
    r'.*bb_authentication_log.*_txt\.json$': 'authentication',
    r'.*bb_security_log.*_txt\.json$': 'security',
    r'.*bb_services_log.*_txt\.json$': 'services',

    # Partner Cloud (and tasks variant)
    r'.*x_bbgs_partner_cloud(_tasks)?_.*_log\.json$': 'partner_cloud',

    # UI / Plugins
    r'.*bb_ultra_ui_log\.json$': 'bb_ultra_ui',
    r'.*collab_ultra_log\.json$': 'collab_ultra',
    r'.*software_updates_log\.json$': 'software_updates',

    # Telemetry/application variants with/without date
    r'.*application(_\d{4}_\d{2}_\d{2})?_log\.json$': 'application_log',

    # SafeAssign variants
    r'.*safeassign_log(_txt)?(_\d{4}_\d{2}_\d{2})?_log\.json$': 'safeassign',

    # Tomcat/GC/Catalina/stdout
    r'.*gc_log\.json$': 'gc_log',
    r'.*catalina_log(_txt)?\.json$': 'catalina_log',
    r'.*stdout_stderr(_\d+)?_log\.json$': 'stdout_stderr',

    # BBCMS / Data-integration / Other
    r'.*bbcms_log_txt\.json$': 'bbcms',
    r'.*data_integration(_\d{4}_\d{2}_\d{2})?_txt\.json$': 'data_integration',

    # Optional: schema logs – map to services for now (adjust if needed)
    r'.*bb_schema_log_txt\.json$': 'services',
})

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
    keep = {k: v for k, v in parsed.items() if k in LOG_FIELDS["authentication"]}
    return keep


def parse_bb_access(entry: dict) -> Optional[dict]:
    message = entry.get("message", "")
    pattern = (
        r'(?P<client_ip>\S+) (?P<host_ip>\S+) (?P<connector>\S+) - '\
        r'\[(?P<timestamp>.+?)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>.+?)" '\
        r'(?P<status>\d+) (?P<size>\S+) "(?P<referer>.*?)" "(?P<user_agent>.*?)" (?P<sev>\d+) (?P<resp_size>\S+)'
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
    keep = {k: v for k, v in parsed.items() if k in LOG_FIELDS["bb_access"]}
    return keep


def parse_generic(entry: dict, log_type: str) -> Optional[dict]:
    message = entry.get("message", "")
    parsed: Dict[str, str] = {}
    for pair in message.split("\n"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            parsed[key.strip()] = val.strip()
    keep = {k: v for k, v in parsed.items() if k in LOG_FIELDS.get(log_type, [])}
    return keep

# -----------------------------
# 4) Dispatch & helpers
# -----------------------------
LOG_PARSERS = {
    "authentication": parse_authentication,
    "bb_access": parse_bb_access,
    "bbcms": lambda e: parse_generic(e, "bbcms"),
    "security": lambda e: parse_generic(e, "security"),
    "services": lambda e: parse_generic(e, "services"),
    "partner_cloud": lambda e: parse_generic(e, "partner_cloud"),
    "safeassign": lambda e: parse_generic(e, "safeassign"),
    "stdout_stderr": lambda e: parse_generic(e, "stdout_stderr"),
    "collab_ultra": lambda e: parse_generic(e, "collab_ultra"),
    "software_updates": lambda e: parse_generic(e, "software_updates"),
    "application_log": lambda e: parse_generic(e, "application_log"),
    "gc_log": lambda e: parse_generic(e, "gc_log"),
    "catalina_log": lambda e: parse_generic(e, "catalina_log"),
    "bb_ultra_ui": lambda e: parse_generic(e, "bb_ultra_ui"),
    "data_integration": lambda e: parse_generic(e, "data_integration"),
}


def get_log_type_from_filename(filename: str) -> Optional[str]:
    for pattern, log_type in LOG_FILE_TYPES.items():
        if re.match(pattern, filename, re.IGNORECASE):
            return log_type
    return None


def detect_log_type(filepath: str) -> Optional[str]:
    return get_log_type_from_filename(Path(filepath).name)


def get_log_fields(log_type: str) -> List[str]:
    return LOG_FIELDS.get(log_type, [])


def parse_log_entry(entry: dict, log_type: str, file_path: Optional[str] = None) -> Optional[dict]:
    parser = LOG_PARSERS.get(log_type)
    if not parser:
        # Unknown type; attach minimal context
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
