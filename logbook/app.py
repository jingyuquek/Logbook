import re
import random
from flask import Flask, render_template, request, redirect, url_for, flash, session, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone, date

SGT = timezone(timedelta(hours=8))

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, cast, String

db = SQLAlchemy()




# ----------------------
# Models
# ----------------------

class Unit(db.Model):
    __tablename__ = "unit"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    passcode_hash = db.Column(db.String(255), nullable=False)

    companies = db.relationship("Company", backref="unit", lazy=True)


class Company(db.Model):
    __tablename__ = "company"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    passcode_hash = db.Column(db.String(255), nullable=False)

    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id"), nullable=False)

    users = db.relationship("User", backref="company", lazy=True)
    stores = db.relationship("Store", backref="company", lazy=True)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(30), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)

    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id"), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True)

    unit = db.relationship('Unit', backref='users_in_unit')


class VehicleType(db.Model):
    __tablename__ = "vehicle_type"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)

    company = db.relationship("Company", backref="vehicle_types")
    vehicles = db.relationship("Vehicle", back_populates="vehicle_type", cascade="all, delete-orphan")
    
    # ADDED LINE: Link to the new dynamic template name rows
    default_extinguishers = db.relationship("VehicleTypeExtinguisher", backref="vehicle_type", cascade="all, delete-orphan")


class FireExtinguisher(db.Model):
    __tablename__ = "fire_extinguisher"
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)

    vehicle = db.relationship("Vehicle", back_populates="extinguishers")

    @property
    def is_valid(self):
        today = datetime.now(SGT).replace(tzinfo=None).date()
        return self.expiry_date and self.expiry_date >= today


class VehicleTypeExtinguisher(db.Model):
    __tablename__ = "vehicle_type_extinguisher"
    id = db.Column(db.Integer, primary_key=True)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey("vehicle_type.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)


class Vehicle(db.Model):
    __tablename__ = "vehicle"
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("store.id"), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey("vehicle_type.id"), nullable=False)
    position = db.Column(db.Integer, nullable=True)
    pol_level = db.Column(db.Integer, default=100, nullable=False)
    
    is_vor = db.Column(db.Boolean, default=False)
    shutter_number = db.Column(db.String(5), nullable=True)

    status = db.Column(db.String(20), default='active', nullable=False)
    target_company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    previous_company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    previous_store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=True)

    # Relationships
    store = db.relationship("Store", back_populates="vehicles", foreign_keys=[store_id])
    previous_store = db.relationship("Store", foreign_keys=[previous_store_id])
    
    company = db.relationship('Company', foreign_keys=[company_id], backref='owned_vehicles')
    target_company = db.relationship('Company', foreign_keys=[target_company_id], backref='incoming_transfers')
    previous_company = db.relationship('Company', foreign_keys=[previous_company_id])

    vehicle_type = db.relationship("VehicleType", back_populates="vehicles")
    logbook_entries = db.relationship("Logbook", back_populates="vehicle", cascade="all, delete-orphan")
    faults = db.relationship("Fault", back_populates="vehicle")
    extinguishers = db.relationship("FireExtinguisher", back_populates="vehicle", cascade="all, delete-orphan")

    @property
    def genrun_valid(self):
        if not self.gen_runs: return False
        now_naive = datetime.now(SGT).replace(tzinfo=None)
        threshold = now_naive - timedelta(days=14)
        last_run = max(self.gen_runs, key=lambda gr: gr.performed_at)
        last_run_time = last_run.performed_at.replace(tzinfo=None) if last_run.performed_at.tzinfo else last_run.performed_at
        return last_run_time >= threshold


class Store(db.Model):
    __tablename__ = "store"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey("vehicle_type.id"), nullable=False)
    position = db.Column(db.Integer, default=0)

    vehicles = db.relationship("Vehicle", back_populates="store", cascade="all, delete-orphan", foreign_keys="[Vehicle.store_id]")


class GenRun(db.Model):
    __tablename__ = "gen_runs"

    id = db.Column(db.Integer, primary_key=True)

    vehicle_id = db.Column(
        db.Integer,
        db.ForeignKey("vehicle.id"),
        nullable=False
    )

    performed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    performed_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(SGT),
        nullable=False
    )

    vehicle = db.relationship("Vehicle", backref="gen_runs")
    performed_by = db.relationship("User")


class Logbook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    location = db.Column(db.String(50))
    meter_reading = db.Column(db.Integer)
    poso = db.Column(db.Float) # Now used for PMCS values (0.4/0.2)
    fuel_received = db.Column(db.Float)
    fuel_type = db.Column(db.String(50))
    driver_name = db.Column(db.String(100))
    accompanying_name = db.Column(db.String(100))
    start_time = db.Column(db.String(4))
    end_time = db.Column(db.String(4))
    action_type = db.Column(db.String(100))
    moving_time = db.Column(db.Float)   # Travelling Time
    stationary_time = db.Column(db.Float) # Stationary Running Time
    date = db.Column(db.Date) # Now manually filled

    vehicle = db.relationship("Vehicle", back_populates="logbook_entries")


class Fault(db.Model):
    __tablename__ = "fault"

    id = db.Column(db.Integer, primary_key=True)
    fault_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(20),
        default="Open",
        nullable=False
    )

    date_reported = db.Column(
        db.DateTime,
        default=lambda: datetime.now(SGT)
    )

    last_updated = db.Column(
        db.DateTime,
        default=lambda: datetime.now(SGT),
        onupdate=lambda: datetime.now(SGT)
    )

    vehicle_id = db.Column(
        db.Integer,
        db.ForeignKey("vehicle.id"),
        nullable=False
    )

    vehicle = db.relationship(
        "Vehicle",
        back_populates="faults"
    )


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=True)
    status = db.Column(db.String(50), default="pending", nullable=False)

    assigned_to_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    assigned_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(SGT),
        nullable=False
    )

    is_completed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    assigned_to = db.relationship(
        "User",
        foreign_keys=[assigned_to_id],
        backref="tasks"
    )

    assigned_by = db.relationship(
        "User",
        foreign_keys=[assigned_by_id]
    )

    vehicle = db.relationship("Vehicle")


