from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from app.models import db, User, VehicleType, Store, Vehicle, SGT
from app.decorators.auth import login_required
from app.config import Role, FlashCategory
import logging

logger = logging.getLogger(__name__)

core_bp = Blueprint("core", __name__)


@core_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """
    Main dashboard for company users.
    Shows vehicles organized by type and store, plus incoming/outgoing transfers.
    """
    user = db.session.get(User, session.get("user_id"))
    
    # Only allow company-level users (not superadmin or unit_admin)
    if not user or user.role in [Role.SUPERADMIN, Role.UNIT_ADMIN]:
        flash("Access denied. Company users only.", FlashCategory.DANGER)
        session.clear()
        return redirect(url_for("auth.login"))

    # Get vehicle types for the user's company
    types = VehicleType.query.filter_by(company_id=user.company_id).order_by(VehicleType.name).all()
    
    # Get active type from query param or default to first
    active_type_id = request.args.get("type_id", type=int)
    if not active_type_id and types:
        active_type_id = types[0].id

    # Get stores for active vehicle type
    stores = []
    if active_type_id:
        stores = Store.query.filter_by(
            company_id=user.company_id, 
            vehicle_type_id=active_type_id
        ).order_by(Store.position).all()
        
        # Sort vehicles within each store
        for s in stores:
            s.display_vehicles = sorted(
                s.vehicles, 
                key=lambda v: (v.position is None, v.position, v.id)
            )

    # Get transfer vehicles
    incoming = Vehicle.query.filter_by(
        target_company_id=user.company_id, 
        status='in_transit'
    ).all()
    
    outgoing = Vehicle.query.filter_by(
        previous_company_id=user.company_id, 
        status='in_transit'
    ).all()

    logger.info(f"Dashboard accessed by user {user.username} for company {user.company_id}")

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