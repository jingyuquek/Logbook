from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, cast, String

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Attach driver extension safely
    db.init_app(app)

    # Blueprint registers
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.assets import assets_bp
    from app.routes.core import core_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(core_bp)

    return app