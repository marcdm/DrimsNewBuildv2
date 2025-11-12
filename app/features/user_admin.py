from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.db.models import db, User, Role, UserRole, UserWarehouse, Warehouse
from app.core.rbac import role_required

user_admin_bp = Blueprint('user_admin', __name__)

@user_admin_bp.route('/')
@login_required
@role_required('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('user_admin/index.html', users=users)

@user_admin_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')
def create():
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        organization = request.form.get('organization', '').strip()
        job_title = request.form.get('job_title', '').strip()
        phone = request.form.get('phone', '').strip()
        is_active = request.form.get('is_active') == 'on'
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('user_admin/create.html', 
                                 roles=Role.query.all(),
                                 warehouses=Warehouse.query.filter_by(status_code='A').all())
        
        if User.query.filter_by(email=email).first():
            flash('A user with this email already exists.', 'danger')
            return render_template('user_admin/create.html',
                                 roles=Role.query.all(),
                                 warehouses=Warehouse.query.filter_by(status_code='A').all())
        
        full_name = f"{first_name} {last_name}".strip()
        
        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            full_name=full_name if full_name else None,
            organization=organization if organization else None,
            job_title=job_title if job_title else None,
            phone=phone if phone else None,
            is_active=is_active
        )
        
        db.session.add(new_user)
        db.session.flush()
        
        role_ids = request.form.getlist('roles')
        for role_id in role_ids:
            user_role = UserRole(user_id=new_user.id, role_id=int(role_id))
            db.session.add(user_role)
        
        warehouse_ids = request.form.getlist('warehouses')
        for warehouse_id in warehouse_ids:
            user_warehouse = UserWarehouse(user_id=new_user.id, warehouse_id=int(warehouse_id))
            db.session.add(user_warehouse)
        
        db.session.commit()
        flash(f'User {email} created successfully.', 'success')
        return redirect(url_for('user_admin.index'))
    
    roles = Role.query.all()
    warehouses = Warehouse.query.filter_by(status_code='A').all()
    return render_template('user_admin/create.html', roles=roles, warehouses=warehouses)

@user_admin_bp.route('/<int:user_id>')
@login_required
@role_required('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')
def view(user_id):
    
    user = User.query.get_or_404(user_id)
    return render_template('user_admin/view.html', user=user)

@user_admin_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')
def edit(user_id):
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        user.organization = request.form.get('organization', '').strip() or None
        user.job_title = request.form.get('job_title', '').strip() or None
        user.phone = request.form.get('phone', '').strip() or None
        user.is_active = request.form.get('is_active') == 'on'
        
        full_name = f"{user.first_name} {user.last_name}".strip()
        user.full_name = full_name if full_name else None
        
        password = request.form.get('password', '').strip()
        if password:
            user.password_hash = generate_password_hash(password)
        
        UserRole.query.filter_by(user_id=user.id).delete()
        role_ids = request.form.getlist('roles')
        for role_id in role_ids:
            user_role = UserRole(user_id=user.id, role_id=int(role_id))
            db.session.add(user_role)
        
        UserWarehouse.query.filter_by(user_id=user.id).delete()
        warehouse_ids = request.form.getlist('warehouses')
        for warehouse_id in warehouse_ids:
            user_warehouse = UserWarehouse(user_id=user.id, warehouse_id=int(warehouse_id))
            db.session.add(user_warehouse)
        
        db.session.commit()
        flash(f'User {user.email} updated successfully.', 'success')
        return redirect(url_for('user_admin.view', user_id=user.id))
    
    roles = Role.query.all()
    warehouses = Warehouse.query.filter_by(status_code='A').all()
    user_role_ids = [r.id for r in user.roles]
    user_warehouse_ids = [w.warehouse_id for w in user.warehouses]
    
    return render_template('user_admin/edit.html', 
                         user=user, 
                         roles=roles, 
                         warehouses=warehouses,
                         user_role_ids=user_role_ids,
                         user_warehouse_ids=user_warehouse_ids)

@user_admin_bp.route('/<int:user_id>/deactivate', methods=['POST'])
@login_required
@role_required('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')
def deactivate(user_id):
    
    if user_id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('user_admin.view', user_id=user_id))
    
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    
    flash(f'User {user.email} has been deactivated.', 'success')
    return redirect(url_for('user_admin.index'))

@user_admin_bp.route('/<int:user_id>/activate', methods=['POST'])
@login_required
@role_required('SYSTEM_ADMINISTRATOR', 'SYS_ADMIN')
def activate(user_id):
    
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    
    flash(f'User {user.email} has been activated.', 'success')
    return redirect(url_for('user_admin.index'))
