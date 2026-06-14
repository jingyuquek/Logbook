"""
Services layer for business logic.
Separates business logic from route handlers for better maintainability.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy import and_
from app.models import db, User, Vehicle, Logbook, Task, Fault, GenRun, Store, Company, Unit, VehicleType, HandoverToken, FireExtinguisher
from app.config import Config, Role, TaskStatus, FaultStatus, VehicleStatus, FlashCategory
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user-related operations."""
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.session.get(User, user_id)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username."""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_users_by_company(company_id: int, approved: bool = True) -> List[User]:
        """Get all users in a company."""
        return User.query.filter_by(company_id=company_id, is_approved=approved).all()
    
    @staticmethod
    def get_pending_approvals(role: str = None, unit_id: int = None) -> List[User]:
        """Get pending user approvals."""
        query = User.query.filter_by(is_approved=False)
        if role:
            query = query.filter_by(role=role)
        if unit_id:
            query = query.filter_by(unit_id=unit_id)
        return query.all()
    
    @staticmethod
    def approve_user(user: User) -> bool:
        """Approve a user."""
        try:
            user.is_approved = True
            db.session.commit()
            logger.info(f"User {user.username} approved")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to approve user {user.username}: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def reject_user(user: User) -> bool:
        """Reject and delete a user."""
        try:
            db.session.delete(user)
            db.session.commit()
            logger.info(f"User {user.username} rejected and deleted")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reject user {user.username}: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Validate password against security policy."""
        if len(password) < Config.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {Config.PASSWORD_MIN_LENGTH} characters long."
        
        if Config.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter."
        
        if Config.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter."
        
        if Config.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number."
        
        return True, ""


