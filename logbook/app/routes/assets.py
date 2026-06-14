from flask import Blueprint, request, redirect, url_for, flash, session, jsonify
import re
from datetime import datetime
from app.models import db, User, Vehicle, Store, VehicleType, FireExtinguisher, VehicleTypeExtinguisher
from app.decorators.auth import login_required, role_required
from app.services import VehicleService, StoreService
from app.config import Role, FlashCategory, VehicleStatus
import logging

logger = logging.getLogger(__name__)

assets_bp = Blueprint("assets", __name__)


@assets_bp.route("/add_vehicle", methods=["POST"])
@login_required
@role_required(Role.COMPANY_ADMIN, Role.MANAGER)
def add_vehicle():
    """
    Add a new vehicle to the fleet.
    Validates license plate format and creates associated fire extinguishers.
    """
    user = db.session.get(User, session.get("user_id"))
    
    plate = request.form.get("license_plate", "").strip()
    store_id = request.form.get("store_id", type=int)
    type_id = request.form.get("vehicle_type_id", type=int)
    
    # Validate required fields
    if not plate or not store_id or not type_id:
        flash("All fields are required.", FlashCategory.DANGER)
        return redirect(url_for('core.dashboard', type_id=type_id))

    # Validate license plate format (alphanumeric only)
    if not re.match("^[A-Za-z0-9]+$", plate):
        flash("Invalid License Plate characters. Only alphanumeric characters allowed.", FlashCategory.DANGER)
        return redirect(url_for('core.dashboard', type_id=type_id))

    vehicle, error = VehicleService.create_vehicle(
        license_plate=plate,
        store_id=store_id,
        company_id=user.company_id,
        vehicle_type_id=type_id
    )
    
    if vehicle:
        logger.info(f"Vehicle {plate} added by user {user.username}")
        flash("Vehicle built with tracking parameters.", FlashCategory.SUCCESS)
    else:
        logger.error(f"Failed to add vehicle {plate}: {error}")
        flash(error or "Failed to add vehicle. Please try again.", FlashCategory.ERROR)
        
    return redirect(url_for("core.dashboard", type_id=type_id))


@assets_bp.route("/move_vehicle", methods=["POST"])
@login_required
def move_vehicle():
    """
    Move a vehicle to a different store.
    JSON API endpoint for drag-and-drop functionality.
    """
    data = request.get_json() or {}
    vehicle_id = data.get("vehicle_id")
    store_id = data.get("store_id")
    
    if not vehicle_id or not store_id:
        return jsonify({"error": "Missing vehicle_id or store_id"}), 400
    
    user = db.session.get(User, session["user_id"])
    
    success, error = VehicleService.move_vehicle(vehicle_id, store_id, user.company_id)
    
    if success:
        logger.info(f"Vehicle moved to store {store_id}")
        return jsonify({"success": True}), 200
    else:
        logger.warning(f"Failed to move vehicle: {error}")
        if "Permission" in error or "not found" in error:
            return jsonify({"error": error}), 403 if "Permission" in error else 404
        return jsonify({"error": "Failed to move vehicle"}), 500


@assets_bp.route("/reorder_vehicles", methods=["POST"])
@login_required
def reorder_vehicles():
    """
    Reorder vehicles within a store.
    JSON API endpoint for position updates.
    """
    data = request.json or {}
    order = data.get("order", [])
    
    if not order:
        return jsonify({"status": "error", "message": "No order data provided"}), 400
    
    user = db.session.get(User, session["user_id"])
    
    success, error = VehicleService.reorder_vehicles(order, user.company_id)
    
    if success:
        return jsonify({"status": "success"}), 200
    else:
        logger.error(f"Failed to reorder vehicles: {error}")
        return jsonify({"status": "error", "message": error}), 500