class HandoverToken(db.Model):
    __tablename__ = "handover_token"
    id = db.Column(db.Integer, primary_key=True)
    token_string = db.Column(db.String(10), unique=True, nullable=False)
    
    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey("vehicle_type.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    vehicle_type = db.relationship("VehicleType", foreign_keys=[vehicle_type_id])

    @staticmethod
    def generate_unique_otp():
        import random
        for _ in range(100):
            otp = "".join([str(random.randint(0, 9)) for _ in range(10)])
            if not HandoverToken.query.filter_by(token_string=otp).first():
                return otp
        raise RuntimeError("Failed to generate a unique operational token.")

# ----------------------
# Create tables
# ----------------------
db.init_app(app)
# ----------------------
# Routes
# ----------------------
def get_sg_time():
    return datetime.now(SGT)

@app.route("/")
def start():
    return redirect(url_for('login'))

# region log in

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        # Fetch the user
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            
            # Superadmins bypass approval
            if user.role != "superadmin" and not user.is_approved:
                flash("Your account is pending approval. Please wait for an admin to approve.", "warning")
                return redirect(url_for("login"))

            # Login success: store session
            session["user_id"] = user.id
            session["role"] = user.role

            # Redirect based on role
            if user.role == "superadmin":
                return redirect(url_for("superadmin_dashboard"))
            elif user.role == "unit_admin":
                return redirect(url_for("unit_admin_dashboard"))  # you will need to create this route
            elif user.role == "admin":
                return redirect(url_for("dashboard"))  # create this route
            elif user.role in ["manager", "user"]:
                return redirect(url_for("dashboard"))  # same dashboard for managers/users
            else:
                flash("Unknown role. Contact system administrator.", "danger")
                return redirect(url_for("login"))

        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()
        unit_name = request.form.get("unit_name", "").strip()

        # --- Basic validation ---
        if not username or not password or not role or not unit_name:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        # --- Case-Insensitive Fetch Unit ---
        unit = Unit.query.filter(Unit.name.ilike(unit_name)).first()
        if not unit:
            flash("Selected unit / company does not exist.", "danger")
            return redirect(url_for("register"))

        # --- Duplicate username check ---
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))

        company_id = None
        is_approved = False   # 🔴 DEFAULT: nobody is auto-approved

        # ---------- UNIT ADMIN ----------
        if role == "unit_admin":
            unit_passcode = request.form.get("unit_passcode", "").strip()
            if not unit_passcode or not check_password_hash(unit.passcode_hash, unit_passcode):
                flash("Invalid unit passcode.", "danger")
                return redirect(url_for("register"))

        # ---------- COMPANY ROLES ----------
        else:  # admin, manager, user
            company_name = request.form.get("company_name", "").strip()
            if not company_name:
                flash("Please specify a company.", "danger")
                return redirect(url_for("register"))

            # --- Case-Insensitive Fetch Company within the Unit ---
            company = Company.query.filter(
                Company.name.ilike(company_name),
                Company.unit_id == unit.id
            ).first()

            if not company:
                flash("Selected unit / company does not exist.", "danger")
                return redirect(url_for("register"))

            company_passcode = request.form.get("company_passcode", "").strip()
            if not company_passcode or not check_password_hash(company.passcode_hash, company_passcode):
                flash("Invalid company passcode.", "danger")
                return redirect(url_for("register"))

            company_id = company.id

        # --- Create new user ---
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            unit_id=unit.id,
            company_id=company_id,
            is_approved=is_approved
        )

        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Registration error:", e)
            flash("Registration failed. Please contact administrator.", "danger")
            return redirect(url_for("register"))

        # --- Flash messages ---
        if role == "unit_admin":
            flash("Unit Admin registration submitted. Awaiting superadmin approval.", "success")
        elif role == "admin":
            flash("Admin registration submitted. Awaiting unit admin approval.", "success")
        else:
            flash("Registration submitted. Awaiting company admin approval.", "success")

        return redirect(url_for("login"))

    # --- GET: Completely clean. No database lookups transmitted over the network ---
    return render_template("register.html")

# endregion

# region set-up

@app.route("/superadmin", methods=["GET", "POST"])
def superadmin_dashboard():
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))

    current_user = User.query.get(session["user_id"])
    if not current_user or current_user.role != "superadmin":
        flash("Access denied. Only superadmins can access this page.", "danger")
        return redirect(url_for("login"))

    # Handle creating a new unit
    if request.method == "POST" and "unit_name" in request.form:
        unit_name = request.form.get("unit_name", "").strip()
        unit_passcode = request.form.get("unit_passcode", "").strip()

        if not unit_name or not unit_passcode:
            flash("Both unit name and passcode are required.", "danger")
            return redirect(url_for("superadmin_dashboard"))

        existing_unit = Unit.query.filter_by(name=unit_name).first()
        if existing_unit:
            flash(f"Unit '{unit_name}' already exists.", "warning")
            return redirect(url_for("superadmin_dashboard"))

        try:
            new_unit = Unit(
                name=unit_name,
                passcode_hash=generate_password_hash(unit_passcode)
            )
            db.session.add(new_unit)
            db.session.commit()
            flash(f"Unit '{unit_name}' created successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating unit: {str(e)}", "danger")

        return redirect(url_for("superadmin_dashboard"))

    # Fetch all units and their active admins
    units = []
    all_units = Unit.query.order_by(Unit.name).all()
    for unit in all_units:
        admins = User.query.filter_by(unit_id=unit.id, role="unit_admin", is_approved=True).all()
        units.append({"unit": unit, "admins": admins})

    # Fetch pending unit_admins
    pending_admins = User.query.filter_by(role="unit_admin", is_approved=False).all()

    return render_template(
        "superadmin_dashboard.html",
        units=units,
        pending_admins=pending_admins
    )

@app.route("/remove_unit_admin", methods=["POST"])
def remove_unit_admin():
    admin_id = request.form.get("admin_id")
    admin = User.query.get(admin_id)
    if admin and admin.role == "unit_admin":
        db.session.delete(admin)
        db.session.commit()
        flash(f"Admin '{admin.username}' removed.", "success")
    return redirect(url_for("superadmin_dashboard"))

@app.route("/remove_unit", methods=["POST"])
def remove_unit():
    unit_id = request.form.get("unit_id")
    unit = Unit.query.get(unit_id)
    if unit:
        db.session.delete(unit)
        db.session.commit()
        flash(f"Unit '{unit.name}' removed.", "success")
    return redirect(url_for("superadmin_dashboard"))

@app.route("/reset_unit_passcode", methods=["POST"])
def reset_unit_passcode():
    unit_id = request.form.get("unit_id")
    new_passcode = request.form.get("new_passcode")
    unit = Unit.query.get(unit_id)
    if unit and new_passcode:
        unit.passcode_hash = generate_password_hash(new_passcode)
        db.session.commit()
        flash(f"Passcode for unit '{unit.name}' updated.", "success")
    return redirect(url_for("superadmin_dashboard"))

@app.route('/approve_unit_admin', methods=['POST'])
def approve_unit_admin():
    if "user_id" not in session: return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    if current_user.role != "superadmin":
        flash("Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    user_id = request.form.get('user_id')
    user = db.session.get(User, user_id)

    if user:
        user.is_approved = True
        db.session.commit()
    
    return redirect(url_for('superadmin_dashboard'))

@app.route('/deny_unit_admin', methods=['POST'])
def deny_unit_admin():
    if "user_id" not in session: return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    if current_user.role != "superadmin":
        flash("Unauthorized", "danger")
        return redirect(url_for("dashboard"))

    user_id = request.form.get('user_id')
    user = db.session.get(User, user_id)

    if user:
        db.session.delete(user)
        db.session.commit()
    
    return redirect(url_for('superadmin_dashboard'))

@app.route("/unit_admin", methods=["GET", "POST"])
def unit_admin_dashboard():
    # Must be logged in
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))

    current_user = User.query.get(session["user_id"])
    if not current_user or current_user.role != "unit_admin":
        flash("Access denied. Only unit admins can access this page.", "danger")
        return redirect(url_for("login"))

    # Handle creating a new company
    if request.method == "POST" and "company_name" in request.form:
        company_name = request.form.get("company_name", "").strip()
        company_passcode = request.form.get("company_passcode", "").strip()

        if not company_name or not company_passcode:
            flash("Both company name and passcode are required.", "danger")
            return redirect(url_for("unit_admin_dashboard"))

        # Ensure company does not exist under the same unit
        existing_company = Company.query.filter_by(
            name=company_name,
            unit_id=current_user.unit_id
        ).first()
        if existing_company:
            flash(f"Company '{company_name}' already exists.", "warning")
            return redirect(url_for("unit_admin_dashboard"))

        try:
            new_company = Company(
                name=company_name,
                passcode_hash=generate_password_hash(company_passcode),
                unit_id=current_user.unit_id
            )
            db.session.add(new_company)
            db.session.commit()
            flash(f"Company '{company_name}' created successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating company: {str(e)}", "danger")

        return redirect(url_for("unit_admin_dashboard"))

    # Fetch all companies under this unit + their active admins
    companies = []
    all_companies = Company.query.filter_by(unit_id=current_user.unit_id).order_by(Company.name).all()
    for company in all_companies:
        admins = User.query.filter_by(company_id=company.id, role="admin", is_approved=True).all()
        companies.append({"company": company, "admins": admins})

    # Fetch pending admins for this unit
    pending_admins = User.query.filter_by(
        role="admin",
        is_approved=False,
        unit_id=current_user.unit_id
    ).all()

    return render_template(
        "unit_admin_dashboard.html",
        companies=companies,
        pending_admins=pending_admins
    )

