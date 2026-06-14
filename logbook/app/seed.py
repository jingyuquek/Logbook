import os
from datetime import date, datetime, timedelta, timezone
from werkzeug.security import generate_password_hash

# Import your shared extension and models from your package
from app import db
from app.models import (
    User, Unit, Company, VehicleType, 
    VehicleTypeExtinguisher, Store, Vehicle, FireExtinguisher
)

# Shared SGT constant matching your app logic
SGT = timezone(timedelta(hours=8))


def create_superadmin():
    """Ensures a baseline superadmin user exists in the system."""
    existing = User.query.filter_by(role="superadmin").first()
    if existing:
        print("Superadmin user already exists. Skipping baseline profile setup.")
        return

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
    print("Superadmin user created successfully! (User: superadmin / Pass: admin123)")


def seed_mock_data():
    """Populates structural mock database records for development and layout testing."""
    # Check if a baseline structural unit already exists to prevent duplication
    if Unit.query.filter_by(name="First Battalion").first():
        print("Database already contains structural seed rows. Skipping mock layout seeding.")
        return

    print("Seeding baseline application layout data...")

    # 1. Seed Units
    unit1 = Unit(name="First Battalion", passcode_hash=generate_password_hash("unit123"))
    db.session.add(unit1)
    db.session.flush()  # Populates unit1.id for downstream relationships

    # 2. Seed Companies
    company1 = Company(name="Alpha Company", passcode_hash=generate_password_hash("alpha123"), unit_id=unit1.id)
    company2 = Company(name="Bravo Company", passcode_hash=generate_password_hash("bravo123"), unit_id=unit1.id)
    db.session.add_all([company1, company2])
    db.session.flush()

    # 3. Seed Vehicle Types & Default Configuration Profiles
    type_bronco = VehicleType(name="Bronco Carrier", company_id=company1.id)
    type_truck = VehicleType(name="Logistics Truck", company_id=company2.id)
    db.session.add_all([type_bronco, type_truck])
    db.session.flush()

    # Add default layout extinguisher requirements to vehicle categories
    req1 = VehicleTypeExtinguisher(vehicle_type_id=type_bronco.id, name="Portable Fire Extinguisher (PFE)")
    req2 = VehicleTypeExtinguisher(vehicle_type_id=type_bronco.id, name="Fixed Fire Extinguisher (FFE)")
    db.session.add_all([req1, req2])
    db.session.flush()

    # 4. Seed Store Layout Nodes
    store_a = Store(name="A-Bay Store", company_id=company1.id, vehicle_type_id=type_bronco.id, position=0)
    store_b = Store(name="B-Bay Store", company_id=company2.id, vehicle_type_id=type_truck.id, position=0)
    db.session.add_all([store_a, store_b])
    db.session.flush()

    # 5. Seed Assets (Vehicles & Connected Extinguishers)
    v1 = Vehicle(
        license_plate="MID1234X",
        store_id=store_a.id,
        company_id=company1.id,
        vehicle_type_id=type_bronco.id,
        status="active"
    )
    db.session.add(v1)
    db.session.flush()

    # Match active asset extinguishers dynamically
    fe1 = FireExtinguisher(name="PFE", expiry_date=date(2027, 12, 31), vehicle_id=v1.id)
    db.session.add(fe1)

    db.session.commit()
    print("Database seeding completed successfully! Mock profiles structural mapping complete.")


def run_seeder():
    """Wrapper function to invoke all setup sequences inside an app context execution."""
    create_superadmin()
    # Optional: uncomment if you want mock layouts auto-generated locally
    # seed_mock_data()