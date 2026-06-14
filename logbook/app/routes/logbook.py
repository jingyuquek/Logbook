from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
from sqlalchemy import and_, cast, String
from app.models import db, User, Vehicle, Logbook, GenRun, Store, Company, Unit, SGT
from app.decorators.auth import login_required, role_required
from app.config import Role, FlashCategory
import logging

logger = logging.getLogger(__name__)

logbook_bp = Blueprint("logbook", __name__)


def to_time(t_str):
    """Convert time string to datetime object for comparison"""
    if not t_str:
        return None
    try:
        return datetime.strptime(t_str.replace(":", "").zfill(4), '%H%M')
    except ValueError:
        return None


def get_last_valid_logbook_value(vehicle_id, field):
    """Get the last valid (non-null/non-empty) value for a given field from logbook entries"""
    entry = Logbook.query.filter_by(vehicle_id=vehicle_id).order_by(Logbook.date.desc(), Logbook.id.desc()).first()
    if entry:
        value = getattr(entry, field, None)
        if value not in [None, '', '-', 'NaN']:
            return value
    return None


@logbook_bp.route("/vehicle/<string:license_plate>")
@login_required
def view_vehicle(license_plate):
    """View vehicle details with recent logbook entries and genrun status"""
    user = db.session.get(User, session['user_id'])
    vehicle = Vehicle.query.filter_by(license_plate=license_plate, company_id=user.company_id).first_or_404()
    
    # Get recent logbook entries (last 10)
    logbooks = Logbook.query.filter_by(vehicle_id=vehicle.id).order_by(Logbook.date.desc(), Logbook.start_time.desc()).limit(10).all()
    
    # Check genrun validity
    last_genrun = GenRun.query.filter_by(vehicle_id=vehicle.id).order_by(GenRun.performed_at.desc()).first()
    now_sg = datetime.now(SGT).replace(tzinfo=None)
    genrun_valid = False
    if last_genrun:
        last_run_time = last_genrun.performed_at.replace(tzinfo=None) if last_genrun.performed_at.tzinfo else last_genrun.performed_at
        genrun_valid = last_run_time >= (now_sg - timedelta(days=14))
    
    logger.info(f"Vehicle {license_plate} viewed by user {user.username}")
    
    return render_template(
        "view_vehicle.html",
        vehicle=vehicle,
        logbooks=logbooks,
        last_genrun=last_genrun,
        genrun_valid=genrun_valid,
        today=now_sg.date(),
        user=user
    )


@logbook_bp.route("/update_pol_level/<int:vehicle_id>", methods=["POST"])
@login_required
def update_pol_level(vehicle_id):
    """Update vehicle POL (Petrol, Oil, Lubricant) level"""
    user = db.session.get(User, session["user_id"])
    vehicle = Vehicle.query.filter_by(id=vehicle_id, company_id=user.company_id).first_or_404()
    
    val = request.form.get("pol_level")
    
    if val is not None and val.strip() != "":
        try:
            vehicle.pol_level = max(0, min(100, int(val)))
            db.session.commit()
            logger.info(f"POL level updated to {vehicle.pol_level}% for vehicle {vehicle.license_plate}")
            flash(f"POL level updated to {vehicle.pol_level}%.", FlashCategory.SUCCESS)
        except ValueError:
            logger.warning(f"Invalid POL level value for vehicle {vehicle_id}")
            flash("Invalid POL level value.", FlashCategory.DANGER)
    else:
        flash("No value received.", FlashCategory.DANGER)
    
    return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))


@logbook_bp.route("/toggle_vor/<int:vehicle_id>", methods=["POST"])
@login_required
def toggle_vor(vehicle_id):
    """Toggle vehicle VOR (Vehicle Out of Report/Service) status"""
    user = db.session.get(User, session["user_id"])
    vehicle = db.session.get(Vehicle, vehicle_id)
    
    if not vehicle or vehicle.company_id != user.company_id:
        flash("Access denied.", FlashCategory.DANGER)
        return redirect(url_for("core.dashboard"))
    
    if user.role not in [Role.COMPANY_ADMIN, Role.MANAGER]:
        flash("Insufficient permissions.", FlashCategory.DANGER)
        return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))
    
    vehicle.is_vor = not vehicle.is_vor
    db.session.commit()
    
    status_msg = "VOR" if vehicle.is_vor else "Operational"
    flash_category = FlashCategory.WARNING if vehicle.is_vor else FlashCategory.SUCCESS
    logger.info(f"Vehicle {vehicle.license_plate} VOR status toggled to {status_msg} by user {user.username}")
    flash(f"Vehicle marked as {status_msg}.", flash_category)
    
    return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))


