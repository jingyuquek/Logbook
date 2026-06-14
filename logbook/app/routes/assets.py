from flask import Blueprint, request, redirect, url_for, flash, session
import re
from datetime import datetime
from app.models import db, User, Vehicle, Store, VehicleType, FireExtinguisher, VehicleTypeExtinguisher

assets_bp = Blueprint("assets", __name__)


@assets_bp.route("/add_vehicle", methods=["POST"])
def add_vehicle():
    user = db.session.get(User, session.get("user_id"))
    if not user or user.role not in ["admin", "manager"]:
        return redirect(url_for("auth.login"))

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

        v_type = db.session.get(VehicleType, type_id)
        if v_type:
            for template in v_type.default_extinguishers:
                db.session.add(FireExtinguisher(vehicle=vehicle, name=template.name, expiry_date=None))
        db.session.commit()
        flash("Vehicle built with tracking parameters.", "success")
    return redirect(url_for("core.dashboard", type_id=type_id))


@assets_bp.route("/move_vehicle", methods=["POST"])
def move_vehicle():
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 401
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
    if "user_id" not in session:
        return {"status": "unauthorized"}, 401
    data = request.json or {}
    for index, v_id in enumerate(data.get("order", [])):
        vehicle = db.session.get(Vehicle, v_id)
        if vehicle:
            vehicle.position = index
    db.session.commit()
    return {"status": "success"}, 200


@assets_bp.route("/add_store", methods=["POST"])
def add_store():
    user = db.session.get(User, session.get("user_id"))
    if not user or user.role not in ["admin", "manager"]:
        return redirect(url_for("auth.login"))

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
def move_store(store_id, direction):
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        return redirect(url_for("core.dashboard"))
    store = Store.query.filter_by(id=store_id, company_id=user.company_id).first()
    if not store:
        return redirect(url_for("core.dashboard"))
    
    if direction == "up":
        swap = Store.query.filter(
            Store.company_id == user.company_id,
            Store.vehicle_type_id == store.vehicle_type_id,
            Store.position < store.position
        ).order_by(Store.position.desc()).first()
    else:
        swap = Store.query.filter(
            Store.company_id == user.company_id,
            Store.vehicle_type_id == store.vehicle_type_id,
            Store.position > store.position
        ).order_by(Store.position.asc()).first()
    
    if swap:
        store.position, swap.position = swap.position, store.position
        db.session.commit()
    return redirect(url_for("core.dashboard", type_id=store.vehicle_type_id))


@assets_bp.route("/remove_vehicle", methods=["POST"])
def remove_vehicle():
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        return redirect(url_for("core.dashboard"))
    vehicle = db.session.get(Vehicle, request.form["vehicle_id"])
    if vehicle and vehicle.company_id == user.company_id:
        saved_type_id = vehicle.vehicle_type_id
        vehicle.company_id = None
        vehicle.store_id = None
        db.session.commit()
        flash("Vehicle removed.", "success")
        return redirect(url_for("core.dashboard", type_id=saved_type_id))
    return redirect(url_for("core.dashboard"))


@assets_bp.route("/remove_store", methods=["POST"])
def remove_store():
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        return redirect(url_for("core.dashboard"))
    store = Store.query.filter_by(id=request.form["store_id"], company_id=user.company_id).first()
    if store:
        saved_type_id = store.vehicle_type_id
        db.session.delete(store)
        db.session.commit()
        flash("Store removed.", "success")
        return redirect(url_for("core.dashboard", type_id=saved_type_id))
    return redirect(url_for("core.dashboard"))


@assets_bp.route("/edit_store/<int:store_id>", methods=["POST"])
def edit_store(store_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))
    store = Store.query.filter_by(id=store_id, company_id=user.company_id).first_or_404()
    new_name = request.form.get("name", "").strip()
    if not new_name:
        flash("Store name cannot be empty.", "danger")
        return redirect(url_for("core.dashboard", type_id=store.vehicle_type_id))
    existing = Store.query.filter_by(name=new_name, company_id=user.company_id, vehicle_type_id=store.vehicle_type_id).first()
    if existing and existing.id != store.id:
        flash("Another store with that name already exists in this layout view.", "warning")
        return redirect(url_for("core.dashboard", type_id=store.vehicle_type_id))
    store.name = new_name
    db.session.commit()
    flash("Store name updated.", "success")
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
