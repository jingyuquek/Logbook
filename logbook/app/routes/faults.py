from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from app.models import db, User, Vehicle, Fault, SGT
from app.decorators.auth import login_required
import logging

logger = logging.getLogger(__name__)

faults_bp = Blueprint("faults", __name__)


@faults_bp.route("/vehicle/<string:license_plate>/faults")
@login_required
def view_faults(license_plate):
    """View all faults for a specific vehicle"""
    user = request.current_user
    vehicle = Vehicle.query.filter_by(license_plate=license_plate, company_id=user.company_id).first()
    
    if not vehicle:
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))
    
    # Get all faults for this vehicle, ordered by most recent first
    faults = Fault.query.filter_by(vehicle_id=vehicle.id).order_by(Fault.last_updated.desc()).all()
    
    return render_template(
        "view_faults.html",
        vehicle=vehicle,
        faults=faults,
        user=user
    )


@faults_bp.route("/vehicle/<string:license_plate>/faults/add", methods=["GET", "POST"])
@login_required
def add_fault(license_plate):
    """Add a new fault report for a vehicle"""
    user = request.current_user
    vehicle = Vehicle.query.filter_by(license_plate=license_plate, company_id=user.company_id).first()
    
    if not vehicle:
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))
    
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        
        if not description:
            flash("Fault description is required.", "warning")
            return redirect(request.url)
        
        try:
            # Get the next fault number for this vehicle
            last_fault = Fault.query.filter_by(vehicle_id=vehicle.id).order_by(Fault.fault_number.desc()).first()
            next_number = 1 if not last_fault else last_fault.fault_number + 1
            
            # Create the fault record
            fault = Fault(
                fault_number=next_number,
                description=description,
                vehicle_id=vehicle.id,
                status="Open",
                date_reported=datetime.now(SGT),
                last_updated=datetime.now(SGT)
            )
            
            db.session.add(fault)
            db.session.commit()
            
            flash(f"Fault #{next_number} reported successfully.", "success")
            logger.info(f"Fault #{next_number} added for vehicle {vehicle.license_plate} by user {user.username}")
            return redirect(url_for("faults.view_faults", license_plate=license_plate))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to add fault: {str(e)}", exc_info=True)
            flash("Failed to report fault.", "error")
            return redirect(request.url)
    
    # GET request - show the form
    return render_template("add_fault.html", vehicle=vehicle, user=user)


@faults_bp.route("/vehicle/<int:vehicle_id>/update_shutter", methods=["POST"])
@login_required
def update_shutter(vehicle_id):
    """Update the shutter number for a vehicle (admin/manager only)"""
    from app.config import Role
    
    user = request.current_user
    
    if user.role.name not in [Role.SUPERADMIN, Role.COMPANY_ADMIN, Role.UNIT_ADMIN]:
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))
    
    vehicle = db.session.get(Vehicle, vehicle_id)
    
    if not vehicle or vehicle.company_id != user.company_id:
        flash("Vehicle not found.", "danger")
        return redirect(url_for("core.dashboard"))
    
    try:
        vehicle.shutter_number = request.form.get("shutter_number", "").strip()
        db.session.commit()
        flash("Shutter number updated.", "success")
        logger.info(f"Shutter number updated for vehicle {vehicle.license_plate}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update shutter number: {str(e)}", exc_info=True)
        flash("Failed to update shutter number.", "error")
    
    return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))