@logbook_bp.route("/vehicle/<int:vehicle_id>/genrun", methods=["POST"])
@login_required
def perform_gen_run(vehicle_id):
    """Record a generator run for a vehicle"""
    user = db.session.get(User, session["user_id"])
    vehicle = Vehicle.query.filter_by(id=vehicle_id, company_id=user.company_id).first()
    
    if not vehicle:
        flash("Vehicle not found or access denied.", FlashCategory.DANGER)
        return redirect(url_for("core.dashboard"))
    
    # Create a new GenRun record
    genrun = GenRun(
        vehicle_id=vehicle.id,
        performed_by_id=user.id,
        performed_at=datetime.now(SGT)
    )
    
    db.session.add(genrun)
    db.session.commit()
    
    logger.info(f"Gen Run recorded for vehicle {vehicle.license_plate} by user {user.username}")
    flash("Gen Run recorded successfully.", FlashCategory.SUCCESS)
    return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))


@logbook_bp.route("/logbook/<license_plate>", methods=["GET", "POST"])
@login_required
def logbook_entry(license_plate):
    """View and create logbook entries for a vehicle"""
    current_user = db.session.get(User, session['user_id'])
    vehicle = Vehicle.query.filter_by(license_plate=license_plate).first_or_404()
    
    def get_view_data():
        """Helper to gather data for the page view"""
        target_name = ""
        source_name = ""
        
        if request.args.get('handover_to'):
            target_unit = db.session.get(Unit, request.args.get('handover_to'))
            if target_unit:
                target_name = target_unit.name
        
        if request.args.get('takeover_from'):
            source_unit = db.session.get(Unit, request.args.get('takeover_from'))
            if source_unit:
                source_name = source_unit.name
        
        # Determine which company's stores to show
        store_company_id = current_user.company_id if request.args.get('takeover_from') else vehicle.company_id
        stores = Store.query.filter_by(company_id=store_company_id).all()
        
        # Get logbook history
        history = Logbook.query.filter_by(vehicle_id=vehicle.id).order_by(Logbook.date.desc(), Logbook.id.desc()).all()
        last_entry = history[0] if history else None
        
        return target_name, source_name, stores, history, last_entry
    
    if request.method == 'POST':
        date_str = request.form.get('date')
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now(SGT).date()
        
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        error_msg = None
        
        if start_time and end_time:
            try:
                dt_start = to_time(start_time)
                dt_end = to_time(end_time)
                
                if dt_start and dt_end:
                    duration_minutes = (dt_end - dt_start).total_seconds() / 60
                    run_time = int(request.form.get('moving_time') or 0) + int(request.form.get('stationary_time') or 0)
                    
                    if duration_minutes < run_time:
                        error_msg = f"Error: Total time ({int(duration_minutes)}m) < required run time ({run_time}m)."
                    else:
                        # Check for time conflicts with existing entries
                        for existing in Logbook.query.filter_by(vehicle_id=vehicle.id, date=entry_date).all():
                            if existing.start_time and existing.end_time:
                                ex_start = to_time(existing.start_time)
                                ex_end = to_time(existing.end_time)
                                if ex_start and ex_end:
                                    if (dt_start < ex_end) and (dt_end > ex_start):
                                        error_msg = f"Time Conflict: Overlaps with {existing.start_time}-{existing.end_time}."
                                        break
            except ValueError:
                error_msg = "Invalid time format. Please use HHMM."
        
        if error_msg:
            flash(error_msg, FlashCategory.DANGER)
            target_name, source_name, display_stores, logbook_entries, last_entry = get_view_data()
            return render_template(
                'logbook.html',
                vehicle=vehicle,
                logbook=logbook_entries,
                user=current_user,
                stores=display_stores,
                target_name=target_name,
                source_name=source_name,
                username=current_user.username,
                prev_meter=last_entry.meter_reading if last_entry else 0,
                prev_poso=last_entry.poso if last_entry else 0,
                today=datetime.now(SGT).strftime('%Y-%m-%d')
            )
        
        # Create new logbook entry
        def to_db_val(val):
            return None if val in [None, '', '-', 'NaN'] else val
        
        new_entry = Logbook(
            vehicle_id=vehicle.id,
            company_id=vehicle.company_id,
            location=to_db_val(request.form.get('location')),
            meter_reading=to_db_val(request.form.get('meter_reading')),
            poso=to_db_val(request.form.get('poso')),
            fuel_received=to_db_val(request.form.get('fuel_received')),
            fuel_type=to_db_val(request.form.get('fuel_type')),
            driver_name=to_db_val(request.form.get('driver_name')),
            accompanying_name=to_db_val(request.form.get('accompanying_name')),
            start_time=to_db_val(start_time),
            end_time=to_db_val(end_time),
            action_type=to_db_val(request.form.get('action_type')),
            moving_time=to_db_val(request.form.get('moving_time')),
            stationary_time=to_db_val(request.form.get('stationary_time')),
            date=entry_date
        )
        
        db.session.add(new_entry)
        db.session.commit()
        logger.info(f"Logbook entry created for vehicle {vehicle.license_plate} by user {current_user.username}")
        flash("Logbook entry created successfully.", FlashCategory.SUCCESS)
        return redirect(url_for("logbook.logbook_entry", license_plate=vehicle.license_plate))
    
    # GET request - display the logbook form
    target_name, source_name, stores, logbook_entries, last_entry = get_view_data()
    
    return render_template(
        'logbook.html',
        vehicle=vehicle,
        logbook=logbook_entries,
        user=current_user,
        stores=stores,
        target_name=target_name,
        source_name=source_name,
        username=current_user.username,
        prev_meter=last_entry.meter_reading if last_entry else 0,
        prev_poso=last_entry.poso if last_entry else 0,
        today=datetime.now(SGT).strftime('%Y-%m-%d')
    )


