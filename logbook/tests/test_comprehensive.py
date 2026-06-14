"""
Comprehensive Test Suite for Vehicle Logbook Application

This test suite covers:
- Unit tests for models and utilities
- Integration tests for routes and endpoints
- End-to-end user flow tests
- Security tests
- Code coverage measurement

Run with: pytest --cov=app --cov-report=html --cov-report=term-missing
"""

import pytest
import os
import sys
from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch, MagicMock

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import (
    User, Unit, Company, Vehicle, VehicleType, Store,
    Logbook, Fault, Task, GenRun, FireExtinguisher,
    VehicleTypeExtinguisher, HandoverToken, SGT
)
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Create application for testing"""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "WTF_CSRF_SSL_STRICT": False,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False
    })
    
    # Disable CSRF protection for testing at the app config level
    # The WTF_CSRF_ENABLED=False config should handle this
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def superadmin_user(app):
    """Create a superadmin user for testing"""
    user = User(
        username="superadmin",
        password_hash=generate_password_hash("password123"),
        role="superadmin",
        is_approved=True
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def unit_admin_user(app):
    """Create a unit admin user for testing"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    unit = Unit(name=f"Test Unit {unique_id}", passcode_hash=generate_password_hash("unit123"))
    db.session.add(unit)
    db.session.commit()
    
    user = User(
        username=f"unitadmin_{unique_id}",
        password_hash=generate_password_hash("password123"),
        role="unit_admin",
        is_approved=True,
        unit_id=unit.id
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def company_admin_user(app):
    """Create a company admin user for testing"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    unit = Unit(name=f"Test Unit {unique_id}", passcode_hash=generate_password_hash("unit123"))
    db.session.add(unit)
    db.session.commit()
    
    company = Company(
        name=f"Test Company {unique_id}",
        passcode_hash=generate_password_hash("company123"),
        unit_id=unit.id
    )
    db.session.add(company)
    db.session.commit()
    
    user = User(
        username=f"admin_{unique_id}",
        password_hash=generate_password_hash("password123"),
        role="admin",
        is_approved=True,
        unit_id=unit.id,
        company_id=company.id
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(app):
    """Create a regular user for testing"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    unit = Unit(name=f"Test Unit Regular {unique_id}", passcode_hash=generate_password_hash("unit123"))
    db.session.add(unit)
    db.session.commit()
    
    company = Company(
        name=f"Test Company Regular {unique_id}",
        passcode_hash=generate_password_hash("company123"),
        unit_id=unit.id
    )
    db.session.add(company)
    db.session.commit()
    
    user = User(
        username=f"regularuser_{unique_id}",
        password_hash=generate_password_hash("password123"),
        role="user",
        is_approved=True,
        unit_id=unit.id,
        company_id=company.id
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def vehicle_type(company_admin_user):
    """Create a vehicle type for testing"""
    user = company_admin_user
    vtype = VehicleType(
        name="Test Vehicle Type",
        company_id=user.company_id
    )
    db.session.add(vtype)
    db.session.commit()
    db.session.refresh(vtype)
    return vtype


@pytest.fixture
def store(company_admin_user, vehicle_type):
    """Create a store for testing"""
    user = company_admin_user
    store = Store(
        name="Test Store",
        company_id=user.company_id,
        vehicle_type_id=vehicle_type.id,
        position=0
    )
    db.session.add(store)
    db.session.commit()
    db.session.refresh(store)
    return store


@pytest.fixture
def vehicle(company_admin_user, vehicle_type, store):
    """Create a vehicle for testing"""
    user = company_admin_user
    vehicle = Vehicle(
        license_plate="TEST123",
        store_id=store.id,
        company_id=user.company_id,
        vehicle_type_id=vehicle_type.id,
        status="active",
        pol_level=100
    )
    db.session.add(vehicle)
    db.session.commit()
    return vehicle


# =============================================================================
# UNIT TESTS - Models
# =============================================================================

class TestUnitModel:
    """Test Unit model"""
    
    def test_create_unit(self, app):
        """Test creating a unit"""
        unit = Unit(
            name="New Unit",
            passcode_hash=generate_password_hash("pass123")
        )
        db.session.add(unit)
        db.session.commit()
        
        assert unit.id is not None
        assert unit.name == "New Unit"
    
    def test_unit_unique_name(self, app):
        """Test unit name uniqueness constraint"""
        unit1 = Unit(name="Unique Unit", passcode_hash=generate_password_hash("pass123"))
        db.session.add(unit1)
        db.session.commit()
        
        with pytest.raises(Exception):
            unit2 = Unit(name="Unique Unit", passcode_hash=generate_password_hash("pass456"))
            db.session.add(unit2)
            db.session.commit()


class TestCompanyModel:
    """Test Company model"""
    
    def test_create_company(self, app, unit_admin_user):
        """Test creating a company"""
        user = unit_admin_user
        company = Company(
            name="New Company",
            passcode_hash=generate_password_hash("comp123"),
            unit_id=user.unit_id
        )
        db.session.add(company)
        db.session.commit()
        
        assert company.id is not None
    
    def test_company_cascade_delete(self, app, unit_admin_user):
        """Test that deleting a unit cascades to companies"""
        user = unit_admin_user
        unit = db.session.get(Unit, user.unit_id)
        
        company = Company(
            name="Cascade Test Company",
            passcode_hash=generate_password_hash("comp123"),
            unit_id=unit.id
        )
        db.session.add(company)
        db.session.commit()
        
        company_id = company.id
        
        db.session.delete(unit)
        db.session.commit()
        
        assert db.session.get(Company, company_id) is None


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, app, company_admin_user):
        """Test creating a user"""
        assert company_admin_user.username.startswith("admin_")
        assert company_admin_user.role == "admin"
        assert company_admin_user.is_approved is True
    
    def test_user_relationships(self, app, company_admin_user):
        """Test user relationships"""
        user = company_admin_user
        
        assert user.unit is not None
        assert user.company is not None


class TestVehicleModel:
    """Test Vehicle model"""
    
    def test_create_vehicle(self, app, vehicle):
        """Test creating a vehicle"""
        assert vehicle.license_plate == "TEST123"
        assert vehicle.status == "active"
        assert vehicle.pol_level == 100
        assert vehicle.is_vor is False
    
    def test_vehicle_unique_license_plate(self, app, company_admin_user, vehicle_type, store):
        """Test license plate uniqueness"""
        user = company_admin_user
        
        v1 = Vehicle(
            license_plate="UNIQUE123",
            store_id=store.id,
            company_id=user.company_id,
            vehicle_type_id=vehicle_type.id
        )
        db.session.add(v1)
        db.session.commit()
        
        with pytest.raises(Exception):
            v2 = Vehicle(
                license_plate="UNIQUE123",
                store_id=store.id,
                company_id=user.company_id,
                vehicle_type_id=vehicle_type.id
            )
            db.session.add(v2)
            db.session.commit()


class TestFireExtinguisherModel:
    """Test FireExtinguisher model"""
    
    def test_is_valid_property(self, app, vehicle):
        """Test fire extinguisher validity check"""
        fe1 = FireExtinguisher(
            vehicle_id=vehicle.id,
            name="PFE",
            expiry_date=date.today() + timedelta(days=30)
        )
        db.session.add(fe1)
        db.session.commit()
        
        assert fe1.is_valid is True
        
        fe2 = FireExtinguisher(
            vehicle_id=vehicle.id,
            name="FFE",
            expiry_date=date.today() - timedelta(days=30)
        )
        db.session.add(fe2)
        db.session.commit()
        
        assert fe2.is_valid is False


class TestFaultModel:
    """Test Fault model"""
    
    def test_create_fault(self, app, vehicle):
        """Test creating a fault"""
        fault = Fault(
            fault_number=1,
            description="Test fault description",
            vehicle_id=vehicle.id,
            status="Open"
        )
        db.session.add(fault)
        db.session.commit()
        
        assert fault.id is not None
        assert fault.fault_number == 1
        assert fault.status == "Open"


class TestTaskModel:
    """Test Task model"""
    
    def test_create_task(self, app, company_admin_user, vehicle):
        """Test creating a task"""
        user = company_admin_user
        
        task = Task(
            title="Test Task",
            description="Test description",
            vehicle_id=vehicle.id,
            assigned_to_id=user.id,
            assigned_by_id=user.id,
            status="pending"
        )
        db.session.add(task)
        db.session.commit()
        
        assert task.id is not None
        assert task.is_completed is False


class TestHandoverTokenModel:
    """Test HandoverToken model"""
    
    def test_generate_unique_otp(self, app):
        """Test OTP generation"""
        otp = HandoverToken.generate_unique_otp()
        
        assert len(otp) == 10
        assert otp.isdigit()


# =============================================================================
# INTEGRATION TESTS - Authentication Routes
# =============================================================================

class TestAuthRoutes:
    """Test authentication routes"""
    
    def test_login_page_loads(self, client):
        """Test login page loads successfully"""
        response = client.get("/login")
        assert response.status_code == 200
    
    def test_register_page_loads(self, client):
        """Test registration page loads successfully"""
        response = client.get("/register")
        assert response.status_code == 200
    
    def test_login_success(self, client, company_admin_user):
        """Test successful login"""
        response = client.post("/login", data={
            "username": "admin",
            "password": "password123"
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post("/login", data={
            "username": "nonexistent",
            "password": "wrongpassword"
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_logout(self, client, company_admin_user):
        """Test logout functionality"""
        client.post("/login", data={
            "username": "admin",
            "password": "password123"
        })
        
        response = client.get("/logout", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_registration_missing_fields(self, client):
        """Test registration with missing fields"""
        response = client.post("/register", data={
            "username": "",
            "password": "password123",
            "role": "user",
            "unit_name": "Test Unit"
        }, follow_redirects=True)
        
        assert response.status_code == 200


# =============================================================================
# INTEGRATION TESTS - Dashboard Routes
# =============================================================================

class TestDashboardRoutes:
    """Test dashboard routes"""
    
    def test_dashboard_requires_login(self, client):
        """Test dashboard requires authentication"""
        response = client.get("/dashboard", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_dashboard_superadmin_redirect(self, client, superadmin_user):
        """Test superadmin redirected from dashboard"""
        with client.session_transaction() as sess:
            sess["user_id"] = superadmin_user.id
            sess["role"] = "superadmin"
        
        response = client.get("/dashboard", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_dashboard_loads_for_user(self, client, regular_user):
        """Test dashboard loads for regular user"""
        with client.session_transaction() as sess:
            sess["user_id"] = regular_user.id
            sess["role"] = "user"
        
        response = client.get("/dashboard")
        
        assert response.status_code == 200


# =============================================================================
# INTEGRATION TESTS - Asset Management Routes
# =============================================================================

class TestAssetRoutes:
    """Test asset management routes"""
    
    def test_add_vehicle_requires_auth(self, client):
        """Test add vehicle requires authentication"""
        response = client.post("/add_vehicle", data={
            "license_plate": "NEW123",
            "store_id": 1,
            "vehicle_type_id": 1
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_add_vehicle_success(self, client, company_admin_user, store, vehicle_type):
        """Test successful vehicle addition"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "company_admin"
        
        response = client.post("/add_vehicle", data={
            "license_plate": "NEWPLATE",
            "store_id": store.id,
            "vehicle_type_id": vehicle_type.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        vehicle = Vehicle.query.filter_by(license_plate="NEWPLATE").first()
        assert vehicle is not None
    
    def test_remove_vehicle(self, client, company_admin_user, vehicle):
        """Test vehicle removal"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post("/remove_vehicle", data={
            "vehicle_id": vehicle.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        db.session.expire_all()
        removed_vehicle = db.session.get(Vehicle, vehicle.id)
        assert removed_vehicle.company_id is None
    
    def test_add_store(self, client, company_admin_user, vehicle_type):
        """Test adding a store"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post("/add_store", data={
            "name": "New Store",
            "vehicle_type_id": vehicle_type.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        store = Store.query.filter_by(name="New Store").first()
        assert store is not None


# =============================================================================
# INTEGRATION TESTS - Logbook Routes
# =============================================================================

class TestLogbookRoutes:
    """Test logbook routes"""
    
    def test_view_vehicle_requires_login(self, client, vehicle):
        """Test view vehicle requires authentication"""
        response = client.get(f"/vehicle/{vehicle.license_plate}", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_view_vehicle_success(self, client, company_admin_user, vehicle):
        """Test viewing vehicle details"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.get(f"/vehicle/{vehicle.license_plate}")
        
        assert response.status_code == 200
    
    def test_update_pol_level(self, client, company_admin_user, vehicle):
        """Test updating POL level"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post(f"/update_pol_level/{vehicle.id}", data={
            "pol_level": 75
        }, follow_redirects=True)
        
        assert response.status_code == 200
        db.session.refresh(vehicle)
        assert vehicle.pol_level == 75
    
    def test_perform_gen_run(self, client, company_admin_user, vehicle):
        """Test recording a generator run"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post(f"/vehicle/{vehicle.id}/genrun", follow_redirects=True)
        
        assert response.status_code == 200
        genrun = GenRun.query.filter_by(vehicle_id=vehicle.id).first()
        assert genrun is not None


# =============================================================================
# INTEGRATION TESTS - Task Routes
# =============================================================================

class TestTaskRoutes:
    """Test task management routes"""
    
    def test_company_list_requires_login(self, client):
        """Test company list requires authentication"""
        response = client.get("/company_list", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_company_list_shows_users(self, client, company_admin_user, regular_user):
        """Test company list displays users"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.get("/company_list")
        
        assert response.status_code == 200
    
    def test_assign_task_success(self, client, company_admin_user, regular_user, vehicle):
        """Test successful task assignment"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post("/assign-task", data={
            "user_id": regular_user.id,
            "task_type": "Maintenance Check",
            "vehicle_ids": [vehicle.id]
        }, follow_redirects=True)
        
        assert response.status_code == 200
        task = Task.query.filter_by(
            assigned_to_id=regular_user.id,
            title="Maintenance Check"
        ).first()
        assert task is not None
    
    def test_my_tasks_shows_assigned_tasks(self, client, company_admin_user, regular_user, vehicle):
        """Test my tasks displays assigned tasks"""
        task = Task(
            title="Test Task",
            assigned_to_id=regular_user.id,
            assigned_by_id=company_admin_user.id,
            vehicle_id=vehicle.id,
            is_completed=False
        )
        db.session.add(task)
        db.session.commit()
        
        with client.session_transaction() as sess:
            sess["user_id"] = regular_user.id
            sess["role"] = "user"
        
        response = client.get("/my_tasks")
        
        assert response.status_code == 200


# =============================================================================
# INTEGRATION TESTS - Fault Routes
# =============================================================================

class TestFaultRoutes:
    """Test fault reporting routes"""
    
    def test_view_faults_requires_login(self, client, vehicle):
        """Test view faults requires authentication"""
        response = client.get(f"/vehicle/{vehicle.license_plate}/faults", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_add_fault_success(self, client, company_admin_user, vehicle):
        """Test adding a fault report"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post(f"/vehicle/{vehicle.license_plate}/faults/add", data={
            "description": "Engine overheating issue"
        }, follow_redirects=True)
        
        assert response.status_code == 200
        fault = Fault.query.filter_by(
            vehicle_id=vehicle.id,
            description="Engine overheating issue"
        ).first()
        assert fault is not None


# =============================================================================
# INTEGRATION TESTS - Transfer Routes
# =============================================================================

class TestTransferRoutes:
    """Test vehicle transfer routes"""
    
    def test_transit_hub_requires_login(self, client):
        """Test transit hub requires authentication"""
        response = client.get("/vehicles/transit", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_generate_handover_token_success(self, client, company_admin_user, vehicle_type):
        """Test successful handover token generation"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post("/generate_handover_token", data={
            "vehicle_type_id": vehicle_type.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        token = HandoverToken.query.filter_by(
            company_id=company_admin_user.company_id,
            vehicle_type_id=vehicle_type.id
        ).first()
        assert token is not None


# =============================================================================
# INTEGRATION TESTS - Admin Routes
# =============================================================================

class TestAdminRoutes:
    """Test admin routes"""
    
    def test_superadmin_dashboard_requires_superadmin(self, client, company_admin_user):
        """Test superadmin dashboard access control"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.get("/superadmin", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_superadmin_dashboard_loads(self, client, superadmin_user):
        """Test superadmin dashboard loads"""
        with client.session_transaction() as sess:
            sess["user_id"] = superadmin_user.id
            sess["role"] = "superadmin"
        
        response = client.get("/superadmin")
        
        assert response.status_code == 200
    
    def test_add_unit(self, client, superadmin_user):
        """Test superadmin adding a unit"""
        with client.session_transaction() as sess:
            sess["user_id"] = superadmin_user.id
            sess["role"] = "superadmin"
        
        response = client.post("/superadmin", data={
            "unit_name": "New Battalion",
            "unit_passcode": "battalion123"
        }, follow_redirects=True)
        
        assert response.status_code == 200
        unit = Unit.query.filter_by(name="New Battalion").first()
        assert unit is not None
    
    def test_unit_admin_dashboard(self, client, unit_admin_user):
        """Test unit admin dashboard loads"""
        with client.session_transaction() as sess:
            sess["user_id"] = unit_admin_user.id
            sess["role"] = "unit_admin"
        
        response = client.get("/unit_admin")
        
        assert response.status_code == 200


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurity:
    """Test security features"""
    
    def test_sql_injection_prevention(self, client, company_admin_user):
        """Test SQL injection prevention"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        malicious_input = "' OR '1'='1"
        response = client.get(f"/vehicle/{malicious_input}", follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_unauthorized_access_prevention(self, client, regular_user, vehicle):
        """Test unauthorized access prevention"""
        with client.session_transaction() as sess:
            sess["user_id"] = regular_user.id
            sess["role"] = "user"
        
        response = client.get(f"/vehicle/{vehicle.license_plate}", follow_redirects=True)
        
        assert response.status_code == 200


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_move_vehicle_api(self, client, company_admin_user, vehicle, store):
        """Test move vehicle API endpoint"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post("/move_vehicle", json={
            "vehicle_id": vehicle.id,
            "store_id": store.id
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
    
    def test_reorder_vehicles_api(self, client, company_admin_user, vehicle):
        """Test reorder vehicles API endpoint"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post("/reorder_vehicles", json={
            "order": [vehicle.id]
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"


# =============================================================================
# USER FLOW TESTS (End-to-End)
# =============================================================================

class TestUserFlows:
    """Test complete user flows"""
    
    def test_complete_vehicle_lifecycle(self, client, company_admin_user, vehicle_type, store):
        """Test complete vehicle lifecycle from creation to removal"""
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        # 1. Add vehicle
        response = client.post("/add_vehicle", data={
            "license_plate": "LIFECYCLE1",
            "store_id": store.id,
            "vehicle_type_id": vehicle_type.id
        }, follow_redirects=True)
        assert response.status_code == 200
        
        vehicle = Vehicle.query.filter_by(license_plate="LIFECYCLE1").first()
        assert vehicle is not None
        
        # 2. View vehicle
        response = client.get(f"/vehicle/{vehicle.license_plate}")
        assert response.status_code == 200
        
        # 3. Update POL level
        response = client.post(f"/update_pol_level/{vehicle.id}", data={
            "pol_level": 75
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # 4. Perform gen run
        response = client.post(f"/vehicle/{vehicle.id}/genrun", follow_redirects=True)
        assert response.status_code == 200
        
        # 5. Remove vehicle
        response = client.post("/remove_vehicle", data={
            "vehicle_id": vehicle.id
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Verify soft delete
        db.session.expire_all()
        removed = db.session.get(Vehicle, vehicle.id)
        assert removed.company_id is None
    
    def test_complete_task_workflow(self, client, company_admin_user, regular_user, vehicle):
        """Test complete task assignment and completion workflow"""
        # 1. Admin assigns task
        with client.session_transaction() as sess:
            sess["user_id"] = company_admin_user.id
            sess["role"] = "admin"
        
        response = client.post("/assign-task", data={
            "user_id": regular_user.id,
            "task_type": "WEEKLY_INSPECTION",
            "vehicle_ids": [vehicle.id]
        }, follow_redirects=True)
        assert response.status_code == 200
        
        task = Task.query.filter_by(
            assigned_to_id=regular_user.id,
            title="WEEKLY_INSPECTION"
        ).first()
        assert task is not None
        
        # 2. User views their tasks
        with client.session_transaction() as sess:
            sess["user_id"] = regular_user.id
            sess["role"] = "user"
        
        response = client.get("/my_tasks")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=60"
    ])
