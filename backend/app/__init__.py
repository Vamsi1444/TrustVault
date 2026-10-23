import os

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from app.extensions import db
from app.config import DevelopmentConfig, ProductionConfig

from app import models

from app.routes.auth import auth_bp
from app.routes.documents import documents_bp
from app.routes.permissions import permissions_bp
from app.routes.admin import admin_bp


def create_app(test_config=None):

    app = Flask(__name__)

    environment = os.getenv("FLASK_ENV", "development")

    if environment == "production":
        ProductionConfig.validate()
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    if test_config:
        app.config.update(test_config)

    frontend_origins = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://localhost:5174"
    )

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    origin.strip()
                    for origin in frontend_origins.split(",")
                ]
            }
        }
    )

    db.init_app(app)

    JWTManager(app)

    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(permissions_bp)

    with app.app_context():
        db.create_all()

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "application": "TrustVault",
            "status": "running",
            "message": "Secure document sharing platform"
        })

    return app