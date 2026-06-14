from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime
from app.models import db, User, VehicleType, Store, Vehicle, SGT

core_bp = Blueprint("core", __name__)

@core_bp.route("/dashboard", methods=["GET"])
def dashboard():
    user = db.session.get(User, session.get("user_id"))
    if not user or user.role in ["superadmin", "unit_admin"]:
        session.clear()
        return redirect(url_for("auth.login"))

    types = VehicleType.query.filter_by(company_id=user.company_id).order_by(VehicleType.name).all()
    active_type_id = request.args.get("type_id", type=int)
    if not active_type_id and types: active_type_id = types[0].id

    stores = []
    if active_type_id:
        stores = Store.query.filter_by(company_id=user.company_id, vehicle_type_id=active_type_id).order_by(Store.position).all()
        for s in stores:
            s.display_vehicles = sorted(s.vehicles, key=lambda v: (v.position is None, v.position, v.id))

    incoming = Vehicle.query.filter_by(target_company_id=user.company_id, status='in_transit').all()
    outgoing = Vehicle.query.filter_by(previous_company_id=user.company_id, status='in_transit').all()

    return render_template(
        "dashboard.html",
        user=user,
        stores=stores,
        types=types,
        active_type_id=active_type_id,
        incoming=incoming,
        outgoing=outgoing,
        now=datetime.now(SGT).replace(tzinfo=None)
    )