@app.route("/remove_company_admin", methods=["POST"])
def remove_company_admin():
    admin_id = request.form.get("admin_id")
    admin = User.query.get(admin_id)
    if admin and admin.role == "admin":
        db.session.delete(admin)
        db.session.commit()
        flash(f"Admin '{admin.username}' removed.", "success")
    return redirect(url_for("unit_admin_dashboard"))

@app.route("/remove_company", methods=["POST"])
def remove_company():
    company_id = request.form.get("company_id")
    company = Company.query.get(company_id)
    if company:
        db.session.delete(company)
        db.session.commit()
        flash(f"Company '{company.name}' removed.", "success")
    return redirect(url_for("unit_admin_dashboard"))

@app.route("/reset_company_passcode", methods=["POST"])
def reset_company_passcode():
    company_id = request.form.get("company_id")
    new_passcode = request.form.get("new_passcode")
    company = Company.query.get(company_id)
    if company and new_passcode:
        company.passcode_hash = generate_password_hash(new_passcode)
        db.session.commit()
        flash(f"Passcode for company '{company.name}' updated.", "success")
    return redirect(url_for("unit_admin_dashboard"))

@app.route('/approve_company_admin', methods=['POST'])
def approve_company_admins():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    if not current_user or current_user.role != "unit_admin":
        flash("Unauthorized: Only Unit Admins can approve company admins.", "danger")
        return redirect(url_for("dashboard"))

    admin_id = request.form.get('admin_id')
    user = db.session.get(User, admin_id)
    
    if user:
        user.is_approved = True
        db.session.commit()
        flash(f"Admin {user.username} approved.", "success")
    else:
        flash("User not found.", "danger")
    
    return redirect(url_for('unit_admin_dashboard'))

@app.route('/deny_company_admin', methods=['POST'])
def deny_company_admin():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    if not current_user or current_user.role != "unit_admin":
        flash("Unauthorized: Only Unit Admins can deny company admins.", "danger")
        return redirect(url_for("dashboard"))

    admin_id = request.form.get('admin_id')
    user = db.session.get(User, admin_id)
    
    if user:
        username = user.username 
        db.session.delete(user)
        db.session.commit()
        flash(f"Admin request for {username} denied and removed.", "info")
    else:
        flash("User not found.", "danger")
    
    return redirect(url_for('unit_admin_dashboard'))

# endregion

# region Fire Extinguisher

@app.route("/vehicle/<int:vehicle_id>/add_extinguisher", methods=["POST"])
def add_extinguisher(vehicle_id):
    if 'user_id' not in session: return redirect(url_for("login"))
    user = db.session.get(User, session['user_id'])
    vehicle = Vehicle.query.filter_by(id=vehicle_id, company_id=user.company_id).first_or_404()
    
    name = request.form.get("name", "").strip()
    expiry_str = request.form.get("expiry_date", "")
    
    if name and expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            fe = FireExtinguisher(vehicle_id=vehicle.id, name=name, expiry_date=expiry_date)
            db.session.add(fe)
            db.session.commit()
            flash("Fire extinguisher added successfully.", "success")
        except ValueError:
            flash("Invalid date format.", "danger")
            
    return redirect(url_for("view_vehicle", license_plate=vehicle.license_plate))

@app.route("/extinguisher/<int:extinguisher_id>/delete", methods=["POST"])
def delete_extinguisher(extinguisher_id):
    if 'user_id' not in session: return redirect(url_for("login"))
    user = db.session.get(User, session['user_id'])
    fe = FireExtinguisher.query.get_or_404(extinguisher_id)
    vehicle = Vehicle.query.filter_by(id=fe.vehicle_id, company_id=user.company_id).first_or_404()
    
    db.session.delete(fe)
    db.session.commit()
    flash("Fire extinguisher removed.", "success")
    return redirect(url_for("view_vehicle", license_plate=vehicle.license_plate))

@app.route("/add_type_extinguisher", methods=["POST"])
def add_type_extinguisher():
    if "user_id" not in session: return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]: return redirect(url_for("dashboard"))
    
    type_id = request.form.get("vehicle_type_id")
    name = request.form.get("name", "").strip()
    
    if name and type_id:
        vte = VehicleTypeExtinguisher(vehicle_type_id=int(type_id), name=name)
        db.session.add(vte)
        db.session.commit()
        flash(f"Added default requirement: '{name}'", "success")
        
    return redirect(url_for("dashboard", type_id=type_id))

@app.route("/delete_type_extinguisher/<int:ext_id>", methods=["POST"])
def delete_type_extinguisher(ext_id):
    if "user_id" not in session: return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]: return redirect(url_for("dashboard"))
    
    ext = db.session.get(VehicleTypeExtinguisher, ext_id)
    type_id = ext.vehicle_type_id if ext else None
    
    if ext:
        db.session.delete(ext)
        db.session.commit()
        flash("Default requirement removed.", "success")
        
    return redirect(url_for("dashboard", type_id=type_id))

# endregion

# region dashboard

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session: return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])

    if not user or user.role in ["superadmin", "unit_admin"]:
        session.clear()
        return redirect(url_for("login"))

    # 1. Fetch all vehicle types available for this unit
    types = VehicleType.query.filter_by(company_id=user.company_id).order_by(VehicleType.name).all()

    # Determine active tab view context
    active_type_id = request.args.get("type_id", type=int)
    if not active_type_id and types:
        active_type_id = types[0].id

    # 2. Fetch ONLY stores that are bound to this company AND this specific active vehicle type
    stores = []
    if active_type_id:
        stores = Store.query.filter_by(company_id=user.company_id, vehicle_type_id=active_type_id).order_by(Store.position).all()
        
        # Sort vehicles within those specific stores
        for store in stores:
            store.display_vehicles = [v for v in store.vehicles]
            store.display_vehicles.sort(key=lambda v: (v.position is None, v.position, v.id))

    # 3. Transit monitoring stays global for cross-company handovers
    incoming = Vehicle.query.filter_by(target_company_id=user.company_id, status='in_transit').all()
    outgoing = Vehicle.query.filter_by(previous_company_id=user.company_id, status='in_transit').all()

    sg_now_naive = datetime.now(SGT).replace(tzinfo=None)

    return render_template(
        "dashboard.html",
        user=user,
        stores=stores,
        types=types,
        active_type_id=active_type_id,
        incoming=incoming,
        outgoing=outgoing,
        now=sg_now_naive
    )

@app.route("/add_vehicle_type", methods=["POST"])
def add_vehicle_type():
    if "user_id" not in session: return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
        
    name = request.form.get("name", "").strip()
    if not name:
        flash("Type name cannot be empty.", "danger")
        return redirect(url_for("dashboard"))
        
    # Create the type cleanly without handling complex list logic upfront
    new_type = VehicleType(name=name, company_id=user.company_id)
    db.session.add(new_type)
    db.session.commit()
    
    flash(f"Vehicle type '{name}' created successfully.", "success")
    return redirect(url_for("dashboard", type_id=new_type.id))

