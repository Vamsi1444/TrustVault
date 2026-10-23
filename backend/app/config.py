import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    JWT_ACCESS_TOKEN_EXPIRES = 900

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///trustvault.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        str(BASE_DIR / "private_uploads")
    )


class DevelopmentConfig(Config):
    SECRET_KEY = Config.SECRET_KEY or "dev-secret-change-me"
    JWT_SECRET_KEY = (
        Config.JWT_SECRET_KEY or Config.SECRET_KEY
    )
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

    @classmethod
    def validate(cls):
        required = ["SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "UPLOAD_FOLDER"]

        missing = [
            key for key in required
            if not os.getenv(key)
        ]

        if missing:
            raise RuntimeError(
                f"Missing production environment variables: {', '.join(missing)}"
            )

        if os.getenv("SECRET_KEY") == "dev-secret-change-me":
            raise RuntimeError("Default development secret is not allowed.")