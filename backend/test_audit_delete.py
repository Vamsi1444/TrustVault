from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(
            text("DELETE FROM audit_logs WHERE id = 1")
        )
        db.session.commit()

        print("WARNING: Deletion was not blocked!")

    except Exception as error:
        db.session.rollback()
        print("SUCCESS: Deletion blocked!")
        print("Database response:", error)