class VehicleService:
    """Service class for vehicle-related operations."""
    
    @staticmethod
    def get_vehicle_by_id(vehicle_id: int) -> Optional[Vehicle]:
        """Get vehicle by ID."""
        return db.session.get(Vehicle, vehicle_id)
    
    @staticmethod
    def get_vehicle_by_plate(license_plate: str) -> Optional[Vehicle]:
        """Get vehicle by license plate."""
        return Vehicle.query.filter_by(license_plate=license_plate).first()
    
    @staticmethod
    def get_vehicles_by_company(company_id: int, status: str = None) -> List[Vehicle]:
        """Get all vehicles for a company."""
        query = Vehicle.query.filter_by(company_id=company_id)
        if status:
            query = query.filter_by(status=status)
        return query.all()
    
    @staticmethod
    def get_vehicles_by_store(store_id: int) -> List[Vehicle]:
        """Get all vehicles in a store."""
        return Vehicle.query.filter_by(store_id=store_id).all()
    
    @staticmethod
    def create_vehicle(
        license_plate: str,
        store_id: int,
        company_id: int,
        vehicle_type_id: int,
        position: int = None,
        status: str = VehicleStatus.ACTIVE
    ) -> Tuple[Optional[Vehicle], str]:
        """Create a new vehicle."""
        try:
            # Check if vehicle already exists
            existing = db.session.query(Vehicle).filter_by(license_plate=license_plate).first()
            if existing:
                return None, "Vehicle with this license plate already exists."
            
            vehicle = Vehicle(
                license_plate=license_plate,
                store_id=store_id,
                company_id=company_id,
                vehicle_type_id=vehicle_type_id,
                position=position,
                status=status
            )
            db.session.add(vehicle)
            db.session.flush()  # Get the ID before commit
            
            # Create default fire extinguishers
            v_type = db.session.get(VehicleType, vehicle_type_id)
            if v_type:
                for template in v_type.default_extinguishers:
                    db.session.add(FireExtinguisher(
                        vehicle=vehicle,
                        name=template.name,
                        expiry_date=None
                    ))
            
            db.session.commit()
            logger.info(f"Vehicle {license_plate} created successfully")
            return vehicle, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create vehicle {license_plate}: {str(e)}", exc_info=True)
            return None, str(e)
    
    @staticmethod
    def move_vehicle(vehicle_id: int, store_id: int, company_id: int) -> Tuple[bool, str]:
        """Move a vehicle to a different store."""
        try:
            vehicle = db.session.get(Vehicle, vehicle_id)
            store = db.session.get(Store, store_id)
            
            if not vehicle or not store:
                return False, "Vehicle or store not found."
            
            if vehicle.company_id != company_id or store.company_id != company_id:
                return False, "Permission denied."
            
            vehicle.store = store
            vehicle.vehicle_type_id = store.vehicle_type_id
            db.session.commit()
            logger.info(f"Vehicle {vehicle.license_plate} moved to store {store.name}")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to move vehicle: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def reorder_vehicles(order: List[int], company_id: int) -> Tuple[bool, str]:
        """Reorder vehicles within a store."""
        try:
            for index, v_id in enumerate(order):
                vehicle = db.session.get(Vehicle, v_id)
                if vehicle and vehicle.company_id == company_id:
                    vehicle.position = index
                else:
                    logger.warning(f"Unauthorized reorder attempt for vehicle {v_id}")
            
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reorder vehicles: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def toggle_vor(vehicle_id: int, company_id: int) -> Tuple[Optional[Vehicle], str]:
        """Toggle vehicle VOR status."""
        try:
            vehicle = db.session.get(Vehicle, vehicle_id)
            if not vehicle or vehicle.company_id != company_id:
                return None, "Access denied."
            
            vehicle.is_vor = not vehicle.is_vor
            db.session.commit()
            logger.info(f"Vehicle {vehicle.license_plate} VOR status toggled to {vehicle.is_vor}")
            return vehicle, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to toggle VOR: {str(e)}", exc_info=True)
            return None, str(e)
    
    @staticmethod
    def update_pol_level(vehicle_id: int, pol_level: int) -> Tuple[bool, str]:
        """Update vehicle POL level."""
        try:
            vehicle = db.session.get(Vehicle, vehicle_id)
            if not vehicle:
                return False, "Vehicle not found."
            
            vehicle.pol_level = max(0, min(100, pol_level))
            db.session.commit()
            logger.info(f"Vehicle {vehicle.license_plate} POL level updated to {vehicle.pol_level}%")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update POL level: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def check_genrun_validity(vehicle: Vehicle) -> bool:
        """Check if vehicle's genrun is valid."""
        if not vehicle.gen_runs:
            return False
        
        now_naive = datetime.now().replace(tzinfo=None)
        threshold = now_naive - timedelta(days=Config.GENRUN_VALIDITY_DAYS)
        last_run = max(vehicle.gen_runs, key=lambda gr: gr.performed_at)
        last_run_time = last_run.performed_at.replace(tzinfo=None) if last_run.performed_at.tzinfo else last_run.performed_at
        return last_run_time >= threshold


