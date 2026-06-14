"""
Application configuration with constants and settings.
Centralizes all magic numbers, strings, and configuration values.
"""
import os
from datetime import timedelta


class Config:
    """Base configuration class."""
    
    # Flask security
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///instance/app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session security
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Password policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = False
    
    # Token generation
    HANDOVER_TOKEN_HOURS = 12
    HANDOVER_TOKEN_LENGTH = 10
    
    # Pagination
    LOGBOOK_ENTRIES_PER_PAGE = 10
    VEHICLES_PER_PAGE = 20
    TASKS_PER_PAGE = 10
    FAULTS_PER_PAGE = 15
    
    # Business rules
    GENRUN_VALIDITY_DAYS = 14
    MAX_LOGBOOK_CONFLICT_DAYS = 7
    
    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Rate limiting (requests per minute)
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_LOGIN = "5 per minute"
    RATELIMIT_REGISTER = "3 per minute"
    
    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"


# Role constants for consistent usage across the codebase
class Role:
    """User role constants."""
    SUPERADMIN = "superadmin"
    UNIT_ADMIN = "unit_admin"
    COMPANY_ADMIN = "company_admin"
    MANAGER = "manager"
    USER = "user"
    
    @classmethod
    def all_roles(cls) -> list:
        return [cls.SUPERADMIN, cls.UNIT_ADMIN, cls.COMPANY_ADMIN, cls.MANAGER, cls.USER]
    
    @classmethod
    def admin_roles(cls) -> list:
        return [cls.SUPERADMIN, cls.UNIT_ADMIN, cls.COMPANY_ADMIN, cls.MANAGER]


# Task status constants
class TaskStatus:
    """Task status constants."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
    @classmethod
    def all_statuses(cls) -> list:
        return [cls.PENDING, cls.IN_PROGRESS, cls.COMPLETED, cls.CANCELLED]


# Fault status constants
class FaultStatus:
    """Fault status constants."""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    
    @classmethod
    def all_statuses(cls) -> list:
        return [cls.OPEN, cls.IN_PROGRESS, cls.RESOLVED, cls.CLOSED]


# Vehicle status constants
class VehicleStatus:
    """Vehicle status constants."""
    ACTIVE = "active"
    IN_TRANSIT = "in_transit"
    VOR = "vor"  # Vehicle Off Road
    MAINTENANCE = "maintenance"
    
    @classmethod
    def all_statuses(cls) -> list:
        return [cls.ACTIVE, cls.IN_TRANSIT, cls.VOR, cls.MAINTENANCE]


# Flash message categories
class FlashCategory:
    """Standardized flash message categories."""
    SUCCESS = "success"      # Green - Operation completed successfully
    INFO = "info"           # Blue - Informational message
    WARNING = "warning"     # Yellow - Caution needed
    ERROR = "error"         # Red - Critical failure
    DANGER = "danger"       # Red - Security/access issues