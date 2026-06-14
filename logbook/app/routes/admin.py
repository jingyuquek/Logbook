from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from app.models import db, User, Unit, Company, AuditLog
from app.decorators.auth import login_required, role_required, superadmin_required, unit_admin_required
from app.services import UserService
from app.config import Role, FlashCategory
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


def get_client_info():
    """Extract client IP and user agent from request."""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:255]
    return ip_address, user_agent


@admin_bp.route("/remove_company_admin", methods=["POST"])
@login_required
@unit_admin_required
def remove_company_admin():
    """Remove company admin - unit admin only"""
    admin_id = request.form.get("admin_id")
    user = db.session.get(User, admin_id)
    
    if user and user.role == Role.COMPANY_ADMIN:
        try:
            old_values = {"username": user.username, "role": user.role}
            success = UserService.reject_user(user)
            if success:
                # Audit log
                ip_address, user_agent = get_client_info()
                AuditLog.log_action(
                    user_id=session['user_id'],
                    action="DELETE",
                    model_name="User",
                    record_id=user.id,
                    old_values=old_values,
                    new_values={"status": "removed"},
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                flash("Company admin removed successfully.", FlashCategory.SUCCESS)
            else:
                flash("Failed to remove company admin.", FlashCategory.ERROR)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error removing company admin: {e}")
            flash("An error occurred while removing company admin.", FlashCategory.ERROR)
    
    return redirect(url_for("admin.unit_admin_dashboard"))


@admin_bp.route("/reset_company_passcode", methods=["POST"])
@login_required
@unit_admin_required
def reset_company_passcode():
    """Reset company passcode - unit admin only"""
    company_id = request.form.get("company_id")
    new_passcode = request.form.get("new_passcode", "").strip()
    company = db.session.get(Company, company_id)
    
    if company and new_passcode:
        try:
            old_values = {"passcode_hash": company.passcode_hash[:10]}  # Store partial hash for audit
            company.passcode_hash = generate_password_hash(new_passcode)
            db.session.commit()
            
            # Audit log
            ip_address, user_agent = get_client_info()
            AuditLog.log_action(
                user_id=session['user_id'],
                action="UPDATE",
                model_name="Company",
                record_id=company.id,
                old_values=old_values,
                new_values={"passcode_reset": True},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            flash("Company passcode reset successfully.", FlashCategory.SUCCESS)
            logger.info(f"Company passcode reset for company {company_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reset company passcode: {str(e)}", exc_info=True)
            flash("Failed to reset company passcode.", FlashCategory.ERROR)
    
    return redirect(url_for("admin.unit_admin_dashboard"))


@admin_bp.route("/remove_company", methods=["POST"])
@login_required
@unit_admin_required
def remove_company():
    """Remove company - unit admin only"""
    company_id = request.form.get("company_id")
    company = db.session.get(Company, company_id)
    
    if company:
        # Check if company has any admins assigned (use eager loading)
        admins = db.session.execute(
            select(User).where(
                User.company_id == company.id,
                User.role == Role.COMPANY_ADMIN
            )
        ).scalars().all()
        
        if not admins:
            try:
                old_values = {"name": company.name, "id": company.id}
                db.session.delete(company)
                db.session.commit()
                
                # Audit log
                ip_address, user_agent = get_client_info()
                AuditLog.log_action(
                    user_id=session['user_id'],
                    action="DELETE",
                    model_name="Company",
                    record_id=company.id,
                    old_values=old_values,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                flash("Company removed successfully.", FlashCategory.SUCCESS)
                logger.info(f"Company {company.name} removed")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to remove company: {str(e)}", exc_info=True)
                flash("Failed to remove company.", FlashCategory.ERROR)
        else:
            flash("Cannot remove company with assigned admins. Remove admins first.", FlashCategory.WARNING)
    
    return redirect(url_for("admin.unit_admin_dashboard"))


@admin_bp.route("/superadmin", methods=["GET", "POST"])
@login_required
@superadmin_required
def superadmin_dashboard():
    """Superadmin dashboard for managing units and unit admins"""
    if request.method == "POST" and "unit_name" in request.form:
        name = request.form.get("unit_name", "").strip()
        code = request.form.get("unit_passcode", "").strip()
        if name and code and not Unit.query.filter_by(name=name).first():
            try:
                new_unit = Unit(name=name, passcode_hash=generate_password_hash(code))
                db.session.add(new_unit)
                db.session.commit()
                
                # Audit log
                ip_address, user_agent = get_client_info()
                AuditLog.log_action(
                    user_id=session['user_id'],
                    action="CREATE",
                    model_name="Unit",
                    record_id=new_unit.id,
                    new_values={"name": name},
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                flash("Unit added successfully.", FlashCategory.SUCCESS)
                logger.info(f"Unit {name} added by superadmin")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to add unit: {str(e)}", exc_info=True)
                flash("Failed to add unit.", FlashCategory.ERROR)
        return redirect(url_for("admin.superadmin_dashboard"))

    # Use eager loading for units and their admins
    units_data = db.session.execute(
        select(Unit).options(joinedload(Unit.admins))
    ).scalars().all()
    
    # Build units list with pre-loaded admins
    units = []
    for u in units_data:
        admins = [admin for admin in u.admins if admin.role == Role.UNIT_ADMIN and admin.is_approved]
        units.append({"unit": u, "admins": admins})
    
    # Get pending unit admins with eager loading
    pending = db.session.execute(
        select(User).where(
            User.role == Role.UNIT_ADMIN,
            User.is_approved == False
        ).options(joinedload(User.unit))
    ).scalars().all()
    
    return render_template("superadmin_dashboard.html", units=units, pending_admins=pending)


@admin_bp.route("/approve_unit_admin", methods=["POST"])
@login_required
@superadmin_required
def approve_unit_admin():
    """Approve a pending unit admin"""
    user = db.session.get(User, request.form.get("user_id"))
    if user:
        try:
            old_values = {"is_approved": user.is_approved}
            user.is_approved = True
            db.session.commit()
            
            # Audit log
            ip_address, user_agent = get_client_info()
            AuditLog.log_action(
                user_id=session['user_id'],
                action="UPDATE",
                model_name="User",
                record_id=user.id,
                old_values=old_values,
                new_values={"is_approved": True},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            flash("Unit admin approved successfully.", FlashCategory.SUCCESS)
            logger.info(f"Unit admin {user.username} approved")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to approve unit admin: {str(e)}", exc_info=True)
            flash("Failed to approve unit admin.", FlashCategory.ERROR)
    return redirect(url_for("admin.superadmin_dashboard"))


@admin_bp.route("/remove_unit_admin", methods=["POST"])
@login_required
@superadmin_required
def remove_unit_admin():
    """Remove a unit admin"""
    user_id = request.form.get("user_id")
    user = db.session.get(User, user_id)
    
    if user and user.role == Role.UNIT_ADMIN:
        try:
            old_values = {"username": user.username, "role": user.role}
            db.session.delete(user)
            db.session.commit()
            
            # Audit log
            ip_address, user_agent = get_client_info()
            AuditLog.log_action(
                user_id=session['user_id'],
                action="DELETE",
                model_name="User",
                record_id=user.id,
                old_values=old_values,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            flash("Unit admin removed successfully.", FlashCategory.SUCCESS)
            logger.info(f"Unit admin {user.username} removed")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to remove unit admin: {str(e)}", exc_info=True)
            flash("Failed to remove unit admin.", FlashCategory.ERROR)
        
    return redirect(url_for("admin.superadmin_dashboard"))


@admin_bp.route("/unit_admin", methods=["GET", "POST"])
@login_required
@unit_admin_required
def unit_admin_dashboard():
    """Unit admin dashboard for managing companies and company admins"""
    current_admin = db.session.get(User, session["user_id"])

    if request.method == "POST" and "company_name" in request.form:
        name = request.form.get("company_name", "").strip()
        code = request.form.get("company_passcode", "").strip()
        if name and code and not Company.query.filter_by(name=name, unit_id=current_admin.unit_id).first():
            try:
                db.session.add(Company(name=name, passcode_hash=generate_password_hash(code), unit=current_admin.unit))
                db.session.commit()
                flash("Company registered under your unit.", FlashCategory.SUCCESS)
                logger.info(f"Company {name} registered by unit admin {current_admin.username}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to register company: {str(e)}", exc_info=True)
                flash("Failed to register company.", FlashCategory.ERROR)
        return redirect(url_for("admin.unit_admin_dashboard"))

    # Use eager loading for companies and their admins
    companies_data = db.session.execute(
        select(Company).where(Company.unit_id == current_admin.unit_id).options(joinedload(Company.admins))
    ).scalars().all()
    
    # Build companies list with pre-loaded admins
    companies = []
    for c in companies_data:
        admins = [admin for admin in c.admins if admin.role == Role.COMPANY_ADMIN and admin.is_approved]
        companies.append({"company": c, "admins": admins})
    
    # Get pending company admins with eager loading
    pending = db.session.execute(
        select(User).where(
            User.role == Role.COMPANY_ADMIN,
            User.is_approved == False,
            User.unit_id == current_admin.unit_id
        ).options(joinedload(User.company))
    ).scalars().all()
    
    return render_template("unit_admin_dashboard.html", companies=companies, pending_admins=pending)


@admin_bp.route("/approve_company_admin", methods=["POST"])
@login_required
@unit_admin_required
def approve_company_admin():
    """Approve a pending company admin"""
    user = db.session.get(User, request.form.get("admin_id"))
    if user:
        try:
            user.is_approved = True
            db.session.commit()
            flash("Company admin approved successfully.", FlashCategory.SUCCESS)
            logger.info(f"Company admin {user.username} approved")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to approve company admin: {str(e)}", exc_info=True)
            flash("Failed to approve company admin.", FlashCategory.ERROR)
    return redirect(url_for("admin.unit_admin_dashboard"))


@admin_bp.route("/reset_unit_passcode", methods=["POST"])
@login_required
@superadmin_required
def reset_unit_passcode():
    """Reset unit passcode - superadmin only"""
    unit_id = request.form.get("unit_id")
    new_passcode = request.form.get("new_passcode", "").strip()
    unit = db.session.get(Unit, unit_id)
    
    if unit and new_passcode:
        try:
            unit.passcode_hash = generate_password_hash(new_passcode)
            db.session.commit()
            flash("Unit passcode reset successfully.", FlashCategory.SUCCESS)
            logger.info(f"Unit passcode reset for unit {unit_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reset unit passcode: {str(e)}", exc_info=True)
            flash("Failed to reset unit passcode.", FlashCategory.ERROR)
    
    return redirect(url_for("admin.superadmin_dashboard"))


@admin_bp.route("/remove_unit", methods=["POST"])
@login_required
@superadmin_required
def remove_unit():
    """Remove a unit - superadmin only"""
    unit_id = request.form.get("unit_id")
    unit = db.session.get(Unit, unit_id)
    
    if unit:
        # Check if unit has any admins assigned (use eager loading)
        admins = db.session.execute(
            select(User).where(
                User.unit_id == unit.id,
                User.role == Role.UNIT_ADMIN
            )
        ).scalars().all()
        
        if not admins:
            try:
                db.session.delete(unit)
                db.session.commit()
                flash("Unit removed successfully.", FlashCategory.SUCCESS)
                logger.info(f"Unit {unit.name} removed")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to remove unit: {str(e)}", exc_info=True)
                flash("Failed to remove unit.", FlashCategory.ERROR)
        else:
            flash("Cannot remove unit with assigned admins. Remove admins first.", FlashCategory.WARNING)
    
    return redirect(url_for("admin.superadmin_dashboard"))


@admin_bp.route("/deny_unit_admin", methods=["POST"])
@login_required
@superadmin_required
def deny_unit_admin():
    """Deny a unit admin registration request"""
    user_id = request.form.get("user_id")
    user = db.session.get(User, user_id)
    
    if user and user.role == Role.UNIT_ADMIN and not user.is_approved:
        try:
            db.session.delete(user)
            db.session.commit()
            flash("Unit admin request denied.", FlashCategory.SUCCESS)
            logger.info(f"Unit admin request denied for {user.username}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to deny unit admin: {str(e)}", exc_info=True)
            flash("Failed to deny unit admin request.", FlashCategory.ERROR)
    
    return redirect(url_for("admin.superadmin_dashboard"))