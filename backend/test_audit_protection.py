from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(
            text("UPDATE audit_logs SET action = 'HACKED' WHERE id = 1")
        )
        db.session.commit()

        print("WARNING: Update was not blocked!")

    except Exception as error:
        db.session.rollback()
        print("SUCCESS: Update blocked!")
        print("Database response:", error)