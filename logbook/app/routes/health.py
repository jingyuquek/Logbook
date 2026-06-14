"""
Health Check Routes
Provides liveness, readiness, and security posture endpoints.
"""
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from app.decorators.auth import login_required, role_required
from app.models import Role

health_bp = Blueprint('health', __name__, url_prefix='/health')

@health_bp.route('/')
def liveness():
    """
    Liveness Probe: Indicates the application is running.
    Used by Kubernetes/orchestrators to determine if the pod needs restarting.
    """
    return jsonify({"status": "healthy", "service": "vehicle-logbook"}), 200

@health_bp.route('/ready')
def readiness():
    """
    Readiness Probe: Indicates the application is ready to serve traffic.
    Checks critical dependencies (Database).
    """
    try:
        # Attempt a simple query to verify DB connection
        from app import db
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "ready",
            "dependencies": {
                "database": "connected"
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: Database connection error - {str(e)}")
        return jsonify({
            "status": "unavailable",
            "dependencies": {
                "database": "disconnected",
                "error": str(e)
            }
        }), 503

@health_bp.route('/security')
@login_required
@role_required(Role.SUPERADMIN)
def security_posture():
    """
    Security Posture Check: Audits the current security configuration.
    Only accessible to Superadmins.
    """
    issues = []
    warnings = []
    checks = {}

    # 1. Check SECRET_KEY
    secret_key = current_app.config.get('SECRET_KEY')
    if not secret_key or secret_key == 'dev-secret-key-change-in-production':
        issues.append("CRITICAL: SECRET_KEY is missing or set to default.")
        checks['secret_key'] = "INVALID"
    elif len(secret_key) < 32:
        warnings.append("WARNING: SECRET_KEY is less than 32 characters.")
        checks['secret_key'] = "WEAK"
    else:
        checks['secret_key'] = "OK"

    # 2. Check DEBUG Mode
    debug_mode = current_app.config.get('DEBUG', False)
    if debug_mode:
        issues.append("CRITICAL: DEBUG mode is enabled in production.")
        checks['debug_mode'] = "ENABLED (UNSAFE)"
    else:
        checks['debug_mode'] = "DISABLED"

    # 3. Check Environment
    env = current_app.config.get('ENV', 'production')
    if env == 'development':
        warnings.append("INFO: Running in Development environment.")
    checks['environment'] = env

    # 4. Check HTTPS (Optional check based on config)
    # In a real deployment behind a proxy, this might be handled externally,
    # but we check if the app expects it.
    checks['https_enforced'] = current_app.config.get('PREFERRED_URL_SCHEME', 'http') == 'https'

    status = "SECURE"
    http_code = 200
    
    if issues:
        status = "INSECURE"
        http_code = 500
    elif warnings:
        status = "WARNINGS_PRESENT"

    return jsonify({
        "status": status,
        "timestamp": "checked_at_runtime",
        "checks": checks,
        "issues": issues,
        "warnings": warnings
    }), http_code
