import pytest

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.users import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.services.audit import record_audit, verify_audit_chain


# --------------------------------------------------
# LOGIN HELPER
# --------------------------------------------------

def login(client, email, password):
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password
        }
    )

    assert response.status_code == 200

    token = response.get_json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


# --------------------------------------------------
# TEST USERS
# --------------------------------------------------

@pytest.fixture
def users(app):
    with app.app_context():
        alice = User(
            name="Alice",
            email="alice@test.com",
            role="viewer"
        )
        alice.set_password("AliceSecure@123")

        bob = User(
            name="Bob",
            email="bob@test.com",
            role="viewer"
        )
        bob.set_password("BobSecure@123")

        db.session.add_all([alice, bob])
        db.session.commit()

        return {
            "alice_id": alice.id,
            "bob_id": bob.id
        }


# --------------------------------------------------
# DOCUMENT HELPER
# --------------------------------------------------

def create_document(owner_id):
    document = Document(
        title="Test Document",
        filename="test.pdf",
        storage_key="test-storage-key",
        category="General",
        owner_id=owner_id
    )

    db.session.add(document)
    db.session.commit()

    return document.id


# --------------------------------------------------
# TEST 1: UNAUTHORIZED METADATA ACCESS
# --------------------------------------------------

def test_unauthorized_user_cannot_access_document_metadata(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response = client.get(
        f"/api/documents/{document_id}",
        headers=bob_headers
    )

    assert response.status_code == 403


# --------------------------------------------------
# TEST 2: UNAUTHORIZED DOWNLOAD
# --------------------------------------------------

def test_unauthorized_user_cannot_download_document(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response = client.get(
        f"/api/documents/{document_id}/download",
        headers=bob_headers
    )

    assert response.status_code == 403


# --------------------------------------------------
# TEST 3: UNAUTHORIZED DELETE
# --------------------------------------------------

def test_unauthorized_user_cannot_delete_document(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response = client.delete(
        f"/api/documents/{document_id}",
        headers=bob_headers
    )

    assert response.status_code == 403

    with app.app_context():
        document = db.session.get(Document, document_id)
        assert document is not None


# --------------------------------------------------
# TEST 4: UNAUTHORIZED GRANT
# --------------------------------------------------

def test_unauthorized_user_cannot_grant_permission(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response = client.post(
        f"/api/permissions/{document_id}/grant",
        headers=bob_headers,
        json={
            "email": "bob@test.com",
            "permission": "read"
        }
    )

    assert response.status_code == 403


# --------------------------------------------------
# TEST 5: UNAUTHORIZED REVOKE
# --------------------------------------------------

def test_unauthorized_user_cannot_revoke_permission(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response = client.delete(
        f"/api/permissions/{document_id}/revoke/{users['alice_id']}",
        headers=bob_headers
    )

    assert response.status_code == 403


# --------------------------------------------------
# TEST 6: REVOKED PERMISSION BLOCKS DOWNLOAD
# --------------------------------------------------

def test_revoked_permission_blocks_download(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

        permission = DocumentPermission(
            document_id=document_id,
            user_id=users["bob_id"],
            permission="read"
        )

        db.session.add(permission)
        db.session.commit()

    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response_before = client.get(
        f"/api/documents/{document_id}",
        headers=bob_headers
    )

    assert response_before.status_code == 200

    alice_headers = login(
        client,
        "alice@test.com",
        "AliceSecure@123"
    )

    revoke_response = client.delete(
        f"/api/permissions/{document_id}/revoke/{users['bob_id']}",
        headers=alice_headers
    )

    assert revoke_response.status_code == 200

    response_after = client.get(
        f"/api/documents/{document_id}/download",
        headers=bob_headers
    )

    assert response_after.status_code == 403


# --------------------------------------------------
# TEST 7: INVALID PERMISSION TYPE
# --------------------------------------------------

def test_invalid_permission_type_is_rejected(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    alice_headers = login(
        client,
        "alice@test.com",
        "AliceSecure@123"
    )

    response = client.post(
        f"/api/permissions/{document_id}/grant",
        headers=alice_headers,
        json={
            "email": "bob@test.com",
            "permission": "admin"
        }
    )

    assert response.status_code == 400


# --------------------------------------------------
# TEST 8: OWNER CAN GRANT READ
# --------------------------------------------------

def test_owner_can_grant_read_permission(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    alice_headers = login(
        client,
        "alice@test.com",
        "AliceSecure@123"
    )

    response = client.post(
        f"/api/permissions/{document_id}/grant",
        headers=alice_headers,
        json={
            "email": "bob@test.com",
            "permission": "read"
        }
    )

    assert response.status_code == 200


# --------------------------------------------------
# TEST 9: GRANTED USER CAN ACCESS METADATA
# --------------------------------------------------

def test_granted_user_can_access_document_metadata(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    alice_headers = login(
        client,
        "alice@test.com",
        "AliceSecure@123"
    )

    grant_response = client.post(
        f"/api/permissions/{document_id}/grant",
        headers=alice_headers,
        json={
            "email": "bob@test.com",
            "permission": "read"
        }
    )

    assert grant_response.status_code == 200

    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response = client.get(
        f"/api/documents/{document_id}",
        headers=bob_headers
    )

    assert response.status_code == 200


# --------------------------------------------------
# TEST 10: UNAUTHENTICATED METADATA ACCESS
# --------------------------------------------------

def test_unauthenticated_user_cannot_access_document(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    response = client.get(
        f"/api/documents/{document_id}"
    )

    assert response.status_code == 401


# --------------------------------------------------
# TEST 11: UNAUTHENTICATED DOWNLOAD
# --------------------------------------------------

def test_unauthenticated_user_cannot_download_document(
    app, client, users
):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    response = client.get(
        f"/api/documents/{document_id}/download"
    )

    assert response.status_code == 401


# --------------------------------------------------
# TEST 12: NONEXISTENT DOCUMENT
# --------------------------------------------------

def test_user_cannot_access_nonexistent_document(
    app, client, users
):
    bob_headers = login(
        client,
        "bob@test.com",
        "BobSecure@123"
    )

    response = client.get(
        "/api/documents/999999",
        headers=bob_headers
    )

    assert response.status_code in (403, 404)


# --------------------------------------------------
# TEST 13: AUDIT LOG UPDATE PROTECTION
# --------------------------------------------------

def test_audit_log_cannot_be_modified(app):
    with app.app_context():
        log = AuditLog(
            action="DOCUMENT_UPLOAD",
            resource_type="document",
            resource_id="123",
            outcome="success",
            previous_hash="GENESIS",
            entry_hash="a" * 64
        )

        db.session.add(log)
        db.session.commit()

        log_id = log.id

        with pytest.raises(Exception):
            db.session.execute(
                db.update(AuditLog)
                .where(AuditLog.id == log_id)
                .values(action="HACKED")
            )
            db.session.commit()

        db.session.rollback()

        saved_log = db.session.get(AuditLog, log_id)

        assert saved_log is not None
        assert saved_log.action == "DOCUMENT_UPLOAD"


# --------------------------------------------------
# TEST 14: AUDIT LOG DELETE PROTECTION
# --------------------------------------------------

def test_audit_log_cannot_be_deleted(app):
    with app.app_context():
        log = AuditLog(
            action="DOCUMENT_UPLOAD",
            resource_type="document",
            resource_id="123",
            outcome="success",
            previous_hash="GENESIS",
            entry_hash="b" * 64
        )

        db.session.add(log)
        db.session.commit()

        log_id = log.id

        with pytest.raises(Exception):
            db.session.execute(
                db.delete(AuditLog)
                .where(AuditLog.id == log_id)
            )
            db.session.commit()

        db.session.rollback()

        saved_log = db.session.get(AuditLog, log_id)

        assert saved_log is not None

def test_owner_can_find_own_document(app, client, users):
    with app.app_context():
        document_id = create_document(users["alice_id"])

    alice_headers = login(client, "alice@test.com", "AliceSecure@123")
    response = client.get("/api/documents/search", headers=alice_headers)

    assert response.status_code == 200
    assert response.json["count"] == 1
    assert response.json["documents"][0]["id"] == document_id


def test_user_cannot_discover_private_documents(app, client, users):
    with app.app_context():
        create_document(users["alice_id"])

    bob_headers = login(client, "bob@test.com", "BobSecure@123")
    response = client.get("/api/documents/search", headers=bob_headers)

    assert response.status_code == 200
    assert response.json["count"] == 0
    assert response.json["documents"] == []


def test_user_can_find_shared_document(app, client, users):
    with app.app_context():
        document_id = create_document(users["alice_id"])
        permission = DocumentPermission(
            document_id=document_id,
            user_id=users["bob_id"],
            permission="read"
        )
        db.session.add(permission)
        db.session.commit()

    bob_headers = login(client, "bob@test.com", "BobSecure@123")
    response = client.get("/api/documents/search", headers=bob_headers)

    assert response.status_code == 200
    assert response.json["count"] == 1
    assert response.json["documents"][0]["id"] == document_id


def test_revoked_document_disappears_from_search(app, client, users):
    with app.app_context():
        document_id = create_document(users["alice_id"])
        permission = DocumentPermission(
            document_id=document_id,
            user_id=users["bob_id"],
            permission="read"
        )
        db.session.add(permission)
        db.session.commit()

    bob_headers = login(client, "bob@test.com", "BobSecure@123")
    alice_headers = login(client, "alice@test.com", "AliceSecure@123")

    before = client.get("/api/documents/search", headers=bob_headers)
    assert before.status_code == 200
    assert before.json["count"] == 1

    revoke = client.delete(
        f"/api/permissions/{document_id}/revoke/{users['bob_id']}",
        headers=alice_headers
    )
    assert revoke.status_code == 200

    after = client.get("/api/documents/search", headers=bob_headers)
    assert after.status_code == 200
    assert after.json["count"] == 0


def test_search_rejects_invalid_date(app, client, users):
    alice_headers = login(client, "alice@test.com", "AliceSecure@123")

    response = client.get(
        "/api/documents/search?date_from=not-a-date",
        headers=alice_headers
    )

    assert response.status_code == 400
    
# AUDIT CHAIN INTEGRITY TESTS

def test_valid_audit_chain_passes(app):
    with app.app_context():
        with app.test_request_context("/"):
            record_audit(
                action="DOCUMENT_UPLOAD",
                resource_type="document",
                resource_id="101"
            )

            record_audit(
                action="DOCUMENT_DOWNLOAD",
                resource_type="document",
                resource_id="101"
            )

        assert verify_audit_chain() is True


def test_modified_audit_record_is_detected(app):
    with app.app_context():
        with app.test_request_context("/"):
            record_audit(
                action="DOCUMENT_UPLOAD",
                resource_type="document",
                resource_id="102"
            )

        from sqlalchemy import text

        db.session.execute(text(
            "DROP TRIGGER IF EXISTS prevent_audit_update"
        ))

        db.session.execute(text(
            "UPDATE audit_logs SET action = 'HACKED' WHERE id = 1"
        ))
        db.session.commit()

        assert verify_audit_chain() is False


def test_broken_previous_hash_is_detected(app):
    with app.app_context():
        with app.test_request_context("/"):
            record_audit(
                action="DOCUMENT_UPLOAD",
                resource_type="document",
                resource_id="103"
            )

            record_audit(
                action="DOCUMENT_DOWNLOAD",
                resource_type="document",
                resource_id="103"
            )

        from sqlalchemy import text

        db.session.execute(text(
            "DROP TRIGGER IF EXISTS prevent_audit_update"
        ))

        db.session.execute(text(
            "UPDATE audit_logs SET previous_hash = 'BROKEN' WHERE id = 2"
        ))
        db.session.commit()

        assert verify_audit_chain() is False
        
# ADMIN DASHBOARD SECURITY TESTS

def test_admin_can_view_activity_logs(app, client, users):
    with app.app_context():
        admin = User(
            name="Admin",
            email="admin@test.com",
            role="admin"
        )
        admin.set_password("AdminSecure@123")
        db.session.add(admin)
        db.session.commit()

    admin_headers = login(
        client,
        "admin@test.com",
        "AdminSecure@123"
    )

    response = client.get(
        "/api/admin/activity",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert "activities" in response.json
    assert "total" in response.json


def test_regular_user_cannot_view_activity_logs(app, client, users):
    alice_headers = login(
        client,
        "alice@test.com",
        "AliceSecure@123"
    )

    response = client.get(
        "/api/admin/activity",
        headers=alice_headers
    )

    assert response.status_code == 403