@app.route("/remove_vehicle_type", methods=["POST"])
def remove_vehicle_type():
    if "user_id" not in session: return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]: return redirect(url_for("dashboard"))

    type_id = request.form.get("vehicle_type_id", type=int)
    vt = VehicleType.query.filter_by(id=type_id, company_id=user.company_id).first()

    if vt:
        name = vt.name
        db.session.delete(vt)
        db.session.commit()
        flash(f"Vehicle type '{name}' and all its associated stores/vehicles have been removed.", "success")
    
    return redirect(url_for("dashboard"))

@app.route("/reorder_vehicles", methods=["POST"])
def reorder_vehicles():
    if "user_id" not in session:
        return {"status": "unauthorized"}, 401
    
    data = request.json
    vehicle_ids = data.get("order", [])
    
    # Update positions based on the order sent from the frontend
    for index, v_id in enumerate(vehicle_ids):
        vehicle = db.session.get(Vehicle, v_id)
        if vehicle:
            vehicle.position = index
            
    db.session.commit()
    return {"status": "success"}, 200

@app.route("/move_vehicle", methods=["POST"])
def move_vehicle():
    if 'user_id' not in session: return {"error": "Unauthorized"}, 401
    data = request.get_json()
    try:
        vehicle_id = int(data.get("vehicle_id"))
        new_store_id = int(data.get("store_id"))
    except (TypeError, ValueError):
        return {"error": "Invalid ID format"}, 400
    user = db.session.get(User, session['user_id'])
    vehicle = db.session.get(Vehicle, vehicle_id)
    new_store = db.session.get(Store, new_store_id)
    if not vehicle or not new_store: return {"error": "Vehicle or Store not found"}, 404
    if vehicle.company_id == user.company_id and new_store.company_id == user.company_id:
        vehicle.store_id = new_store_id
        vehicle.vehicle_type_id = new_store.vehicle_type_id
        db.session.commit()
        return {"success": True}, 200
    return {"error": "Permission denied: Company mismatch"}, 403

@app.route("/add_vehicle", methods=["POST"])
def add_vehicle():
    if "user_id" not in session: return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    license_plate = request.form["license_plate"].strip()
    store_id = int(request.form["store_id"])
    type_id = int(request.form["vehicle_type_id"])
    if not re.match("^[A-Za-z0-9]+$", license_plate):
        flash("Invalid License Plate: Only letters and numbers allowed.", "danger")
        return redirect(url_for('dashboard', type_id=type_id))
    vehicle = Vehicle.query.filter_by(license_plate=license_plate).first()
    if vehicle:
        if vehicle.company_id != user.company_id and vehicle.company_id is not None:
            flash("Vehicle belongs to another company.", "danger")
            return redirect(url_for("dashboard", type_id=type_id))
        vehicle.store_id = store_id
        vehicle.company_id = user.company_id
        vehicle.vehicle_type_id = type_id
    # Inside your app.route("/add_vehicle", methods=["POST"]) else block:
    else:
        vehicle = Vehicle(license_plate=license_plate, store_id=store_id, company_id=user.company_id, vehicle_type_id=type_id)
        db.session.add(vehicle)
        db.session.flush()
        
        v_type = db.session.get(VehicleType, type_id)
        if v_type:
            for template in v_type.default_extinguishers:
                # REMOVED placeholder date; defaults cleanly to None
                new_fe = FireExtinguisher(vehicle_id=vehicle.id, name=template.name, expiry_date=None)
                db.session.add(new_fe)
                
    db.session.commit()
    flash("Vehicle added with default configuration profiles.", "success")
    return redirect(url_for("dashboard", type_id=type_id))

@app.route("/move_store/<int:store_id>/<direction>")
def move_store(store_id, direction):
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]: return redirect(url_for("dashboard"))
    store = Store.query.filter_by(id=store_id, company_id=user.company_id).first()
    if not store: return redirect(url_for("dashboard"))
    if direction == "up":
        swap = Store.query.filter(Store.company_id == user.company_id, Store.vehicle_type_id == store.vehicle_type_id, Store.position < store.position).order_by(Store.position.desc()).first()
    else:
        swap = Store.query.filter(Store.company_id == user.company_id, Store.vehicle_type_id == store.vehicle_type_id, Store.position > store.position).order_by(Store.position.asc()).first()
    if swap:
        store.position, swap.position = swap.position, store.position
        db.session.commit()
    return redirect(url_for("dashboard", type_id=store.vehicle_type_id))

@app.route("/remove_vehicle", methods=["POST"])
def remove_vehicle():
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]: return redirect(url_for("dashboard"))
    vehicle = db.session.get(Vehicle, request.form["vehicle_id"])
    if vehicle and vehicle.company_id == user.company_id:
        saved_type_id = vehicle.vehicle_type_id
        vehicle.company_id = None
        vehicle.store_id = None
        db.session.commit()
        flash("Vehicle removed.", "success")
        return redirect(url_for("dashboard", type_id=saved_type_id))
    return redirect(url_for("dashboard"))

@app.route("/remove_store", methods=["POST"])
def remove_store():
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]: return redirect(url_for("dashboard"))
    store = Store.query.filter_by(id=request.form["store_id"], company_id=user.company_id).first()
    if store:
        saved_type_id = store.vehicle_type_id
        db.session.delete(store)
        db.session.commit()
        flash("Store removed.", "success")
        return redirect(url_for("dashboard", type_id=saved_type_id))
    return redirect(url_for("dashboard"))

@app.route("/add_store", methods=["POST"])
def add_store():
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    name = request.form.get("name", "").strip()
    type_id = request.form.get("vehicle_type_id", type=int)
    if not name or not type_id:
        flash("Store name and type context required.", "danger")
        return redirect(url_for("dashboard", type_id=type_id))
    existing = Store.query.filter_by(name=name, company_id=user.company_id, vehicle_type_id=type_id).first()
    if existing:
        flash("Store already exists in this type layout view.", "warning")
        return redirect(url_for("dashboard", type_id=type_id))
    new_store = Store(name=name, company_id=user.company_id, vehicle_type_id=type_id, position=Store.query.filter_by(company_id=user.company_id, vehicle_type_id=type_id).count())
    db.session.add(new_store)
    db.session.commit()
    flash("Store created.", "success")
    return redirect(url_for("dashboard", type_id=type_id))

@app.route("/edit_store/<int:store_id>", methods=["POST"])
def edit_store(store_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])
    if user.role not in ["admin", "manager"]:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))
    store = Store.query.filter_by(id=store_id, company_id=user.company_id).first_or_404()
    new_name = request.form.get("name", "").strip()
    if not new_name:
        flash("Store name cannot be empty.", "danger")
        return redirect(url_for("dashboard", type_id=store.vehicle_type_id))
    existing = Store.query.filter_by(name=new_name, company_id=user.company_id, vehicle_type_id=store.vehicle_type_id).first()
    if existing and existing.id != store.id:
        flash("Another store with that name already exists in this layout view.", "warning")
        return redirect(url_for("dashboard", type_id=store.vehicle_type_id))
    store.name = new_name
    db.session.commit()
    flash("Store name updated.", "success")
    return redirect(url_for("dashboard", type_id=store.vehicle_type_id))