class LogbookService:
    """Service class for logbook-related operations."""
    
    @staticmethod
    def get_entries_by_vehicle(vehicle_id: int, limit: int = None) -> List[Logbook]:
        """Get logbook entries for a vehicle."""
        query = Logbook.query.filter_by(vehicle_id=vehicle_id).order_by(Logbook.date.desc(), Logbook.start_time.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @staticmethod
    def get_entries_by_company(company_id: int, filters: Dict[str, str] = None, page: int = 1, per_page: int = 10) -> Any:
        """Get logbook entries for a company with pagination and filters."""
        query = db.session.query(Logbook, Vehicle).join(Vehicle, Logbook.vehicle_id == Vehicle.id).filter(Logbook.company_id == company_id)
        
        if filters:
            conditions = []
            if filters.get('date'):
                from sqlalchemy import cast, String
                conditions.append(cast(Logbook.date, String).ilike(f"%{filters['date']}%"))
            if filters.get('location'):
                conditions.append(Logbook.location.ilike(f"%{filters['location']}%"))
            if filters.get('license_plate'):
                conditions.append(Vehicle.license_plate.ilike(f"%{filters['license_plate']}%"))
            if filters.get('action_type'):
                conditions.append(Logbook.action_type.ilike(f"%{filters['action_type']}%"))
            if filters.get('driver_name'):
                conditions.append(Logbook.driver_name.ilike(f"%{filters['driver_name']}%"))
            
            if conditions:
                query = query.filter(and_(*conditions))
        
        return query.order_by(Logbook.date.desc(), Logbook.start_time.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def create_entry(data: Dict[str, Any]) -> Tuple[Optional[Logbook], str]:
        """Create a new logbook entry."""
        try:
            entry = Logbook(**data)
            db.session.add(entry)
            db.session.commit()
            logger.info(f"Logbook entry created for vehicle {data.get('vehicle_id')}")
            return entry, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create logbook entry: {str(e)}", exc_info=True)
            return None, str(e)
    
    @staticmethod
    def delete_entry(entry_id: int) -> Tuple[bool, str]:
        """Delete a logbook entry."""
        try:
            entry = db.session.get(Logbook, entry_id)
            if not entry:
                return False, "Entry not found."
            
            db.session.delete(entry)
            db.session.commit()
            logger.info(f"Logbook entry {entry_id} deleted")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete logbook entry: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def get_last_valid_value(vehicle_id: int, field: str) -> Any:
        """Get the last valid value for a field from logbook entries."""
        entry = Logbook.query.filter_by(vehicle_id=vehicle_id).order_by(Logbook.date.desc(), Logbook.id.desc()).first()
        if entry:
            value = getattr(entry, field, None)
            if value not in [None, '', '-', 'NaN']:
                return value
        return None
    
    @staticmethod
    def check_time_conflicts(vehicle_id: int, date: datetime.date, start_time: str, end_time: str) -> Optional[str]:
        """Check for time conflicts with existing entries."""
        def to_time(t_str):
            if not t_str:
                return None
            try:
                return datetime.strptime(t_str.replace(":", "").zfill(4), '%H%M')
            except ValueError:
                return None
        
        dt_start = to_time(start_time)
        dt_end = to_time(end_time)
        
        if not dt_start or not dt_end:
            return None
        
        for existing in Logbook.query.filter_by(vehicle_id=vehicle_id, date=date).all():
            if existing.start_time and existing.end_time:
                ex_start = to_time(existing.start_time)
                ex_end = to_time(existing.end_time)
                if ex_start and ex_end:
                    if (dt_start < ex_end) and (dt_end > ex_start):
                        return f"Time Conflict: Overlaps with {existing.start_time}-{existing.end_time}."
        
        return None


class TaskService:
    """Service class for task-related operations."""
    
    @staticmethod
    def get_tasks_by_user(user_id: int, completed: bool = False) -> List[Task]:
        """Get tasks for a user."""
        return Task.query.filter_by(assigned_to_id=user_id, is_completed=completed).all()
    
    @staticmethod
    def get_tasks_by_company(company_id: int) -> List[Task]:
        """Get all tasks for a company."""
        return Task.query.join(Vehicle).filter(Vehicle.company_id == company_id).all()
    
    @staticmethod
    def create_task(
        title: str,
        assigned_to_id: int,
        assigned_by_id: int,
        vehicle_id: int = None,
        description: str = None
    ) -> Tuple[Optional[Task], str]:
        """Create a new task."""
        try:
            task = Task(
                title=title,
                description=description,
                assigned_to_id=assigned_to_id,
                assigned_by_id=assigned_by_id,
                vehicle_id=vehicle_id,
                status=TaskStatus.PENDING,
                is_completed=False
            )
            db.session.add(task)
            db.session.commit()
            logger.info(f"Task '{title}' created for user {assigned_to_id}")
            return task, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create task: {str(e)}", exc_info=True)
            return None, str(e)
    
    @staticmethod
    def complete_task(task_id: int) -> Tuple[bool, str]:
        """Mark a task as completed."""
        try:
            task = db.session.get(Task, task_id)
            if not task:
                return False, "Task not found."
            
            task.is_completed = True
            task.status = TaskStatus.COMPLETED
            db.session.commit()
            logger.info(f"Task {task_id} completed")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to complete task: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def delete_task(task_id: int) -> Tuple[bool, str]:
        """Delete a task."""
        try:
            task = db.session.get(Task, task_id)
            if not task:
                return False, "Task not found."
            
            db.session.delete(task)
            db.session.commit()
            logger.info(f"Task {task_id} deleted")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete task: {str(e)}", exc_info=True)
            return False, str(e)


class FaultService:
    """Service class for fault-related operations."""
    
    @staticmethod
    def get_faults_by_vehicle(vehicle_id: int) -> List[Fault]:
        """Get all faults for a vehicle."""
        return Fault.query.filter_by(vehicle_id=vehicle_id).order_by(Fault.last_updated.desc()).all()
    
    @staticmethod
    def create_fault(vehicle_id: int, description: str) -> Tuple[Optional[Fault], str]:
        """Create a new fault report."""
        try:
            from datetime import datetime
            from app.models import SGT
            
            # Get next fault number
            last_fault = Fault.query.filter_by(vehicle_id=vehicle_id).order_by(Fault.fault_number.desc()).first()
            next_number = 1 if not last_fault else last_fault.fault_number + 1
            
            fault = Fault(
                fault_number=next_number,
                description=description,
                vehicle_id=vehicle_id,
                status=FaultStatus.OPEN,
                date_reported=datetime.now(SGT),
                last_updated=datetime.now(SGT)
            )
            db.session.add(fault)
            db.session.commit()
            logger.info(f"Fault #{next_number} created for vehicle {vehicle_id}")
            return fault, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create fault: {str(e)}", exc_info=True)
            return None, str(e)
    
    @staticmethod
    def update_fault_status(fault_id: int, status: str) -> Tuple[bool, str]:
        """Update fault status."""
        try:
            from datetime import datetime
            from app.models import SGT
            
            fault = db.session.get(Fault, fault_id)
            if not fault:
                return False, "Fault not found."
            
            fault.status = status
            fault.last_updated = datetime.now(SGT)
            db.session.commit()
            logger.info(f"Fault {fault_id} status updated to {status}")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update fault status: {str(e)}", exc_info=True)
            return False, str(e)


class TransferService:
    """Service class for vehicle transfer operations."""
    
    @staticmethod
    def generate_handover_token(
        unit_id: int,
        company_id: int,
        vehicle_type_id: int,
        validity_hours: int = 12
    ) -> Tuple[Optional[HandoverToken], str]:
        """Generate a new handover token."""
        try:
            from datetime import datetime, timedelta
            from app.models import SGT
            
            # Clean up expired tokens
            HandoverToken.query.filter(HandoverToken.expires_at < datetime.now(SGT).replace(tzinfo=None)).delete()
            
            otp = HandoverToken.generate_unique_otp()
            expiration_deadline = (datetime.now(SGT) + timedelta(hours=validity_hours)).replace(tzinfo=None)
            
            token = HandoverToken(
                token_string=otp,
                unit_id=unit_id,
                company_id=company_id,
                vehicle_type_id=vehicle_type_id,
                expires_at=expiration_deadline
            )
            db.session.add(token)
            db.session.commit()
            logger.info(f"Handover token generated: {otp}")
            return token, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to generate handover token: {str(e)}", exc_info=True)
            return None, str(e)
    
    @staticmethod
    def validate_handover_token(token_string: str, vehicle_type_name: str) -> Tuple[Optional[HandoverToken], str]:
        """Validate a handover token."""
        from datetime import datetime
        from app.models import SGT
        
        token = HandoverToken.query.filter_by(token_string=token_string).first()
        
        if not token:
            return None, "Invalid token."
        
        if datetime.now(SGT).replace(tzinfo=None) > token.expires_at:
            # Clean up expired token
            db.session.delete(token)
            db.session.commit()
            return None, "Token has expired."
        
        if token.vehicle_type.name != vehicle_type_name:
            return None, f"Token requires Type '{token.vehicle_type.name}', but vehicle type does not match."
        
        return token, ""
    
    @staticmethod
    def cancel_handover(vehicle_id: int) -> Tuple[bool, str]:
        """Cancel a vehicle handover."""
        try:
            vehicle = db.session.get(Vehicle, vehicle_id)
            if not vehicle or vehicle.status != 'in_transit':
                return False, "Vehicle not in transit."
            
            # Remove handover logbook entry
            handover_entry = Logbook.query.filter(
                Logbook.vehicle_id == vehicle.id,
                Logbook.action_type.like('%HANDOVER TO%')
            ).order_by(Logbook.id.desc()).first()
            
            if handover_entry:
                db.session.delete(handover_entry)
            
            # Restore vehicle to previous state
            vehicle.company_id = vehicle.previous_company_id
            vehicle.store_id = vehicle.previous_store_id
            vehicle.status = VehicleStatus.ACTIVE
            vehicle.target_company_id = None
            vehicle.previous_company_id = None
            vehicle.previous_store_id = None
            
            db.session.commit()
            logger.info(f"Handover cancelled for vehicle {vehicle.license_plate}")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to cancel handover: {str(e)}", exc_info=True)
            return False, str(e)


class StoreService:
    """Service class for store-related operations."""
    
    @staticmethod
    def get_stores_by_company(company_id: int, vehicle_type_id: int = None) -> List[Store]:
        """Get stores for a company."""
        query = Store.query.filter_by(company_id=company_id)
        if vehicle_type_id:
            query = query.filter_by(vehicle_type_id=vehicle_type_id)
        return query.order_by(Store.position).all()
    
    @staticmethod
    def create_store(name: str, company_id: int, vehicle_type_id: int) -> Tuple[Optional[Store], str]:
        """Create a new store."""
        try:
            # Get next position
            pos_count = Store.query.filter_by(company_id=company_id, vehicle_type_id=vehicle_type_id).count()
            
            store = Store(
                name=name,
                company_id=company_id,
                vehicle_type_id=vehicle_type_id,
                position=pos_count
            )
            db.session.add(store)
            db.session.commit()
            logger.info(f"Store '{name}' created")
            return store, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create store: {str(e)}", exc_info=True)
            return None, str(e)
    
    @staticmethod
    def delete_store(store_id: int, company_id: int) -> Tuple[bool, str]:
        """Delete a store."""
        try:
            store = Store.query.filter_by(id=store_id, company_id=company_id).first()
            if not store:
                return False, "Store not found."
            
            db.session.delete(store)
            db.session.commit()
            logger.info(f"Store {store_id} deleted")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete store: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def update_store(store_id: int, name: str, company_id: int) -> Tuple[bool, str]:
        """Update store name."""
        try:
            store = Store.query.filter_by(id=store_id, company_id=company_id).first()
            if not store:
                return False, "Store not found."
            
            # Check for duplicates
            existing = Store.query.filter_by(name=name, company_id=company_id, vehicle_type_id=store.vehicle_type_id).first()
            if existing and existing.id != store_id:
                return False, "Another store with that name already exists."
            
            store.name = name
            db.session.commit()
            logger.info(f"Store {store_id} name updated to '{name}'")
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update store: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def move_store(store_id: int, direction: str, company_id: int) -> Tuple[bool, str]:
        """Move store position up or down."""
        try:
            store = Store.query.filter_by(id=store_id, company_id=company_id).first()
            if not store:
                return False, "Store not found."
            
            if direction == "up":
                swap = Store.query.filter(
                    Store.company_id == company_id,
                    Store.vehicle_type_id == store.vehicle_type_id,
                    Store.position < store.position
                ).order_by(Store.position.desc()).first()
            else:
                swap = Store.query.filter(
                    Store.company_id == company_id,
                    Store.vehicle_type_id == store.vehicle_type_id,
                    Store.position > store.position
                ).order_by(Store.position.asc()).first()
            
            if swap:
                store.position, swap.position = swap.position, store.position
                db.session.commit()
                logger.info(f"Store {store_id} moved {direction}")
                return True, ""
            else:
                return False, "Cannot move further in this direction."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to move store: {str(e)}", exc_info=True)
            return False, str(e)
