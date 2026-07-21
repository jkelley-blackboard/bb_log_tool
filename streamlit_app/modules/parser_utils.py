# ─────────────────────────────────────────────────────────────
# Section 1: Imports
# ─────────────────────────────────────────────────────────────
import re
import json
from pathlib import Path
from typing import Dict, Optional

# ─────────────────────────────────────────────────────────────
# Section 2: Manifest Utilities
# ─────────────────────────────────────────────────────────────
def load_manifest(manifest_path):
    """Load converted_files.json and return list of file paths."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ─────────────────────────────────────────────────────────────
# Section 3: Filename Detection
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