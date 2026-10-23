from pathlib import Path

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.users import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.services.permissions import can_read_document
from app.services.storage import save_private_file, get_private_file_path
from app.services.audit import record_audit
from datetime import datetime
from sqlalchemy import or_
from app.models.permission import DocumentPermission

documents_bp = Blueprint(
    "documents",
    __name__,
    url_prefix="/api/documents"
)


def get_current_user():
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


# --------------------------------------------------
# LIST DOCUMENTS
# --------------------------------------------------

@documents_bp.route("/", methods=["GET"])
@jwt_required()
def list_documents():

    user = get_current_user()

    if not user or not user.is_active:
        return jsonify({"error": "Unauthorized"}), 401

    documents = Document.query.filter_by(owner_id=user.id).all()

    return jsonify([
        {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "category": doc.category,
            "owner_id": doc.owner_id,
            "uploaded_at": doc.uploaded_at.isoformat()
        }
        for doc in documents
    ]), 200


# --------------------------------------------------
# GET DOCUMENT METADATA
# --------------------------------------------------

@documents_bp.route("/<int:document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id):

    user = get_current_user()
    document = db.session.get(Document, document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if not can_read_document(user, document):
        record_audit(
            action="DOCUMENT_READ",
            resource_type="document",
            resource_id=document_id,
            outcome="denied",
            actor_id=user.id if user else None
        )
        return jsonify({"error": "Access denied"}), 403

    record_audit(
        action="DOCUMENT_READ",
        resource_type="document",
        resource_id=document_id,
        actor_id=user.id
    )

    return jsonify({
        "id": document.id,
        "title": document.title,
        "filename": document.filename,
        "category": document.category,
        "owner_id": document.owner_id
    }), 200


# --------------------------------------------------
# UPLOAD DOCUMENT
# --------------------------------------------------

@documents_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():

    user = get_current_user()

    if not user or not user.is_active:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    uploaded_file = request.files["file"]

    title = request.form.get("title", "").strip()
    category = request.form.get("category", "General").strip()

    if not uploaded_file.filename or not title:
        return jsonify({"error": "Filename and title are required"}), 400

    storage_key = None

    try:
        storage_key, safe_name = save_private_file(uploaded_file)

        document = Document(
            title=title,
            filename=safe_name,
            storage_key=storage_key,
            category=category,
            owner_id=user.id
        )

        db.session.add(document)
        db.session.flush()

        record_audit(
            action="DOCUMENT_UPLOAD",
            resource_type="document",
            resource_id=document.id,
            actor_id=user.id
        )

        db.session.commit()

        return jsonify({
            "message": "Document uploaded successfully",
            "document_id": document.id,
            "title": document.title,
            "filename": document.filename
        }), 201

    except ValueError as error:
        db.session.rollback()

        if storage_key:
            path = get_private_file_path(storage_key)
            if path:
                Path(path).unlink(missing_ok=True)

        return jsonify({"error": str(error)}), 400

    except Exception:
        db.session.rollback()

        if storage_key:
            path = get_private_file_path(storage_key)
            if path:
                Path(path).unlink(missing_ok=True)

        raise


# --------------------------------------------------
# DOWNLOAD DOCUMENT
# --------------------------------------------------

@documents_bp.route("/<int:document_id>/download", methods=["GET"])
@jwt_required()
def download_document(document_id):

    user = get_current_user()
    document = db.session.get(Document, document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    # Authorization MUST happen before file access.

    if not can_read_document(user, document):
        record_audit(
            action="DOCUMENT_DOWNLOAD",
            resource_type="document",
            resource_id=document_id,
            outcome="denied",
            actor_id=user.id if user else None
        )

        return jsonify({"error": "Access denied"}), 403

    file_path = get_private_file_path(document.storage_key)

    if not file_path or not Path(file_path).is_file():
        return jsonify({"error": "File not found"}), 404

    record_audit(
        action="DOCUMENT_DOWNLOAD",
        resource_type="document",
        resource_id=document_id,
        actor_id=user.id
    )

    return send_file(
        file_path,
        as_attachment=True,
        download_name=document.filename,
        mimetype="application/octet-stream"
    )

# --------------------------------------------------
# SEARCH DOCUMENTS
# --------------------------------------------------

@documents_bp.route("/search", methods=["GET"])
@jwt_required()
def search_documents():

    user = get_current_user()

    if not user or not user.is_active:
        return jsonify({"error": "Unauthorized"}), 401

    # Only documents owned by the user or explicitly shared with them.
    query = Document.query.outerjoin(
        DocumentPermission,
        (DocumentPermission.document_id == Document.id) &
        (DocumentPermission.user_id == user.id)
    ).filter(
        or_(
            Document.owner_id == user.id,
            DocumentPermission.id.isnot(None)
        )
    )

    # Search by title.
    title = request.args.get("title", "").strip()

    if title:
        query = query.filter(Document.title.ilike(f"%{title}%"))

    # Search by owner email.
    owner_email = request.args.get("owner", "").strip().lower()

    if owner_email:
        query = query.join(
            User,
            Document.owner_id == User.id
        ).filter(User.email.ilike(f"%{owner_email}%"))

    # Filter by category.
    category = request.args.get("category", "").strip()

    if category:
        query = query.filter(Document.category.ilike(category))

    # Filter by upload date.
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    try:
        if date_from:
            start_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Document.uploaded_at >= start_date)

        if date_to:
            end_date = datetime.strptime(date_to, "%Y-%m-%d")
            end_date = end_date.replace(
                hour=23,
                minute=59,
                second=59
            )
            query = query.filter(Document.uploaded_at <= end_date)

    except ValueError:
        return jsonify({
            "error": "Dates must use YYYY-MM-DD format"
        }), 400

    documents = query.order_by(
        Document.uploaded_at.desc()
    ).distinct().all()

    return jsonify({
        "count": len(documents),
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "category": doc.category,
                "owner_id": int(doc.owner_id),
                "uploaded_at": doc.uploaded_at.isoformat()
            }
            for doc in documents
        ]
    }), 200
# --------------------------------------------------
# DELETE DOCUMENT
# --------------------------------------------------

@documents_bp.route("/<int:document_id>", methods=["DELETE"])
@jwt_required()
def delete_document(document_id):

    user = get_current_user()
    document = db.session.get(Document, document_id)

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if document.owner_id != user.id:

        record_audit(
            action="DOCUMENT_DELETE",
            resource_type="document",
            resource_id=document_id,
            outcome="denied",
            actor_id=user.id if user else None
        )

        return jsonify({"error": "Access denied"}), 403

    file_path = get_private_file_path(document.storage_key)

    try:
        record_audit(
            action="DOCUMENT_DELETE",
            resource_type="document",
            resource_id=document_id,
            actor_id=user.id
        )

        db.session.delete(document)
        db.session.commit()

        if file_path:
            Path(file_path).unlink(missing_ok=True)

        return jsonify({
            "message": "Document deleted successfully"
        }), 200

    except Exception:
        db.session.rollback()
        raise