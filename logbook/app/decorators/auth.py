"""
Authentication and authorization decorators.
Provides reusable decorators for login and role-based access control.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, abort
from typing import Callable, Any


def login_required(f: Callable) -> Callable:
    """
    Decorator to require user authentication for a route.
    
    Args:
        f: The route function to decorate
        
    Returns:
        The decorated function with login check
        
    Example:
        @login_required
        def dashboard():
            return render_template('dashboard.html')
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles: str) -> Callable:
    """
    Decorator to require specific user roles for a route.
    Must be used after @login_required or combined with it.
    
    Args:
        *roles: Variable number of allowed role strings
        
    Returns:
        A decorator function
        
    Example:
        @role_required('admin', 'superadmin')
        def admin_panel():
            return render_template('admin.html')
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @login_required
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            from app.models import User, db
            
            user = db.session.get(User, session["user_id"])
            if not user or user.role not in roles:
                flash("Access denied. Insufficient permissions.", "danger")
                return redirect(url_for("core.dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def superadmin_required(f: Callable) -> Callable:
    """
    Decorator specifically for superadmin-only routes.
    
    Args:
        f: The route function to decorate
        
    Returns:
        The decorated function with superadmin check
    """
    @wraps(f)
    @role_required('superadmin')
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        return f(*args, **kwargs)
    return decorated_function


def unit_admin_required(f: Callable) -> Callable:
    """
    Decorator specifically for unit_admin-only routes.
    
    Args:
        f: The route function to decorate
        
    Returns:
        The decorated function with unit_admin check
    """
    @wraps(f)
    @role_required('unit_admin')
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        return f(*args, **kwargs)
    return decorated_function


def company_admin_required(f: Callable) -> Callable:
    """
    Decorator specifically for company_admin-only routes.
    
    Args:
        f: The route function to decorate
        
    Returns:
        The decorated function with company_admin check
    """
    @wraps(f)
    @role_required('company_admin')
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        return f(*args, **kwargs)
    return decorated_function