@assets_bp.route("/add_store", methods=["POST"])
@login_required
@role_required(Role.COMPANY_ADMIN, Role.MANAGER)
def add_store():
    """Add a new store for a specific vehicle type."""
    user = db.session.get(User, session.get("user_id"))

    name = request.form.get("name", "").strip()
    type_id = request.form.get("vehicle_type_id", type=int)

    if not name or not type_id:
        flash("Store name and vehicle type are required.", FlashCategory.DANGER)
        return redirect(url_for("core.dashboard", type_id=type_id))

    store, error = StoreService.create_store(name, user.company_id, type_id)
    
    if store:
        logger.info(f"Store '{name}' created by user {user.username}")
        flash("Store created.", FlashCategory.SUCCESS)
    else:
        logger.error(f"Failed to create store: {error}")
        flash("Failed to create store.", FlashCategory.ERROR)
        
    return redirect(url_for("core.dashboard", type_id=type_id))


@assets_bp.route("/vehicle/<int:vehicle_id>/add_extinguisher", methods=["POST"])
def add_extinguisher(vehicle_id):
    user = db.session.get(User, session.get("user_id"))
    vehicle = Vehicle.query.filter_by(id=vehicle_id, company_id=user.company_id).first_or_404()
    name = request.form.get("name", "").strip()
    expiry_str = request.form.get("expiry_date", "")

    if name and expiry_str:
        try:
            exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            db.session.add(FireExtinguisher(vehicle=vehicle, name=name, expiry_date=exp))
            db.session.commit()
            flash("Extinguisher linked safely.", "success")
        except ValueError:
            flash("Invalid date structure.", "danger")
    return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))


@assets_bp.route("/extinguisher/<int:extinguisher_id>/delete", methods=["POST"])
def delete_extinguisher(extinguisher_id):
    if 'user_id' not in session:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, session['user_id'])
    fe = FireExtinguisher.query.get_or_404(extinguisher_id)
    vehicle = Vehicle.query.filter_by(id=fe.vehicle_id, company_id=user.company_id).first_or_404()

    db.session.delete(fe)
    db.session.commit()
    flash("Fire extinguisher removed.", "success")
    return redirect(url_for("logbook.view_vehicle", license_plate=vehicle.license_plate))


@assets_bp.route("/add_type_extinguisher", methods=["POST"])
def add_type_extinguisher():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        return redirect(url_for("core.dashboard"))

    type_id = request.form.get("vehicle_type_id")
    name = request.form.get("name", "").strip()

    if name and type_id:
        vte = VehicleTypeExtinguisher(vehicle_type_id=int(type_id), name=name)
        db.session.add(vte)
        db.session.commit()
        flash(f"Added default requirement: '{name}'", "success")
    return redirect(url_for("core.dashboard", type_id=type_id))


@assets_bp.route("/delete_type_extinguisher/<int:ext_id>", methods=["POST"])
def delete_type_extinguisher(ext_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        return redirect(url_for("core.dashboard"))

    vte = VehicleTypeExtinguisher.query.get_or_404(ext_id)
    type_id = vte.vehicle_type_id
    db.session.delete(vte)
    db.session.commit()
    flash("Default extinguisher requirement removed.", "success")
    return redirect(url_for("core.dashboard", type_id=type_id))


@assets_bp.route("/add_vehicle_type", methods=["POST"])
def add_vehicle_type():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))

    name = request.form.get("name", "").strip()
    if not name:
        flash("Type name cannot be empty.", "danger")
        return redirect(url_for("core.dashboard"))

    new_type = VehicleType(name=name, company_id=user.company_id)
    db.session.add(new_type)
    db.session.commit()

    flash(f"Vehicle type '{name}' created successfully.", "success")
    return redirect(url_for("core.dashboard", type_id=new_type.id))


