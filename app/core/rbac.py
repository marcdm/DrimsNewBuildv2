"""
Role-Based Access Control (RBAC) utilities
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def role_required(*role_codes):
    """
    Decorator to restrict access to routes based on user roles.
    
    Usage:
        @role_required('LOGISTICS_MANAGER', 'SYSTEM_ADMINISTRATOR')
        def my_route():
            ...
    
    Args:
        *role_codes: One or more role codes that are allowed to access the route
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            user_role_codes = [role.code for role in current_user.roles]
            
            if not any(code in user_role_codes for code in role_codes):
                flash('You do not have permission to access this page.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def has_role(*role_codes):
    """
    Check if the current user has any of the specified roles.
    
    Usage in templates:
        {% if has_role('LOGISTICS_MANAGER', 'SYSTEM_ADMINISTRATOR') %}
            <a href="#">Admin Link</a>
        {% endif %}
    
    Args:
        *role_codes: One or more role codes to check
        
    Returns:
        bool: True if user has any of the specified roles
    """
    if not current_user.is_authenticated:
        return False
    
    user_role_codes = [role.code for role in current_user.roles]
    return any(code in user_role_codes for code in role_codes)


def has_all_roles(*role_codes):
    """
    Check if the current user has ALL of the specified roles.
    
    Args:
        *role_codes: One or more role codes to check
        
    Returns:
        bool: True if user has all of the specified roles
    """
    if not current_user.is_authenticated:
        return False
    
    user_role_codes = [role.code for role in current_user.roles]
    return all(code in user_role_codes for code in role_codes)


def has_warehouse_access(warehouse_id):
    """
    Check if the current user has access to a specific warehouse.
    
    Args:
        warehouse_id: The warehouse ID to check
        
    Returns:
        bool: True if user has access to the warehouse
    """
    if not current_user.is_authenticated:
        return False
    
    if has_role('SYSTEM_ADMINISTRATOR', 'LOGISTICS_MANAGER'):
        return True
    
    user_warehouse_ids = [w.warehouse_id for w in current_user.warehouses]
    return warehouse_id in user_warehouse_ids


def get_user_role_codes():
    """
    Get a list of role codes for the current user.
    
    Returns:
        list: List of role code strings
    """
    if not current_user.is_authenticated:
        return []
    
    return [role.code for role in current_user.roles]


def get_user_role_names():
    """
    Get a list of role names for the current user.
    
    Returns:
        list: List of role name strings
    """
    if not current_user.is_authenticated:
        return []
    
    return [role.name for role in current_user.roles]


def is_admin():
    """
    Check if the current user is a system administrator.
    
    Returns:
        bool: True if user is an admin
    """
    return has_role('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')


def is_logistics_manager():
    """
    Check if the current user is a logistics manager.
    
    Returns:
        bool: True if user is a logistics manager
    """
    return has_role('LOGISTICS_MANAGER')


def is_logistics_officer():
    """
    Check if the current user is a logistics officer.
    
    Returns:
        bool: True if user is a logistics officer
    """
    return has_role('LOGISTICS_OFFICER')


def can_approve_needs_lists():
    """
    Check if the current user can approve needs lists.
    
    Returns:
        bool: True if user can approve needs lists
    """
    return has_role('LOGISTICS_MANAGER', 'SYSTEM_ADMINISTRATOR')


def can_prepare_fulfilments():
    """
    Check if the current user can prepare fulfilments.
    
    Returns:
        bool: True if user can prepare fulfilments
    """
    return has_role('LOGISTICS_OFFICER', 'LOGISTICS_MANAGER', 'SYSTEM_ADMINISTRATOR')


def can_manage_users():
    """
    Check if the current user can manage users.
    
    Returns:
        bool: True if user can manage users
    """
    return has_role('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')


def can_submit_needs_lists():
    """
    Check if the current user can submit needs lists.
    
    Returns:
        bool: True if user can submit needs lists
    """
    return has_role('AGENCY_HUB', 'LOGISTICS_OFFICER', 'LOGISTICS_MANAGER', 'SYSTEM_ADMINISTRATOR')


def can_view_reports():
    """
    Check if the current user can view reports.
    
    Returns:
        bool: True if user can view reports
    """
    return current_user.is_authenticated
