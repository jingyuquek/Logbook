from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User, Unit, Company

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()
        unit_name = request.form.get("unit_name", "").strip()

        if not username or not password or not role or not unit_name:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        unit = Unit.query.filter(Unit.name.ilike(unit_name)).first()
        if not unit:
            flash("Selected unit does not exist.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("auth.register"))

        company_id = None
        if role == "unit_admin":
            unit_passcode = request.form.get("unit_passcode", "").strip()
            if not unit_passcode or not check_password_hash(unit.passcode_hash, unit_passcode):
                flash("Invalid unit passcode.", "danger")
                return redirect(url_for("auth.register"))
        else:
            company_name = request.form.get("company_name", "").strip()
            company = Company.query.filter(Company.name.ilike(company_name), Company.unit_id == unit.id).first()
            if not company:
                flash("Selected company does not exist inside this unit.", "danger")
                return redirect(url_for("auth.register"))

            company_passcode = request.form.get("company_passcode", "").strip()
            if not company_passcode or not check_password_hash(company.passcode_hash, company_passcode):
                flash("Invalid company passcode.", "danger")
                return redirect(url_for("auth.register"))
            company_id = company.id

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            unit=unit,          # Object optimization assignment!
            company_id=company_id,
            is_approved=False
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registration submitted! Please await administrative verification.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth_bp.route("/", methods=["GET"])
def start():
    return redirect(url_for('auth.login'))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if user.role != "superadmin" and not user.is_approved:
                flash("Your account is pending approval.", "warning")
                return redirect(url_for("auth.login"))

            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "superadmin":
                return redirect(url_for("admin.superadmin_dashboard"))
            elif user.role == "unit_admin":
                return redirect(url_for("admin.unit_admin_dashboard"))
            else:
                return redirect(url_for("core.dashboard"))

        flash("Invalid username or password.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route('/logout', methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))