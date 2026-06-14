from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User, Unit, Company, AuditLog
from app.decorators.auth import login_required
from app.config import Config, Role, FlashCategory
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


def get_client_info():
    """Extract client IP and user agent from request."""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:255]
    return ip_address, user_agent


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password against security policy.
    
    Args:
        password: The password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < Config.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {Config.PASSWORD_MIN_LENGTH} characters long."
    
    if Config.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    
    if Config.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    
    if Config.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    
    return True, ""

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration with validation and security checks."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()
        unit_name = request.form.get("unit_name", "").strip()

        # Validate required fields
        if not username or not password or not role or not unit_name:
            flash("All fields are required.", FlashCategory.DANGER)
            return redirect(url_for("auth.register"))

        # Validate password strength
        is_valid_password, password_error = validate_password(password)
        if not is_valid_password:
            flash(password_error, FlashCategory.DANGER)
            return redirect(url_for("auth.register"))

        # Validate role
        if role not in Role.all_roles():
            flash("Invalid role selected.", FlashCategory.DANGER)
            return redirect(url_for("auth.register"))

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", FlashCategory.DANGER)
            return redirect(url_for("auth.register"))

        # Find unit
        unit = Unit.query.filter(Unit.name.ilike(unit_name)).first()
        if not unit:
            flash("Selected unit does not exist.", FlashCategory.DANGER)
            return redirect(url_for("auth.register"))

        company_id = None
        if role == Role.UNIT_ADMIN:
            unit_passcode = request.form.get("unit_passcode", "").strip()
            if not unit_passcode or not check_password_hash(unit.passcode_hash, unit_passcode):
                flash("Invalid unit passcode.", FlashCategory.DANGER)
                return redirect(url_for("auth.register"))
        else:
            company_name = request.form.get("company_name", "").strip()
            company = Company.query.filter(
                Company.name.ilike(company_name), 
                Company.unit_id == unit.id
            ).first()
            if not company:
                flash("Selected company does not exist inside this unit.", FlashCategory.DANGER)
                return redirect(url_for("auth.register"))

            company_passcode = request.form.get("company_passcode", "").strip()
            if not company_passcode or not check_password_hash(company.passcode_hash, company_passcode):
                flash("Invalid company passcode.", FlashCategory.DANGER)
                return redirect(url_for("auth.register"))
            company_id = company.id

        try:
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role,
                unit=unit,
                company_id=company_id,
                is_approved=False
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Audit log
            ip_address, user_agent = get_client_info()
            AuditLog.log_action(
                user_id=new_user.id,
                action="CREATE",
                model_name="User",
                record_id=new_user.id,
                new_values={"username": username, "role": role},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"User {username} registered successfully with role {role}")

            flash("Registration submitted! Please await administrative verification.", FlashCategory.SUCCESS)
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration failed for {username}: {str(e)}", exc_info=True)
            flash("Registration failed. Please try again.", FlashCategory.ERROR)
            return redirect(url_for("auth.register"))

    return render_template("register.html")

@auth_bp.route("/", methods=["GET"])
def start():
    return redirect(url_for('auth.login'))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with session management."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Validate input
        if not username or not password:
            flash("Username and password are required.", FlashCategory.DANGER)
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if user.role != Role.SUPERADMIN and not user.is_approved:
                flash("Your account is pending approval.", FlashCategory.WARNING)
                return redirect(url_for("auth.login"))

            # Set session variables
            session["user_id"] = user.id
            session["role"] = user.role
            session["username"] = user.username
            session.permanent = True  # Use configured session lifetime

            # Audit log login
            ip_address, user_agent = get_client_info()
            AuditLog.log_action(
                user_id=user.id,
                action="LOGIN",
                model_name="User",
                record_id=user.id,
                new_values={"status": "success"},
                ip_address=ip_address,
                user_agent=user_agent
            )

            logger.info(f"User {username} logged in successfully")

            # Redirect based on role
            if user.role == Role.SUPERADMIN:
                return redirect(url_for("admin.superadmin_dashboard"))
            elif user.role == Role.UNIT_ADMIN:
                return redirect(url_for("admin.unit_admin_dashboard"))
            else:
                return redirect(url_for("core.dashboard"))

        # Audit failed login attempt
        ip_address, user_agent = get_client_info()
        AuditLog.log_action(
            user_id=None,
            action="LOGIN",
            model_name="User",
            new_values={"username": username, "status": "failed"},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        flash("Invalid username or password.", FlashCategory.DANGER)
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route('/logout', methods=["GET"])
@login_required
def logout():
    """Log out the current user and clear session."""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')
    
    # Audit log logout before clearing session
    ip_address, user_agent = get_client_info()
    AuditLog.log_action(
        user_id=user_id,
        action="LOGOUT",
        model_name="User",
        record_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    session.clear()
    logger.info(f"User {username} logged out")
    flash("You have been logged out successfully.", FlashCategory.INFO)
    return redirect(url_for('auth.login'))