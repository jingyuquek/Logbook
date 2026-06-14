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
    from app.routes.logbook import logbook_bp
    from app.routes.faults import faults_bp
    from app.routes.tasks import tasks_bp
    from app.routes.transfer import transfer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(logbook_bp)
    app.register_blueprint(faults_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(transfer_bp)

    return app