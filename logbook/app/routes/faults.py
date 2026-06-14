from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from app.models import db, User, Vehicle, Fault, SGT

faults_bp = Blueprint("faults", __name__)


@faults_bp.route("/vehicle/<string:license_plate>/faults")
def view_faults(license_plate):
    """View all faults for a specific vehicle"""
    if 'user_id' not in session:
        return redirect(url_for("auth.login"))
    
    user = db.session.get(User, session['user_id'])
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
def add_fault(license_plate):
    """Add a new fault report for a vehicle"""
    if 'user_id' not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("auth.login"))
    
    user = db.session.get(User, session['user_id'])
    vehicle = Vehicle.query.filter_by(license_plate=license_plate, company_id=user.company_id).first()
    
    if not vehicle:
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))
    
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        
        if not description:
            flash("Fault description is required.", "warning")
            return redirect(request.url)
        
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
        return redirect(url_for("faults.view_faults", license_plate=license_plate))
    
    # GET request - show the form
    return render_template("add_fault.html", vehicle=vehicle, user=user)


@faults_bp.route("/vehicle/<int:vehicle_id>/update_shutter", methods=["POST"])
def update_shutter(vehicle_id):
    """Update the shutter number for a vehicle (admin/manager only)"""
    if 'user_id' not in session:
        return redirect(url_for("auth.login"))
    
    user = db.session.get(User, session['user_id'])
    
    if user.role not in ['admin', 'manager']:
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))
    
    vehicle = db.session.get(Vehicle, vehicle_id)
    
    if not vehicle or vehicle.company_id != user.company_id:
        flash("Vehicle not found.", "danger")
        return redirect(url_for("core.dashboard"))
    
    vehicle.shutter_number = request.form.get("shutter_number", "").strip()
    db.session.commit()
    
    flash("Shutter number updated.", "success")
    return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))
