import hashlib
import json

from datetime import datetime, timezone

from flask import request

from app.extensions import db
from app.models.audit_log import AuditLog


def calculate_hash(payload):
    canonical_data = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        canonical_data.encode("utf-8")
    ).hexdigest()


def record_audit(
    action,
    resource_type,
    resource_id=None,
    outcome="success",
    actor_id=None,
    details=None
):
    previous = (
        AuditLog.query
        .order_by(AuditLog.id.desc())
        .first()
    )

    previous_hash = previous.entry_hash if previous else "GENESIS"

    created_at = datetime.now(timezone.utc)
    ip_address = request.remote_addr if request else None

    payload = {
        "actor_id": actor_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "outcome": outcome,
        "ip_address": ip_address,
        "details": details,
        "created_at": created_at.isoformat(),
        "previous_hash": previous_hash
    }

    entry_hash = calculate_hash(payload)

    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=payload["resource_id"],
        outcome=outcome,
        ip_address=ip_address,
        details=details,
        created_at=created_at,
        previous_hash=previous_hash,
        entry_hash=entry_hash
    )

    db.session.add(entry)
    db.session.commit()

    return True


def verify_audit_chain():
    entries = AuditLog.query.order_by(AuditLog.id.asc()).all()

    expected_previous_hash = "GENESIS"

    for entry in entries:
        if entry.previous_hash != expected_previous_hash:
            return False

        payload = {
            "actor_id": entry.actor_id,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "outcome": entry.outcome,
            "ip_address": entry.ip_address,
            "details": entry.details,
            "created_at": normalize_timestamp(entry.created_at),
            "previous_hash": entry.previous_hash
        }

        calculated_hash = calculate_hash(payload)

        if calculated_hash != entry.entry_hash:
            return False

        expected_previous_hash = entry.entry_hash

    return True

def normalize_timestamp(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()