@app.route("/vehicle/<string:license_plate>/faults")
def view_faults(license_plate):
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session['user_id'])

    vehicle = Vehicle.query.filter_by(
        license_plate=license_plate,
        company_id=user.company_id
    ).first()

    if not vehicle:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    faults = (
        Fault.query
        .filter_by(vehicle_id=vehicle.id)
        .order_by(Fault.last_updated.desc())
        .all()
    )

    return render_template(
        "view_faults.html",
        vehicle=vehicle,
        faults=faults,
        user=user
    )

@app.route("/vehicle/<string:license_plate>/faults/add", methods=["GET", "POST"])
def add_fault(license_plate):
    if 'user_id' not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))

    user = db.session.get(User, session['user_id'])

    vehicle = Vehicle.query.filter_by(
        license_plate=license_plate,
        company_id=user.company_id
    ).first()

    if not vehicle:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        description = request.form.get("description", "").strip()

        if not description:
            flash("Fault description is required.", "warning")
            return redirect(request.url)

        last_fault = (
            Fault.query
            .filter_by(vehicle_id=vehicle.id)
            .order_by(Fault.fault_number.desc())
            .first()
        )

        next_number = 1 if not last_fault else last_fault.fault_number + 1

        fault = Fault(
            fault_number=next_number,
            description=description,
            vehicle_id=vehicle.id
        )

        db.session.add(fault)
        db.session.commit()

        flash("Fault added successfully.", "success")
        return redirect(url_for("view_faults", license_plate=license_plate))

    return render_template(
        "add_fault.html",
        vehicle=vehicle,
        user=user
    )

@app.route("/vehicle/<int:vehicle_id>/update_shutter", methods=["POST"])
def update_shutter(vehicle_id):
    if 'user_id' not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session['user_id'])

    if user.role not in ['admin', 'manager']:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    vehicle = db.session.get(Vehicle, vehicle_id)

    if not vehicle or vehicle.company_id != user.company_id:
        flash("Vehicle not found.", "danger")
        return redirect(url_for("dashboard"))

    vehicle.shutter_number = request.form.get("shutter_number", "").strip()
    db.session.commit()

    flash("Shutter number updated.", "success")
    return redirect(url_for("view_vehicle", license_plate=vehicle.license_plate))

@app.route('/move_vehicle_store', methods=['POST'])
def move_vehicle_store():
    user = User.query.get(session.get('user_id'))
    if not user or user.role not in ['admin', 'manager']:
        return redirect(url_for('login'))

    v_id, new_s_id = request.form.get('vehicle_id'), request.form.get('new_store_id')
    vehicle = Vehicle.query.get(v_id)
    
    if vehicle and vehicle.company_id == user.company_id:
        vehicle.store_id = new_s_id
        # Append to the end of the new store's list
        vehicle.sort_order = Vehicle.query.filter_by(store_id=new_s_id).count() + 1
        db.session.commit()
    return redirect(url_for('dashboard'))

# endregion

# region company_admin 

@app.route('/admin_approvals')
def admin_approvals():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    
    # Strictly for Company-level 'admin'
    if current_user.role != "admin":
        flash("Unauthorized: This page is for company admins only.", "danger")
        return redirect(url_for("dashboard"))

    # Only fetch pending users belonging to the admin's company
    pending_users = User.query.filter_by(
        is_approved=False, 
        company_id=current_user.company_id
    ).order_by(User.id.asc()).all()

    return render_template("admin_approvals.html", pending_users=pending_users,user=current_user)

@app.route('/approve_user/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    admin = db.session.get(User, session.get("user_id"))
    user_to_approve = db.session.get(User, user_id)

    # Strictly ensure admin and applicant are in the same company
    if user_to_approve and user_to_approve.company_id == admin.company_id:
        user_to_approve.is_approved = True
        db.session.commit()
        flash(f"User {user_to_approve.username} approved successfully.", "success")
    else:
        flash("Invalid approval request.", "danger")
        
    return redirect(url_for('admin_approvals'))

@app.route('/decline_user/<int:user_id>', methods=['POST'])
def decline_user(user_id):
    admin = db.session.get(User, session.get("user_id"))
    user_to_decline = db.session.get(User, user_id)

    if user_to_decline and user_to_decline.company_id == admin.company_id:
        db.session.delete(user_to_decline)
        db.session.commit()
        flash("Application declined and removed.", "info")
    else:
        flash("Invalid decline request.", "danger")
        
    return redirect(url_for('admin_approvals'))

@app.route("/company_list")
def company_list():
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))

    current_user = db.session.get(User, session["user_id"])

    if not current_user.company_id:
        flash("You are not assigned to a company.", "danger")
        return redirect(url_for("dashboard"))

    company = db.session.get(Company, current_user.company_id)

    # Role priority for sorting: Admin → Manager → User
    role_priority = {
        "admin": 1,
        "manager": 2,
        "user": 3
    }

    # Get all approved users in the company
    users = (
        User.query
        .filter_by(company_id=company.id, is_approved=True)
        .all()
    )

    # Sort by role priority then username
    users = sorted(
        users,
        key=lambda u: (role_priority.get(u.role, 99), u.username.lower())
    )

    # 🔥 Fetch all vehicles belonging to this company
    vehicles = (
        Vehicle.query
        .filter_by(company_id=company.id)
        .order_by(Vehicle.license_plate.asc())
        .all()
    )

    return render_template(
        "company_list.html",
        company=company,
        users=users,
        user=current_user,
        vehicles=vehicles  # Enables dropdown in modal
    )

# endregion

# region tasks

@app.route("/assign-task", methods=["POST"])
def assign_task():
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))

    current_user = db.session.get(User, session["user_id"])

    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    target_user_id = request.form.get("user_id")
    task_type = request.form.get("task_type")
    vehicle_ids = request.form.getlist("vehicle_ids")

    if not all([target_user_id, task_type, vehicle_ids]):
        flash("All fields and at least one vehicle are required.", "warning")
        return redirect(url_for("company_list"))

    target_user = User.query.filter_by(
        id=target_user_id,
        company_id=current_user.company_id,
        is_approved=True
    ).first()

    if not target_user:
        flash("Invalid user.", "danger")
        return redirect(url_for("company_list"))

    assigned_count = 0
    for v_id in vehicle_ids:
        vehicle = Vehicle.query.filter_by(
            id=v_id,
            company_id=current_user.company_id
        ).first()
        
        if vehicle:
            task = Task(
                title=task_type,
                assigned_to_id=target_user.id,
                assigned_by_id=current_user.id,
                vehicle_id=vehicle.id,
                status="pending",
                is_completed=False
            )
            db.session.add(task)
            assigned_count += 1

    if assigned_count > 0:
        db.session.commit()
        flash(f"Successfully assigned {task_type} to {target_user.username} for {assigned_count} vehicles.", "success")
    else:
        flash("No valid vehicles were selected.", "danger")

    return redirect(url_for("company_list"))

@app.route("/my_tasks")
def my_tasks():
    # 1. Session check
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))

    current_user = db.session.get(User, session["user_id"])

    # 2. Fetch ONLY pending tasks for this user
    pending_tasks = Task.query.filter_by(
        assigned_to_id=current_user.id, 
        is_completed=False
    ).order_by(Task.created_at.desc()).all()

    # 3. Determine vehicle for a top-right button (Fixed: using pending_tasks)
    vehicle = next((task.vehicle for task in pending_tasks if task.vehicle), None)

    return render_template(
        "my_tasks.html",
        user=current_user,
        tasks=pending_tasks,
        vehicle=vehicle
    )

