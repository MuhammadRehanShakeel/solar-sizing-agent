"""audit.py - Writes one line to AuditLog for every important staff action (never stops the request)."""
import logging

from app.database import execute_query

log = logging.getLogger("audit")


def audit(user_id, action, target=None, details=None, ip=None):
    try:
        execute_query("INSERT INTO AuditLog (user_id, action, target, details, ip_address) VALUES (?, ?, ?, ?, ?)",
                      (user_id, action, target, (details or "")[:400] or None, ip), commit=True)
    except Exception:
        log.exception("Could not write the audit log")
