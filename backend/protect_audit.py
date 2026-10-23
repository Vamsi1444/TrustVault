from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():

    # Prevent modification of audit records
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS prevent_audit_update
        BEFORE UPDATE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'Audit records cannot be modified');
        END;
    """))

    # Prevent deletion of audit records
    db.session.execute(text("""
        CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
        BEFORE DELETE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'Audit records cannot be deleted');
        END;
    """))

    db.session.commit()

    print("Audit protection triggers created successfully!")

    # Verify that both triggers exist
    result = db.session.execute(text("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'trigger'
        AND tbl_name = 'audit_logs'
        ORDER BY name;
    """))

    triggers = [row[0] for row in result]

    for trigger in triggers:
        print("Found trigger:", trigger)

    if (
        "prevent_audit_update" in triggers
        and "prevent_audit_delete" in triggers
    ):
        print("\nSUCCESS: Both audit protection triggers are active.")
    else:
        print("\nERROR: One or more triggers are missing.")