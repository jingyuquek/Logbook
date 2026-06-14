from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from sqlalchemy import and_, cast, String
from app.models import db, User, Vehicle, Task, Logbook, Company, SGT

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/company_list")
def company_list():
    """Display company personnel list with role-based sorting and vehicle assignments"""
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("auth.login"))
    
    current_user = db.session.get(User, session["user_id"])
    
    if not current_user.company_id:
        flash("You are not assigned to a company.", "danger")
        return redirect(url_for("core.dashboard"))
    
    company = db.session.get(Company, current_user.company_id)
    
    # Role priority for sorting: Admin → Manager → User
    role_priority = {"admin": 1, "manager": 2, "user": 3}
    
    # Get all approved users in the company
    users = User.query.filter_by(company_id=company.id, is_approved=True).all()
    
    # Sort by role priority then username
    users = sorted(users, key=lambda u: (role_priority.get(u.role, 99), u.username.lower()))
    
    # Fetch all vehicles belonging to this company
    vehicles = Vehicle.query.filter_by(company_id=company.id).order_by(Vehicle.license_plate.asc()).all()
    
    return render_template(
        "company_list.html",
        user=current_user,
        company=company,
        users=users,
        vehicles=vehicles
    )


@tasks_bp.route("/assign-task", methods=["POST"])
def assign_task():
    """Assign a task to a user (admin only)"""
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("auth.login"))
    
    current_user = db.session.get(User, session["user_id"])
    
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("core.dashboard"))
    
    target_user_id = request.form.get("user_id")
    task_type = request.form.get("task_type")
    vehicle_ids = request.form.getlist("vehicle_ids")
    
    if not all([target_user_id, task_type, vehicle_ids]):
        flash("All fields and at least one vehicle are required.", "warning")
        return redirect(url_for("tasks.company_list"))
    
    target_user = User.query.filter_by(
        id=target_user_id,
        company_id=current_user.company_id,
        is_approved=True
    ).first()
    
    if not target_user:
        flash("Invalid user.", "danger")
        return redirect(url_for("tasks.company_list"))
    
    assigned_count = 0
    for v_id in vehicle_ids:
        vehicle = Vehicle.query.filter_by(id=v_id, company_id=current_user.company_id).first()
        
        if vehicle:
            task = Task(
                title=task_type,
                assigned_to_id=target_user.id,
                assigned_by_id=current_user.id,
                vehicle_id=vehicle.id,
                created_at=datetime.now(SGT),
                is_completed=False
            )
            db.session.add(task)
            assigned_count += 1
    
    db.session.commit()
    flash(f"Task '{task_type}' assigned to {target_user.username} for {assigned_count} vehicle(s).", "success")
    return redirect(url_for("tasks.company_list"))


@tasks_bp.route("/my_tasks")
def my_tasks():
    """Display pending tasks assigned to the current user"""
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("auth.login"))
    
    current_user = db.session.get(User, session["user_id"])
    
    # Fetch ONLY pending tasks for this user
    pending_tasks = Task.query.filter_by(
        assigned_to_id=current_user.id,
        is_completed=False
    ).order_by(Task.created_at.desc()).all()
    
    # Determine vehicle for a top-right button
    vehicle = next((task.vehicle for task in pending_tasks if task.vehicle), None)
    
    return render_template(
        "my_tasks.html",
        user=current_user,
        tasks=pending_tasks,
        vehicle=vehicle
    )


@tasks_bp.route("/completed_tasks")
def completed_tasks():
    """Display completed tasks (logbook entries) for the current user with pagination"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    current_user = db.session.get(User, session["user_id"])
    page = request.args.get('page', 1, type=int)
    
    # Query logbook entries where current user was the driver
    # Join with Vehicle to ensure company match
    pagination = db.session.query(Logbook, Vehicle)\
        .join(Vehicle, Logbook.vehicle_id == Vehicle.id)\
        .filter(Logbook.driver_name == current_user.username)\
        .filter(Vehicle.company_id == current_user.company_id)\
        .order_by(Logbook.date.desc(), Logbook.start_time.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    return render_template(
        'completed_tasks.html',
        pagination=pagination,
        entries=pagination.items,
        user=current_user
    )


@tasks_bp.route("/company_tasks")
def company_tasks():
    """Display all company logbook entries with filtering and pagination (for admins)"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    page = request.args.get('page', 1, type=int)
    user = db.session.get(User, session['user_id'])
    
    # Get filter parameters
    f_date = request.args.get('f_date', '').strip()
    f_loc = request.args.get('f_loc', '').strip()
    f_plate = request.args.get('f_plate', '').strip()
    f_task = request.args.get('f_task', '').strip()
    f_driver = request.args.get('f_driver', '').strip()
    
    # Build base query
    query = db.session.query(Logbook, Vehicle).join(Vehicle, Logbook.vehicle_id == Vehicle.id).filter(Logbook.company_id == user.company_id)
    
    # Apply filters
    conditions = []
    if f_date:
        conditions.append(cast(Logbook.date, String).ilike(f"%{f_date}%"))
    if f_loc:
        conditions.append(Logbook.location.ilike(f"%{f_loc}%"))
    if f_plate:
        conditions.append(Vehicle.license_plate.ilike(f"%{f_plate}%"))
    if f_task:
        conditions.append(Logbook.action_type.ilike(f"%{f_task}%"))
    if f_driver:
        conditions.append(Logbook.driver_name.ilike(f"%{f_driver}%"))
    
    if conditions:
        query = query.filter(and_(*conditions))
    
    pagination = query.order_by(Logbook.date.desc(), Logbook.start_time.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template(
        'company_tasks.html',
        pagination=pagination,
        entries=pagination.items,
        user=user
    )


@tasks_bp.route("/complete_task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    """Mark a task as completed after verifying logbook entry exists"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    current_user = db.session.get(User, session["user_id"])
    task = Task.query.get_or_404(task_id)
    
    # Singapore Time Logic
    now_sg = datetime.now(SGT)
    today_sg_date = now_sg.date()
    
    # Get clean version of the task title for matching
    search_purpose = task.title.strip().upper()
    
    # Logbook Verification: Check for Same Vehicle + Same Purpose + Same Date
    log_entry = Logbook.query.filter(
        Logbook.vehicle_id == task.vehicle_id,
        Logbook.action_type == search_purpose,
        Logbook.date == today_sg_date
    ).first()
    
    if not log_entry:
        flash(
            f"No entry found for Vehicle {task.vehicle.license_plate} with Purpose '{search_purpose}' on {today_sg_date}.",
            "warning"
        )
        return redirect(url_for('tasks.my_tasks'))
    
    # Success - mark task as completed
    task.is_completed = True
    db.session.commit()
    
    flash(f"Task '{task.title}' verified and completed!", "success")
    return redirect(url_for('tasks.my_tasks'))


@tasks_bp.route("/delete_task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    """Delete a task (admin only)"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    current_user = db.session.get(User, session["user_id"])
    
    if current_user.role != "admin":
        flash("Unauthorized.", "danger")
        return redirect(url_for("core.dashboard"))
    
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    
    flash("Task removed from company history.", "success")
    return redirect(url_for('tasks.company_tasks'))
