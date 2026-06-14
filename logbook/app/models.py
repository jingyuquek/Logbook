from datetime import date, datetime, timedelta, timezone
from app import db

SGT = timezone(timedelta(hours=8))


class Unit(db.Model):
    __tablename__ = "unit"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    passcode_hash = db.Column(db.String(255), nullable=False)

    companies = db.relationship("Company", backref="companies_in_unit", lazy=True, cascade="all, delete-orphan")
    users = db.relationship("User", backref="users_in_unit", lazy=True)
    

class Company(db.Model):
    __tablename__ = "company"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    passcode_hash = db.Column(db.String(255), nullable=False)

    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id"), nullable=False)

    users = db.relationship("User", backref="company_employees", lazy=True)
    stores = db.relationship("Store", backref="store_company", lazy=True, cascade="all, delete-orphan")
    vehicle_types = db.relationship("VehicleType", backref="vt_company", lazy=True, cascade="all, delete-orphan")

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(30), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)

    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id"), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True)

    unit = db.relationship('Unit', backref='users_assigned_to_unit')
    company = db.relationship('Company', backref='users_assigned_to_company')

class VehicleType(db.Model):
    __tablename__ = "vehicle_type"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)

    company = db.relationship("Company", backref="types_in_company", lazy=True)
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
        threshold = now_naive - datetime.timedelta(days=14)
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
