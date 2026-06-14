"""
Centralized Authentication and Authorization Decorators.

This module provides reusable decorators for securing routes,
replacing manual session checks and ensuring consistent security policies.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request
from logbook.models import db, User, Role
from logbook.config import FlashCategory


def login_required(f):
    """
    Decorator to require a user to be logged in.
    
    Checks if 'user_id' exists in the session and verifies the user
    still exists and is active in the database.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', FlashCategory.WARNING)
            return redirect(url_for('auth.login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your session has expired or the account is inactive. Please log in again.', FlashCategory.ERROR)
            return redirect(url_for('auth.login'))
        
        # Attach user object to request context for easy access in routes
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """
    Decorator to require specific roles for access.
    
    Usage: @role_required('admin', 'company_admin')
    Must be used AFTER @login_required.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                flash('Authentication required.', FlashCategory.ERROR)
                return redirect(url_for('auth.login'))
            
            user = request.current_user
            if user.role.name not in allowed_roles:
                flash('You do not have permission to access this page.', FlashCategory.ERROR)
                # Redirect based on role or default to dashboard
                if user.role.name == Role.DRIVER:
                    return redirect(url_for('core.driver_dashboard'))
                elif user.role.name == Role.MECHANIC:
                    return redirect(url_for('core.mechanic_dashboard'))
                return redirect(url_for('core.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Convenience decorators for specific roles
def superadmin_required(f):
    return role_required(Role.SUPER_ADMIN)(f)


def company_admin_required(f):
    return role_required(Role.COMPANY_ADMIN)(f)


def mechanic_required(f):
    return role_required(Role.MECHANIC)(f)


def driver_required(f):
    return role_required(Role.DRIVER)(f)