# Alias for templates that use 'logbook' instead of 'logbook.logbook_entry'
@logbook_bp.route("/logbook_alias/<license_plate>")
@login_required
def logbook(license_plate):
    """Alias endpoint for templates using url_for('logbook', ...)"""
    return redirect(url_for("logbook.logbook_entry", license_plate=license_plate))


@logbook_bp.route("/api/vehicle/<int:vehicle_id>/last_values")
@login_required
def vehicle_last_values(vehicle_id):
    """API endpoint to get last valid logbook values for a vehicle"""
    engine_hours = get_last_valid_logbook_value(vehicle_id, "stationary_time")
    stationary_time = get_last_valid_logbook_value(vehicle_id, "stationary_time")
    
    logger.info(f"Last values requested for vehicle {vehicle_id} by user {session.get('user_id')}")
    
    return jsonify({
        "engine_hours": engine_hours,
        "stationary_time": stationary_time
    })


@logbook_bp.route("/delete_logbook_entry/<int:entry_id>", methods=["POST"])
@login_required
@role_required(Role.COMPANY_ADMIN, Role.MANAGER)
def delete_logbook_entry(entry_id):
    """Delete a logbook entry (admin only)"""
    current_user = db.session.get(User, session["user_id"])
    entry = Logbook.query.get_or_404(entry_id)
    license_plate = entry.vehicle.license_plate
    
    try:
        db.session.delete(entry)
        db.session.commit()
        logger.info(f"Logbook entry {entry_id} deleted by user {current_user.username}")
        flash("Logbook entry deleted.", FlashCategory.SUCCESS)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete logbook entry {entry_id}: {str(e)}", exc_info=True)
        flash("Failed to delete logbook entry.", FlashCategory.ERROR)
    
    return redirect(url_for("logbook.logbook_entry", license_plate=license_plate))
