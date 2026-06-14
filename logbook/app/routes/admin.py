from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from app.models import db, User, Unit, Company

admin_bp = Blueprint("admin", __name__)

# Aliases for backward compatibility with templates
@admin_bp.route("/admin_approvals")
def admin_approvals():
    """Alias for company admin approvals page"""
    return redirect(url_for("tasks.company_list"))

@admin_bp.route("/approve_user", methods=["POST"])
def approve_user():
    """Alias for approving company admin"""
    return redirect(url_for("admin.approve_company_admin"))

@admin_bp.route("/decline_user", methods=["POST"])
def decline_user():
    """Alias for denying company admin"""
    return redirect(url_for("admin.deny_unit_admin"))

@admin_bp.route("/deny_company_admin", methods=["POST"])
def deny_company_admin():
    """Alias for denying company admin"""
    return redirect(url_for("admin.approve_company_admin"))

@admin_bp.route("/approve_company_admins", methods=["POST"])
def approve_company_admins():
    """Alias for approving company admin"""
    return redirect(url_for("admin.approve_company_admin"))

@admin_bp.route("/remove_company_admin", methods=["POST"])
def remove_company_admin():
    """Remove company admin - unit admin only"""
    if session.get("role") != "unit_admin":
        return redirect(url_for("auth.login"))
    
    admin_id = request.form.get("admin_id")
    user = db.session.get(User, admin_id)
    
    if user and user.role == "admin":
        db.session.delete(user)
        db.session.commit()
        flash("Company admin removed successfully.", "success")
    
    return redirect(url_for("admin.unit_admin_dashboard"))

@admin_bp.route("/reset_company_passcode", methods=["POST"])
def reset_company_passcode():
    """Reset company passcode - unit admin only"""
    if session.get("role") != "unit_admin":
        return redirect(url_for("auth.login"))
    
    company_id = request.form.get("company_id")
    new_passcode = request.form.get("new_passcode", "").strip()
    company = db.session.get(Company, company_id)
    
    if company and new_passcode:
        company.passcode_hash = generate_password_hash(new_passcode)
        db.session.commit()
        flash("Company passcode reset successfully.", "success")
    
    return redirect(url_for("admin.unit_admin_dashboard"))

@admin_bp.route("/remove_company", methods=["POST"])
def remove_company():
    """Remove company - unit admin only"""
    if session.get("role") != "unit_admin":
        return redirect(url_for("auth.login"))
    
    company_id = request.form.get("company_id")
    company = db.session.get(Company, company_id)
    
    if company:
        # Check if company has any admins assigned
        admins = User.query.filter_by(company_id=company.id, role="admin").all()
        if not admins:
            db.session.delete(company)
            db.session.commit()
            flash("Company removed successfully.", "success")
        else:
            flash("Cannot remove company with assigned admins. Remove admins first.", "error")
    
    return redirect(url_for("admin.unit_admin_dashboard"))

@admin_bp.route("/superadmin", methods=["GET", "POST"])
def superadmin_dashboard():
    if session.get("role") != "superadmin": return redirect(url_for("auth.login"))

    if request.method == "POST" and "unit_name" in request.form:
        name = request.form.get("unit_name", "").strip()
        code = request.form.get("unit_passcode", "").strip()
        if name and code and not Unit.query.filter_by(name=name).first():
            db.session.add(Unit(name=name, passcode_hash=generate_password_hash(code)))
            db.session.commit()
            flash("Unit added successfully.", "success")
        return redirect(url_for("admin.superadmin_dashboard"))

    units = [{"unit": u, "admins": User.query.filter_by(unit_id=u.id, role="unit_admin", is_approved=True).all()} for u in Unit.query.all()]
    pending = User.query.filter_by(role="unit_admin", is_approved=False).all()
    return render_template("superadmin_dashboard.html", units=units, pending_admins=pending)