@app.route('/completed_tasks')
def completed_tasks():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    page = request.args.get('page', 1, type=int)
    
    # Sorts by Date (Newest first), then Start Time (Latest first)
    pagination = db.session.query(Logbook, Vehicle)\
        .join(Vehicle, Logbook.vehicle_id == Vehicle.id)\
        .filter(Logbook.driver_name == current_user.username)\
        .filter(Vehicle.company_id == current_user.company_id)\
        .order_by(Logbook.date.desc(), Logbook.start_time.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    return render_template('completed_tasks.html', 
                           pagination=pagination, 
                           entries=pagination.items, 
                           user=current_user)

@app.route('/company_tasks')
def company_tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    page = request.args.get('page', 1, type=int)
    user = db.session.get(User, session['user_id'])
    
    f_date = request.args.get('f_date', '').strip()
    f_loc = request.args.get('f_loc', '').strip()
    f_plate = request.args.get('f_plate', '').strip()
    f_task = request.args.get('f_task', '').strip()
    f_driver = request.args.get('f_driver', '').strip()
    
    query = db.session.query(Logbook, Vehicle).join(Vehicle, Logbook.vehicle_id == Vehicle.id).filter(Logbook.company_id == user.company_id)
    
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
        
    return render_template('company_tasks.html', pagination=pagination, entries=pagination.items, user=user)

@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    current_user = db.session.get(User, session["user_id"])
    task = Task.query.get_or_404(task_id)

    # Singapore Time Logic
    now_sg = datetime.now(SGT)
    today_sg_date = now_sg.date()
    
    # DEBUG: Get clean versions of the strings
    search_purpose = task.title.strip().upper()

    # Logbook Verification
    # We check for: Same Vehicle + Same Purpose + Same Date
    log_entry = Logbook.query.filter(
        Logbook.vehicle_id == task.vehicle_id,
        Logbook.action_type == search_purpose, # Match 'BOS' to 'BOS'
        Logbook.date == today_sg_date
    ).first()

    if not log_entry:
        # If it fails, we flash a very specific message to help you debug
        flash(f"No entry found for Vehicle {task.vehicle.license_plate} with Purpose '{search_purpose}' on {today_sg_date}.", "warning")
        return redirect(url_for('my_tasks'))

    # Success
    task.is_completed = True
    db.session.commit()
    flash(f"Task '{task.title}' verified and completed!", "success")
    return redirect(url_for('my_tasks'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    # Manual Session Check
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    if current_user.role != "admin":
        flash("Unauthorized.", "danger")
        return redirect(url_for("dashboard"))

    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task removed from company history.", "success")
    return redirect(url_for('company_tasks'))


# endregion

# region view_vehicles

@app.route("/vehicle/<string:license_plate>")
def view_vehicle(license_plate):
    if 'user_id' not in session: return redirect(url_for("login"))
    user = db.session.get(User, session['user_id'])
    vehicle = Vehicle.query.filter_by(license_plate=license_plate, company_id=user.company_id).first_or_404()
    
    # Preview sorted by Date then Time desc
    logbooks = Logbook.query.filter_by(vehicle_id=vehicle.id).order_by(Logbook.date.desc(), Logbook.start_time.desc()).limit(10).all()
    last_genrun = GenRun.query.filter_by(vehicle_id=vehicle.id).order_by(GenRun.performed_at.desc()).first()
    
    now_sg = datetime.now(SGT).replace(tzinfo=None)
    genrun_valid = (last_genrun.performed_at.replace(tzinfo=None) >= (now_sg - timedelta(days=14))) if last_genrun else False

    return render_template("view_vehicle.html", vehicle=vehicle, logbooks=logbooks, last_genrun=last_genrun, 
                           genrun_valid=genrun_valid, today=now_sg.date(), user=user)

@app.route("/update_pol_level/<int:vehicle_id>", methods=["POST"])
def update_pol_level(vehicle_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    val = request.form.get("pol_level")
    if val is not None and val.strip() != "":
        vehicle.pol_level = max(0, min(100, int(val)))
        db.session.commit()
        flash(f"POL level updated to {vehicle.pol_level}%.", "success")
    else:
        flash("No value received.", "danger")
    return redirect(url_for("view_vehicle", license_plate=vehicle.license_plate))

@app.route("/toggle_vor/<int:vehicle_id>", methods=["POST"])
def toggle_vor(vehicle_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])
    vehicle = db.session.get(Vehicle, vehicle_id)

    if not vehicle or vehicle.company_id != user.company_id:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    if user.role not in ["admin", "manager"]:
        flash("Insufficient permissions.", "danger")
        return redirect(url_for("view_vehicle", license_plate=vehicle.license_plate))

    vehicle.is_vor = not vehicle.is_vor
    db.session.commit()

    flash(
        f"Vehicle marked as {'VOR' if vehicle.is_vor else 'Operational'}.",
        "warning" if vehicle.is_vor else "success"
    )

    return redirect(url_for("view_vehicle", license_plate=vehicle.license_plate))

@app.route("/vehicle/<int:vehicle_id>/genrun", methods=["POST"])
def perform_gen_run(vehicle_id):
    # Ensure user is logged in
    if "user_id" not in session:
        flash("Please log in.", "warning")
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    # Make sure vehicle exists and belongs to the same unit as user
    vehicle = Vehicle.query.filter_by(
        id=vehicle_id,
        company_id=user.company_id
    ).first()

    if not vehicle:
        flash("Vehicle not found or access denied.", "danger")
        return redirect(url_for("dashboard"))

    # Create a new GenRun record for this vehicle
    genrun = GenRun(
        vehicle_id=vehicle.id,
        performed_by_id=user.id,
        performed_at=datetime.now(SGT)
    )

    db.session.add(genrun)
    db.session.commit()

    flash("Gen Run recorded successfully.", "success")
    return redirect(url_for("view_vehicle", license_plate=vehicle.license_plate))


# endregion

# region logbook

@app.route('/logbook/<license_plate>', methods=['GET', 'POST'])
def logbook(license_plate):
    if "user_id" not in session: return redirect(url_for("login"))
    current_user, vehicle = db.session.get(User, session['user_id']), Vehicle.query.filter_by(license_plate=license_plate).first_or_404()
    to_db_val = lambda val: None if val in [None, '', '-', 'NaN'] else val
    
    def to_time(t_str):
        if not t_str: return None
        return datetime.strptime(t_str.replace(":", "").zfill(4), '%H%M')

    # Reusable function to gather data for the page view
    def get_view_data():
        target = db.session.get(Unit, request.args.get('handover_to')).name if request.args.get('handover_to') else ""
        source = db.session.get(Unit, request.args.get('takeover_from')).name if request.args.get('takeover_from') else ""
        stores = Store.query.filter_by(company_id=(current_user.company_id if request.args.get('takeover_from') else vehicle.company_id)).all()
        history = Logbook.query.filter_by(vehicle_id=vehicle.id).order_by(Logbook.date.desc(), Logbook.id.desc()).all()
        last = history[0] if history else None
        return target, source, stores, history, last

    if request.method == 'POST':
        date_str = request.form.get('date')
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now(SGT).date()
        s_t, e_t = request.form.get('start_time'), request.form.get('end_time')
        
        error_msg = None
        if s_t and e_t:
            try:
                dt_s, dt_e = to_time(s_t), to_time(e_t)
                duration = (dt_e - dt_s).total_seconds() / 60
                run_time = int(request.form.get('moving_time') or 0) + int(request.form.get('stationary_time') or 0)
                
                if duration < run_time:
                    error_msg = f"Error: Total time ({int(duration)}m) < required run time ({run_time}m)."
                else:
                    for ex in Logbook.query.filter_by(vehicle_id=vehicle.id, date=entry_date).all():
                        if ex.start_time and ex.end_time:
                            ex_s, ex_e = to_time(ex.start_time), to_time(ex.end_time)
                            if (dt_s < ex_e) and (dt_e > ex_s):
                                error_msg = f"Time Conflict: Overlaps with {ex.start_time}-{ex.end_time}."
                                break
            except ValueError:
                error_msg = "Invalid time format. Please use HHMM."

        if error_msg:
            flash(error_msg, "danger")
            # If error, re-fetch data but RENDER instead of REDIRECT to keep form values
            target_name, source_name, display_stores, logbook_entries, last_e = get_view_data()
            return render_template('logbook.html', vehicle=vehicle, logbook=logbook_entries, user=current_user, 
                                   stores=display_stores, target_name=target_name, source_name=source_name,
                                   username=current_user.username, prev_meter=last_e.meter_reading if last_e else 0, 
                                   prev_poso=last_e.poso if last_e else 0, today=datetime.now(SGT).strftime('%Y-%m-%d'))

        # No errors, proceed to save
        action_type = request.form.get('action_type', '').upper()
        new_entry = Logbook(
            location=request.form.get('location'), action_type=action_type, start_time=s_t, end_time=to_db_val(e_t),
            moving_time=to_db_val(request.form.get('moving_time')), stationary_time=to_db_val(request.form.get('stationary_time')),
            meter_reading=to_db_val(request.form.get('meter_reading')), fuel_received=to_db_val(request.form.get('fuel_received')),
            fuel_type=to_db_val(request.form.get('fuel_type')), poso=to_db_val(request.form.get('poso')),
            driver_name=request.form.get('driver_name'), accompanying_name=request.form.get('accompanying_name'),
            vehicle_id=vehicle.id, date=entry_date, company_id=current_user.company_id 
        )
        
        if "HANDOVER TO" in action_type:
            vehicle.previous_store_id, vehicle.status, vehicle.store_id = vehicle.store_id, 'in_transit', None
            vehicle.target_company_id, vehicle.previous_company_id = request.args.get('handover_to'), vehicle.company_id
        elif "TAKEOVER FROM" in action_type:
            vehicle.company_id, vehicle.status, vehicle.store_id = current_user.company_id, 'active', request.form.get("new_store_id")
            vehicle.target_company_id = vehicle.previous_company_id = vehicle.previous_store_id = None

        db.session.add(new_entry); db.session.commit()
        return redirect(url_for('logbook', license_plate=license_plate))

    # Standard GET request
    target_name, source_name, display_stores, logbook_entries, last_e = get_view_data()
    return render_template('logbook.html', vehicle=vehicle, logbook=logbook_entries, user=current_user, stores=display_stores,
                           target_name=target_name, source_name=source_name, username=current_user.username, 
                           prev_meter=last_e.meter_reading if last_e else 0, prev_poso=last_e.poso if last_e else 0, 
                           today=datetime.now(SGT).strftime('%Y-%m-%d'))

def get_last_valid_logbook_value(vehicle_id, field_name):
    """
    Returns the last non-null, non-'-' value for a given logbook field.
    """
    entries = (
        Logbook.query
        .filter_by(vehicle_id=vehicle_id)
        .order_by(Logbook.date.desc(), Logbook.start_time.desc())
        .all()
    )

    for entry in entries:
        value = getattr(entry, field_name, None)
        if value not in (None, "-", ""):
            return value

    return None

@app.route("/api/vehicle/<int:vehicle_id>/last_values")
def vehicle_last_values(vehicle_id):
    engine_hours = get_last_valid_logbook_value(vehicle_id, "engine_hours")
    stationary_time = get_last_valid_logbook_value(vehicle_id, "stationary_time")

    return {
        "engine_hours": engine_hours,
        "stationary_time": stationary_time
    }

@app.route('/delete_logbook_entry/<int:entry_id>', methods=['POST'])
def delete_logbook_entry(entry_id):
    # Manual Session Check
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    current_user = db.session.get(User, session["user_id"])
    if current_user.role != "admin":
        flash("Unauthorized: Admins only.", "danger")
        return redirect(url_for("dashboard"))

    entry = Logbook.query.get_or_404(entry_id)
    license_plate = entry.vehicle.license_plate # Save this to redirect back
    
    db.session.delete(entry)
    db.session.commit()
    flash("Logbook entry deleted.", "success")
    return redirect(url_for('logbook', license_plate=license_plate))

# endregion

# region transfer

@app.route("/vehicle/<int:vehicle_id>/initiate_handover", methods=["POST"])
def initiate_handover(vehicle_id):
    if session.get('role') != 'admin': 
        return redirect(url_for("index"))
    
    lp = request.form.get("lp")
    otp_input = request.form.get("handover_otp", "").strip()
    
    # 1. Pull the vehicle targeted for transit
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle:
        flash("Vehicle records could not be resolved.", "danger")
        return redirect(url_for("dashboard"))
        
    # 2. Query the token table for the inputted numeric sequence
    token = HandoverToken.query.filter_by(token_string=otp_input).first()
    
    # 3. Confidential Guard Check
    if not token or get_sg_time().replace(tzinfo=None) > token.expires_at or token.vehicle_type.name != vehicle.vehicle_type.name:
        flash(f"Security Error: Mismatch. Token requires Type '{token.vehicle_type.name}', but vehicle is Type '{vehicle.vehicle_type.name}'.", "danger")
        return redirect(url_for("view_vehicle", license_plate=lp))
        
    # 4. Target destination routing is completed securely via token values
    return redirect(url_for("logbook", license_plate=lp, handover_to=token.company_id))

@app.route("/vehicles/transit")
def transit_hub():
    if 'user_id' not in session: 
        return redirect(url_for("login"))
    
    user = db.session.get(User, session['user_id'])
    
    # Proactive Cleanup: Delete expired tokens immediately from the DB file
    HandoverToken.query.filter(HandoverToken.expires_at < get_sg_time().replace(tzinfo=None)).delete()
    db.session.commit()

    incoming = Vehicle.query.filter_by(target_company_id=user.company_id, status='in_transit').all()
    outgoing = Vehicle.query.filter_by(previous_company_id=user.company_id, status='in_transit').all()
    
    # Pull only active, unexpired tokens for the UI view
    active_tokens = HandoverToken.query.filter(
        HandoverToken.company_id == user.company_id,
        HandoverToken.expires_at > get_sg_time().replace(tzinfo=None)
    ).all()
    
    vehicle_types = VehicleType.query.filter_by(company_id=user.company_id).order_by(VehicleType.name).all()    
    
    return render_template("vehicles_in_transit.html", incoming=incoming, outgoing=outgoing, user=user, active_tokens=active_tokens, vehicle_types=vehicle_types)

@app.route("/generate_handover_token", methods=["POST"])
def generate_handover_token():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))
    
    user = db.session.get(User, session["user_id"])
    if not user or not user.company_id or not user.unit_id:
        flash("Could not resolve your structural unit details.", "danger")
        return redirect(url_for("transit_hub"))
        
    vehicle_type_id = request.form.get("vehicle_type_id")
    if not vehicle_type_id:
        flash("Please specify a vehicle type for this token.", "danger")
        return redirect(url_for("transit_hub"))
        
    try:
        # Proactive Cleanup: Clear out stale tokens before calculating unique space allocations
        HandoverToken.query.filter(HandoverToken.expires_at < get_sg_time().replace(tzinfo=None)).delete()
        
        otp = HandoverToken.generate_unique_otp()
        expiration_deadline = (get_sg_time() + timedelta(hours=12)).replace(tzinfo=None)
        
        token = HandoverToken(
            token_string=otp,
            unit_id=user.unit_id,
            company_id=user.company_id,
            vehicle_type_id=int(vehicle_type_id),
            expires_at=expiration_deadline
        )
        
        db.session.add(token)
        db.session.commit()
        flash(f"Token generated successfully: {otp} (Valid for 12 hours)", "success")
    except Exception as e:
        db.session.rollback()
        print("Token Generation Error:", e)
        flash("Failed to generate operational token.", "danger")
        
    return redirect(url_for("transit_hub"))

@app.route("/reject_handover/<int:vehicle_id>", methods=['POST'])
def reject_handover(vehicle_id):
    if 'user_id' not in session: return redirect(url_for("login"))
    
    vehicle = db.session.get(Vehicle, vehicle_id)
    if vehicle and vehicle.status == 'in_transit':
        handover_entry = Logbook.query.filter(
            Logbook.vehicle_id == vehicle.id,
            Logbook.action_type.like('%HANDOVER TO%')
        ).order_by(Logbook.id.desc()).first()
        
        if handover_entry:
            db.session.delete(handover_entry)

        vehicle.company_id = vehicle.previous_company_id
        vehicle.store_id = vehicle.previous_store_id
        vehicle.status = 'active'
        vehicle.target_company_id = vehicle.previous_company_id = vehicle.previous_store_id = None
        
        db.session.commit()
        flash(f"Handover for {vehicle.license_plate} rejected. Logbook entry removed.", "info")
    
    return redirect(url_for('transit_hub'))

@app.route("/cancel_handover/<int:vehicle_id>", methods=['POST'])
def cancel_handover(vehicle_id):
    if 'user_id' not in session: return redirect(url_for("login"))
    
    vehicle = db.session.get(Vehicle, vehicle_id)
    if vehicle and vehicle.status == 'in_transit':
        handover_entry = Logbook.query.filter(
            Logbook.vehicle_id == vehicle.id,
            Logbook.action_type.like('%HANDOVER TO%')
        ).order_by(Logbook.id.desc()).first()
        
        if handover_entry:
            db.session.delete(handover_entry)

        vehicle.company_id = vehicle.previous_company_id
        vehicle.store_id = vehicle.previous_store_id
        vehicle.status = 'active'
        vehicle.target_company_id = vehicle.previous_company_id = vehicle.previous_store_id = None
        
        db.session.commit()
        flash(f"Handover cancelled. Logbook entry for {vehicle.license_plate} removed.", "warning")
        
    return redirect(url_for('transit_hub'))

# endregion


# ----------------------
# Run app
# ----------------------

# region startup

def seed_database():
    if Unit.query.first() is None:
        print("Empty database detected. Automating initial structural setup...")

        # ----------------------------------------------------
        # 1. UNIT 1 & COMPANY 1: 10C4I (Delta)
        # ----------------------------------------------------
        unit1 = Unit(name="10C4I", passcode_hash="placeholder_unit_hash")
        db.session.add(unit1)
        db.session.flush() 

        co_user = User(
            username="co", 
            password_hash=generate_password_hash("12345"), 
            role="unit_admin", 
            is_approved=True,
            unit_id=unit1.id, 
            company_id=None
        )
        db.session.add(co_user)
        
        company1 = Company(name="Delta", passcode_hash="placeholder_company_hash", unit_id=unit1.id)
        db.session.add(company1)
        db.session.flush() 
        
        oc_user = User(
            username="oc", 
            password_hash=generate_password_hash("12345"), 
            role="admin", 
            is_approved=True,
            unit_id=unit1.id, 
            company_id=company1.id
        )
        db.session.add(oc_user)

        # 1a. Create Bronco type for Delta (needed before the store can be generated)
        bronco_type_delta = VehicleType(name="Bronco", company_id=company1.id)
        db.session.add(bronco_type_delta)
        db.session.flush()

        # 1b. Create "S store" linked to both Delta Company and Bronco type
        s_store = Store(name="S store", company_id=company1.id, vehicle_type_id=bronco_type_delta.id, position=0)
        db.session.add(s_store)
        db.session.flush()

        # 1c. Seed Vehicle 99999
        v1 = Vehicle(
            license_plate="99999",
            store_id=s_store.id,
            company_id=company1.id,
            vehicle_type_id=bronco_type_delta.id,
            status="active"
        )
        db.session.add(v1)
        db.session.flush()

        fe1_v1 = FireExtinguisher(name="PFE", expiry_date=date(2027, 12, 31), vehicle_id=v1.id)
        fe2_v1 = FireExtinguisher(name="FFE", expiry_date=date(2027, 12, 31), vehicle_id=v1.id)
        db.session.add_all([fe1_v1, fe2_v1])

        # ----------------------------------------------------
        # 2. UNIT 2 & COMPANY 2: 12C4I (Alpha)
        # ----------------------------------------------------
        unit2 = Unit(name="12C4I", passcode_hash="placeholder_unit2_hash")
        db.session.add(unit2)
        db.session.flush()

        co2_user = User(
            username="co2",
            password_hash=generate_password_hash("12345"),
            role="unit_admin",
            is_approved=True,
            unit_id=unit2.id,
            company_id=None
        )
        db.session.add(co2_user)

        company2 = Company(name="Alpha", passcode_hash="placeholder_company2_hash", unit_id=unit2.id)
        db.session.add(company2)
        db.session.flush()

        oc2_user = User(
            username="oc2",
            password_hash=generate_password_hash("12345"),
            role="admin",
            is_approved=True,
            unit_id=unit2.id,
            company_id=company2.id
        )
        db.session.add(oc2_user)

        # 2a. Create Bronco type for Alpha (needed before the store can be generated)
        bronco_type_alpha = VehicleType(name="Bronco", company_id=company2.id)
        db.session.add(bronco_type_alpha)
        db.session.flush()

        # 2b. Create "A store" linked to both Alpha Company and Bronco type
        a_store = Store(name="A store", company_id=company2.id, vehicle_type_id=bronco_type_alpha.id, position=0)
        db.session.add(a_store)
        db.session.flush()

        # 2c. Seed Vehicle 00000
        v2 = Vehicle(
            license_plate="00000",
            store_id=a_store.id,
            company_id=company2.id,
            vehicle_type_id=bronco_type_alpha.id,
            status="active"
        )
        db.session.add(v2)
        db.session.flush()

        fe1_v2 = FireExtinguisher(name="PFE", expiry_date=date(2027, 12, 31), vehicle_id=v2.id)
        fe2_v2 = FireExtinguisher(name="FFE", expiry_date=date(2027, 12, 31), vehicle_id=v2.id)
        db.session.add_all([fe1_v2, fe2_v2])

        # ----------------------------------------------------
        # COMMIT DATA INTEGRATION
        # ----------------------------------------------------
        db.session.commit()
        print("Database seeding completed successfully! Stores are now properly mapped to Bronco types.")

def create_superadmin():
    existing = User.query.filter_by(role="superadmin").first()
    if existing:
        return  # already exists

    superadmin = User(
        username="superadmin",
        password_hash=generate_password_hash("admin123"),
        role="superadmin",
        is_approved=True,
        unit_id=None,
        company_id=None
    )
    db.session.add(superadmin)
    db.session.commit()

# endregion

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_superadmin() # Creates your fallback superadmin
        seed_database()     # Creates your unit, company, CO, and OC accounts
        
    app.run(debug=True)