from flask import Flask
from app.config import Config
from app.extensions import init_extensions, db, login_manager
import logging


def create_app():
    """
    Application factory for creating Flask app instance.
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Set max content length for uploads
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT
    )
    logger = logging.getLogger(__name__)
    logger.info("Creating Flask application")
    
    # Initialize extensions (db, login_manager, csrf)
    init_extensions(app)
    
    # Import models after db is initialized to avoid circular imports
    from app.models import User
    
    # Setup login manager user loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprints
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
    
    logger.info("Flask application created successfully")
    
    return app