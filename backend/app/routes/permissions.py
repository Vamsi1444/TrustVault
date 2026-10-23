from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.users import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.services.audit import record_audit


permissions_bp = Blueprint(
    "permissions",
    __name__,
    url_prefix="/api/permissions"
)


def get_active_owner():
    user_id = int(get_jwt_identity())
    owner = db.session.get(User, user_id)

    if not owner or not owner.is_active:
        return None

    return owner


def audit_denial(action, document_id, owner):
    record_audit(
        action=action,
        resource_type="document",
        resource_id=document_id,
        outcome="denied",
        actor_id=owner.id
    )


# --------------------------------------------------
# GRANT PERMISSION
# --------------------------------------------------
@permissions_bp.route(
    "/<int:document_id>/grant",
    methods=["POST"]
)
@jwt_required()
def grant_permission(document_id):
    owner = get_active_owner()

    if not owner:
        return jsonify({"error": "Unauthorized"}), 401

    document = db.session.get(Document, document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if document.owner_id != owner.id:
        audit_denial("PERMISSION_GRANT", document_id, owner)
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}

    target_email = data.get("email")
    permission_type = data.get("permission")

    if not isinstance(target_email, str) or not target_email.strip():
        return jsonify({"error": "Valid email is required"}), 400

    target_email = target_email.strip().lower()

    if permission_type not in ("read", "edit"):
        return jsonify({
            "error": "Permission must be read or edit"
        }), 400

    target_user = User.query.filter_by(email=target_email).first()

    if not target_user or not target_user.is_active:
        return jsonify({"error": "Target user not found"}), 404

    if target_user.id == owner.id:
        return jsonify({
            "error": "Owner already has full access"
        }), 400

    existing = DocumentPermission.query.filter_by(
        document_id=document.id,
        user_id=target_user.id
    ).first()

    try:
        if existing:
            existing.permission = permission_type
        else:
            db.session.add(
                DocumentPermission(
                    document_id=document.id,
                    user_id=target_user.id,
                    permission=permission_type
                )
            )

        db.session.commit()

        record_audit(
            action="PERMISSION_GRANT",
            resource_type="document",
            resource_id=document.id,
            outcome="success",
            actor_id=owner.id,
            details=(
                f"Granted {permission_type} access "
                f"to user {target_user.id}"
            )
        )

        return jsonify({
            "message": "Permission granted",
            "document_id": document.id,
            "user_id": target_user.id,
            "permission": permission_type
        }), 200

    except Exception:
        db.session.rollback()
        raise


# --------------------------------------------------
# REVOKE PERMISSION
# --------------------------------------------------
@permissions_bp.route(
    "/<int:document_id>/revoke/<int:target_user_id>",
    methods=["DELETE"]
)
@jwt_required()
def revoke_permission(document_id, target_user_id):
    owner = get_active_owner()

    if not owner:
        return jsonify({"error": "Unauthorized"}), 401

    document = db.session.get(Document, document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if document.owner_id != owner.id:
        audit_denial("PERMISSION_REVOKE", document_id, owner)
        return jsonify({"error": "Access denied"}), 403

    permission = DocumentPermission.query.filter_by(
        document_id=document.id,
        user_id=target_user_id
    ).first()

    if not permission:
        return jsonify({"error": "Permission not found"}), 404

    try:
        db.session.delete(permission)
        db.session.commit()

        record_audit(
            action="PERMISSION_REVOKE",
            resource_type="document",
            resource_id=document.id,
            outcome="success",
            actor_id=owner.id,
            details=f"Revoked access from user {target_user_id}"
        )

        return jsonify({
            "message": "Permission revoked"
        }), 200

    except Exception:
        db.session.rollback()
        raise


# --------------------------------------------------
# LIST DOCUMENT PERMISSIONS
# Owner only
# --------------------------------------------------
@permissions_bp.route(
    "/<int:document_id>",
    methods=["GET"]
)
@jwt_required()
def list_permissions(document_id):
    owner = get_active_owner()

    if not owner:
        return jsonify({"error": "Unauthorized"}), 401

    document = db.session.get(Document, document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if document.owner_id != owner.id:
        return jsonify({"error": "Access denied"}), 403

    permissions = DocumentPermission.query.filter_by(
        document_id=document.id
    ).all()

    result = []

    for permission in permissions:
        target_user = db.session.get(User, permission.user_id)

        if target_user:
            result.append({
                "user_id": target_user.id,
                "email": target_user.email,
                "permission": permission.permission
            })

    return jsonify({
        "permissions": result
    }), 200