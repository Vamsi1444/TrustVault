from app.models.users import User
from app.models.document import Document
from app.models.permission import DocumentPermission


def get_document_access(user, document):
    """
    Returns the user's access level for a document.
    """

    if not user or not user.is_active:
        return None

    # Document owner has full access.
    if document.owner_id == user.id:
        return "owner"

    # Check explicitly granted permissions.
    permission = DocumentPermission.query.filter_by(
        document_id=document.id,
        user_id=user.id
    ).first()

    if permission:
        return permission.permission

    return None


def can_read_document(user, document):
    return get_document_access(user, document) in (
        "owner", "read", "edit"
    )


def can_edit_document(user, document):
    return get_document_access(user, document) in (
        "owner", "edit"
    )