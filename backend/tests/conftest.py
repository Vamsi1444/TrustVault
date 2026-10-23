import sys
from pathlib import Path

import pytest
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def app():
    from app import create_app
    from app.extensions import db

    test_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only-32-bytes"
    })

    with test_app.app_context():
        db.drop_all()
        db.create_all()

        db.session.execute(text("""
            CREATE TRIGGER prevent_audit_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'Audit records cannot be modified');
            END;
        """))

        db.session.execute(text("""
            CREATE TRIGGER prevent_audit_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'Audit records cannot be deleted');
            END;
        """))

        db.session.commit()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()