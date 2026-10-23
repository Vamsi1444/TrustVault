from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.users import User
from app.models.audit_log import AuditLog


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/activity", methods=["GET"])
@jwt_required()
def get_activity():

    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    # Authentication and authorization
    if not user or not user.is_active:
        return jsonify({"error": "Unauthorized"}), 401

    if user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    if page < 1 or per_page < 1 or per_page > 100:
        return jsonify({"error": "Invalid pagination"}), 400

    # Base query
    query = AuditLog.query

    # Filter by action
    action = request.args.get("action", "").strip()

    if action:
        query = query.filter(AuditLog.action.ilike(action))

    # Filter by outcome
    outcome = request.args.get("outcome", "").strip().lower()

    if outcome:
        if outcome not in ("success", "denied", "failure"):
            return jsonify({"error": "Invalid outcome"}), 400

        query = query.filter(AuditLog.outcome == outcome)

    # Filter by actor ID
    actor_id = request.args.get("actor_id", "").strip()

    if actor_id:
        try:
            actor_id = int(actor_id)
            if actor_id < 1:
                raise ValueError
        except ValueError:
            return jsonify({"error": "Invalid actor ID"}), 400

        query = query.filter(AuditLog.actor_id == actor_id)

    # Filter by date range
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    try:
        if date_from:
            start_date = datetime.strptime(
                date_from, "%Y-%m-%d"
            )
            query = query.filter(
                AuditLog.created_at >= start_date
            )

        if date_to:
            end_date = datetime.strptime(
                date_to, "%Y-%m-%d"
            ) + timedelta(days=1)

            query = query.filter(
                AuditLog.created_at < end_date
            )

    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Retrieve records
    pagination = (
        query
        .order_by(AuditLog.id.desc())
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    )

    activities = []

    for log in pagination.items:
        activities.append({
            "id": log.id,
            "actor_id": log.actor_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "outcome": log.outcome,
            "ip_address": log.ip_address,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
            "entry_hash": log.entry_hash
        })

    return jsonify({
        "activities": activities,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages
    }), 200