@admin_bp.route("/approve_unit_admin", methods=["POST"])
def approve_unit_admin():
    if session.get("role") != "superadmin": return redirect(url_for("auth.login"))
    user = db.session.get(User, request.form.get("user_id"))
    if user:
        user.is_approved = True
        db.session.commit()
    return redirect(url_for("admin.superadmin_dashboard"))

@admin_bp.route("/remove_unit_admin", methods=["POST"])
def remove_unit_admin():
    if session.get("role") != "superadmin": 
        return redirect(url_for("auth.login"))
        
    user_id = request.form.get("user_id")
    user = db.session.get(User, user_id)
    
    if user and user.role == "unit_admin":
        db.session.delete(user)
        db.session.commit()
        flash("Unit admin removed successfully.", "success")
        
    return redirect(url_for("admin.superadmin_dashboard"))


@admin_bp.route("/unit_admin", methods=["GET", "POST"])
def unit_admin_dashboard():
    if session.get("role") != "unit_admin": return redirect(url_for("auth.login"))
    current_admin = db.session.get(User, session["user_id"])

    if request.method == "POST" and "company_name" in request.form:
        name = request.form.get("company_name", "").strip()
        code = request.form.get("company_passcode", "").strip()
        if name and code and not Company.query.filter_by(name=name, unit_id=current_admin.unit_id).first():
            db.session.add(Company(name=name, passcode_hash=generate_password_hash(code), unit=current_admin.unit))
            db.session.commit()
            flash("Company registered under your unit.", "success")
        return redirect(url_for("admin.unit_admin_dashboard"))

    companies = [{"company": c, "admins": User.query.filter_by(company_id=c.id, role="admin", is_approved=True).all()} for c in Company.query.filter_by(unit_id=current_admin.unit_id).all()]
    pending = User.query.filter_by(role="admin", is_approved=False, unit_id=current_admin.unit_id).all()
    return render_template("unit_admin_dashboard.html", companies=companies, pending_admins=pending)

@admin_bp.route("/approve_company_admin", methods=["POST"])
def approve_company_admin():
    if session.get("role") != "unit_admin": return redirect(url_for("auth.login"))
    user = db.session.get(User, request.form.get("admin_id"))
    if user:
        user.is_approved = True
        db.session.commit()
    return redirect(url_for("admin.unit_admin_dashboard"))

@admin_bp.route("/reset_unit_passcode", methods=["POST"])
def reset_unit_passcode():
    if session.get("role") != "superadmin":
        return redirect(url_for("auth.login"))
    
    unit_id = request.form.get("unit_id")
    new_passcode = request.form.get("new_passcode", "").strip()
    unit = db.session.get(Unit, unit_id)
    
    if unit and new_passcode:
        unit.passcode_hash = generate_password_hash(new_passcode)
        db.session.commit()
        flash("Unit passcode reset successfully.", "success")
    
    return redirect(url_for("admin.superadmin_dashboard"))

@admin_bp.route("/remove_unit", methods=["POST"])
def remove_unit():
    if session.get("role") != "superadmin":
        return redirect(url_for("auth.login"))
    
    unit_id = request.form.get("unit_id")
    unit = db.session.get(Unit, unit_id)
    
    if unit:
        # Check if unit has any admins assigned
        admins = User.query.filter_by(unit_id=unit.id, role="unit_admin").all()
        if not admins:
            db.session.delete(unit)
            db.session.commit()
            flash("Unit removed successfully.", "success")
        else:
            flash("Cannot remove unit with assigned admins. Remove admins first.", "error")
    
    return redirect(url_for("admin.superadmin_dashboard"))

@admin_bp.route("/deny_unit_admin", methods=["POST"])
def deny_unit_admin():
    if session.get("role") != "superadmin":
        return redirect(url_for("auth.login"))
    
    user_id = request.form.get("user_id")
    user = db.session.get(User, user_id)
    
    if user and user.role == "unit_admin" and not user.is_approved:
        db.session.delete(user)
        db.session.commit()
        flash("Unit admin request denied.", "success")
    
    return redirect(url_for("admin.superadmin_dashboard"))