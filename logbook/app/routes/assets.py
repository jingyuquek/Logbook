from flask import Blueprint, request, redirect, url_for, flash, session
import re
from datetime import datetime
from app.models import db, User, Vehicle, Store, VehicleType, FireExtinguisher, VehicleTypeExtinguisher

assets_bp = Blueprint("assets", __name__)

@assets_bp.route("/add_vehicle", methods=["POST"])
def add_vehicle():
    user = db.session.get(User, session.get("user_id"))
    if not user or user.role not in ["admin", "manager"]: return redirect(url_for("auth.login"))

    plate = request.form["license_plate"].strip()
    store_id = int(request.form["store_id"])
    type_id = int(request.form["vehicle_type_id"])

    if not re.match("^[A-Za-z0-9]+$", plate):
        flash("Invalid License Plate characters.", "danger")
        return redirect(url_for('core.dashboard', type_id=type_id))

    vehicle = Vehicle.query.filter_by(license_plate=plate).first()
    if not vehicle:
        vehicle = Vehicle(license_plate=plate, store_id=store_id, company_id=user.company_id, vehicle_type_id=type_id)
        db.session.add(vehicle)
        db.session.flush()
        
        # Pull template requirements directly to assign asset properties
        v_type = db.session.get(VehicleType, type_id)
        if v_type:
            for template in v_type.default_extinguishers:
                db.session.add(FireExtinguisher(vehicle=vehicle, name=template.name, expiry_date=None))
        db.session.commit()
        flash("Vehicle built with tracking parameters.", "success")
    return redirect(url_for("core.dashboard", type_id=type_id))


@assets_bp.route("/move_vehicle", methods=["POST"])
def move_vehicle():
    if "user_id" not in session: return {"error": "Unauthorized"}, 401
    data = request.get_json() or {}
    vehicle = db.session.get(Vehicle, data.get("vehicle_id"))
    store = db.session.get(Store, data.get("store_id"))
    user = db.session.get(User, session["user_id"])

    if vehicle and store and vehicle.company_id == user.company_id and store.company_id == user.company_id:
        vehicle.store = store
        vehicle.vehicle_type_id = store.vehicle_type_id
        db.session.commit()
        return {"success": True}, 200
    return {"error": "Permit Denied"}, 403


@assets_bp.route("/reorder_vehicles", methods=["POST"])
def reorder_vehicles():
    if "user_id" not in session: return {"status": "unauthorized"}, 401
    data = request.json or {}
    for index, v_id in enumerate(data.get("order", [])):
        vehicle = db.session.get(Vehicle, v_id)
        if vehicle: vehicle.position = index
    db.session.commit()
    return {"status": "success"}, 200


@assets_bp.route("/add_store", methods=["POST"])
def add_store():
    user = db.session.get(User, session.get("user_id"))
    if not user or user.role not in ["admin", "manager"]: return redirect(url_for("auth.login"))

    name = request.form.get("name", "").strip()
    type_id = request.form.get("vehicle_type_id", type=int)
    
    if name and type_id:
        pos_count = Store.query.filter_by(company_id=user.company_id, vehicle_type_id=type_id).count()
        db.session.add(Store(name=name, company_id=user.company_id, vehicle_type_id=type_id, position=pos_count))
        db.session.commit()
        flash("Store created.", "success")
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
    return redirect(url_for("core.dashboard"))  # Or view_vehicle if you prefer