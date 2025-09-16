# ./modules/parser_utils.py
import re
from datetime import datetime
from pathlib import Path

# --------------------------
# 1. LOG FIELDS
# --------------------------
LOG_FIELDS = {
    "authentication": ["timestamp", "evt_name", "authnprovider", "dhost", "src_ip", "duid", "duser"],
    "bb_access": ["timestamp", "client_ip", "host_ip", "connector", "method", "path", "protocol",
                  "status", "size", "user_agent", "sev", "resp_size"],
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
    "data_integration": ["timestamp", "job_name", "status", "details"]
}

# --------------------------
# 2. NOISE PATTERNS
# --------------------------
NOISE_PATTERNS = {
    "authentication": [r'testuser', r'debug'],
    "bb_access": [r'healthcheck', r'favicon\.ico'],
    "bbcms": [r'/internal/monitoring/'],
    "security": [r'testuser'],
    "services": [r'debug', r'test_service'],
    "partner_cloud": [r'dummy'],
    "safeassign": [],
    "stdout_stderr": [],
    "collab_ultra": [],
    "software_updates": [],
    "application_log": [],
    "gc_log": [],
    "catalina_log": [],
    "bb_ultra_ui": [],
    "data_integration": []
}

# --------------------------
# 3. FILE NAME TO LOG TYPE
# --------------------------
LOG_FILE_TYPES = {
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
    r'.*data_integration.*\.log$': 'data_integration'
}

# --------------------------
# 4. PARSER FUNCTIONS
# --------------------------
def parse_authentication(entry):
    message = entry.get("message", "")
    parsed = {}
    for pair in message.split("|"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            parsed[key.strip()] = val.strip()
    if "timestamp" in parsed:
        try:
            parsed["timestamp"] = datetime.strptime(parsed["timestamp"], "%b %d %Y %H:%M:%S.%f %Z")
        except Exception:
            pass
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS["authentication"]}

def parse_bb_access(entry):
    message = entry.get("message", "")
    pattern = r'(?P<client_ip>\S+) (?P<host_ip>\S+) (?P<connector>\S+) - \[(?P<timestamp>.*?)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>.*?)" (?P<status>\d+) (?P<size>\S+) "(?P<referer>.*?)" "(?P<user_agent>.*?)" (?P<sev>\d+) (?P<resp_size>\S+)'
    match = re.match(pattern, message)
    if not match:
        return None
    parsed = match.groupdict()
    if "timestamp" in parsed:
        try:
            parsed["timestamp"] = datetime.strptime(parsed["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
        except Exception:
            pass
    # Check for noise
    for pat in NOISE_PATTERNS.get("bb_access", []):
        if parsed.get("path") and re.search(pat, parsed["path"]):
            return None
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS["bb_access"]}

# Generic parser
def parse_generic(entry, log_type):
    message = entry.get("message", "")
    parsed = {}
    for pair in message.split("|"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            parsed[key.strip()] = val.strip()
    return {k: v for k, v in parsed.items() if k in LOG_FIELDS.get(log_type, [])}

# --------------------------
# 5. PARSER DISPATCH
# --------------------------
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
    "data_integration": lambda e: parse_generic(e, "data_integration")
}

# --------------------------
# 6. HELPER FUNCTIONS
# --------------------------
def get_log_type_from_filename(filename):
    """Return the log type based on filename using regex rules."""
    for pattern, log_type in LOG_FILE_TYPES.items():
        if re.match(pattern, filename, re.IGNORECASE):
            return log_type
    return None

def detect_log_type(filepath):
    """Wrapper for backwards compatibility with search.py"""
    return get_log_type_from_filename(Path(filepath).name)

def get_log_fields(log_type):
    """Return all field names for a given log type."""
    return LOG_FIELDS.get(log_type, [])

def parse_log_entry(entry, log_type, file_path=None):
    """
    Parse a single log entry with optional file path context.
    Automatically adds _file_path and _file_name to parsed results.
    Returns None if the record is noisy/ignored.
    """
    parser = LOG_PARSERS.get(log_type)
    if not parser:
        return {
            "_file_path": file_path,
            "_file_name": Path(file_path).name if file_path else None,
            "raw_message": entry.get("message"),
            "host": entry.get("host"),
            "path": entry.get("path")
        }

    parsed = parser(entry)
    if parsed is None:
        return None  # noisy or ignored record

    # Attach metadata
    parsed.update({
        "_file_path": file_path,
        "_file_name": Path(file_path).name if file_path else None,
        "raw_message": entry.get("message"),
        "host": entry.get("host"),
        "path": entry.get("path")
    })
    return parsed