@assets_bp.route("/remove_vehicle_type", methods=["POST"])
def remove_vehicle_type():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        return redirect(url_for("core.dashboard"))

    type_id = request.form.get("vehicle_type_id", type=int)
    vt = VehicleType.query.filter_by(id=type_id, company_id=user.company_id).first()

    if vt:
        name = vt.name
        db.session.delete(vt)
        db.session.commit()
        flash(f"Vehicle type '{name}' and all its associated stores/vehicles have been removed.", "success")

    return redirect(url_for("core.dashboard"))


@assets_bp.route("/move_store/<int:store_id>/<direction>")
@login_required
@role_required(Role.COMPANY_ADMIN, Role.MANAGER)
def move_store(store_id, direction):
    """Move store position up or down."""
    user = db.session.get(User, session["user_id"])
    
    success, error = StoreService.move_store(store_id, direction, user.company_id)
    
    if success:
        flash(f"Store moved {direction}.", FlashCategory.SUCCESS)
    else:
        flash(error, FlashCategory.WARNING)
    
    store = Store.query.get(store_id)
    return redirect(url_for("core.dashboard", type_id=store.vehicle_type_id if store else None))


@assets_bp.route("/remove_vehicle", methods=["POST"])
@login_required
@role_required(Role.COMPANY_ADMIN, Role.MANAGER)
def remove_vehicle():
    """Remove a vehicle from the fleet."""
    user = db.session.get(User, session["user_id"])
    vehicle = db.session.get(Vehicle, request.form["vehicle_id"])
    
    if vehicle and vehicle.company_id == user.company_id:
        saved_type_id = vehicle.vehicle_type_id
        vehicle.company_id = None
        vehicle.store_id = None
        db.session.commit()
        flash("Vehicle removed.", FlashCategory.SUCCESS)
        return redirect(url_for("core.dashboard", type_id=saved_type_id))
    return redirect(url_for("core.dashboard"))


@assets_bp.route("/remove_store", methods=["POST"])
@login_required
@role_required(Role.COMPANY_ADMIN, Role.MANAGER)
def remove_store():
    """Remove a store."""
    user = db.session.get(User, session["user_id"])
    store = Store.query.filter_by(id=request.form["store_id"], company_id=user.company_id).first()
    
    if store:
        saved_type_id = store.vehicle_type_id
        success, error = StoreService.delete_store(store.id, user.company_id)
        if success:
            flash("Store removed.", FlashCategory.SUCCESS)
        else:
            flash(error, FlashCategory.ERROR)
        return redirect(url_for("core.dashboard", type_id=saved_type_id))
    return redirect(url_for("core.dashboard"))


@assets_bp.route("/edit_store/<int:store_id>", methods=["POST"])
@login_required
@role_required(Role.COMPANY_ADMIN, Role.MANAGER)
def edit_store(store_id):
    """Edit store name."""
    user = db.session.get(User, session["user_id"])
    store = Store.query.filter_by(id=store_id, company_id=user.company_id).first_or_404()
    new_name = request.form.get("name", "").strip()
    
    if not new_name:
        flash("Store name cannot be empty.", FlashCategory.DANGER)
        return redirect(url_for("core.dashboard", type_id=store.vehicle_type_id))
    
    success, error = StoreService.update_store(store_id, new_name, user.company_id)
    
    if success:
        flash("Store name updated.", FlashCategory.SUCCESS)
    else:
        flash(error, FlashCategory.WARNING)
    
    return redirect(url_for("core.dashboard", type_id=store.vehicle_type_id))


@assets_bp.route('/move_vehicle_store', methods=['POST'])
def move_vehicle_store():
    user = db.session.get(User, session.get('user_id'))
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.login'))

    v_id = request.form.get('vehicle_id')
    new_s_id = request.form.get('new_store_id')
    vehicle = Vehicle.query.get(v_id)

    if vehicle and vehicle.company_id == user.company_id:
        vehicle.store_id = new_s_id
        vehicle.position = Vehicle.query.filter_by(store_id=new_s_id).count()
        db.session.commit()
    return redirect(url_for('core.dashboard'))
