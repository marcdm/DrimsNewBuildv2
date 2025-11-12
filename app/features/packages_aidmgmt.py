"""
Relief Packages (AIDMGMT Workflow - Step 2)
Handles creation and management of relief packages from approved requests
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from app.db import db
from app.db.models import ReliefPkg, ReliefPkgItem, ReliefRqst, ReliefRqstItem, Inventory, Item, Warehouse
from app.core.audit import add_audit_fields

packages_bp = Blueprint('packages', __name__, url_prefix='/packages')

@packages_bp.route('/')
@login_required
def list_packages():
    """List all relief packages"""
    status_filter = request.args.get('status', 'all')
    
    query = ReliefPkg.query
    
    if status_filter == 'pending':
        query = query.filter_by(status_code='P')
    elif status_filter == 'dispatched':
        query = query.filter_by(status_code='D')
    elif status_filter == 'completed':
        query = query.filter_by(status_code='C')
    
    packages = query.order_by(ReliefPkg.reliefpkg_id.desc()).all()
    
    return render_template('packages/list.html', 
                         packages=packages,
                         status_filter=status_filter)

@packages_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_package():
    """Create a relief package from an approved request"""
    if request.method == 'POST':
        try:
            reliefrqst_id = int(request.form.get('reliefrqst_id'))
            
            relief_request = ReliefRqst.query.get_or_404(reliefrqst_id)
            
            if relief_request.status_code not in [2, 3]:
                flash('Only approved or partially fulfilled requests can be packaged', 'danger')
                return redirect(url_for('packages.create_package'))
            
            warehouse_id = int(request.form.get('warehouse_id'))
            
            package = ReliefPkg()
            package.reliefrqst_id = reliefrqst_id
            package.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            package.transport_mode = request.form.get('transport_mode')
            package.comments_text = request.form.get('comments_text')
            package.status_code = 'P'
            
            inventory = Inventory.query.filter_by(
                warehouse_id=warehouse_id,
                status_code='A'
            ).first()
            
            if not inventory:
                flash('Selected warehouse has no active inventory', 'danger')
                return redirect(url_for('packages.create_package'))
            
            package.to_inventory_id = inventory.inventory_id
            
            add_audit_fields(package, current_user.email, is_new=True)
            package.verify_by_id = current_user.email.upper()
            package.verify_dtime = datetime.now()
            
            db.session.add(package)
            db.session.flush()
            
            item_rqst_ids = request.form.getlist('rqst_item_id[]')
            item_qtys = request.form.getlist('item_qty[]')
            
            for rqst_item_id_str, qty_str in zip(item_rqst_ids, item_qtys):
                if rqst_item_id_str and qty_str:
                    rqst_item_id = int(rqst_item_id_str)
                    qty = float(qty_str)
                    
                    if qty <= 0:
                        flash(f'Quantity must be positive: received {qty}', 'danger')
                        db.session.rollback()
                        return redirect(url_for('packages.create_package'))
                    
                    rqst_item = ReliefRqstItem.query.filter_by(
                        reliefrqst_id=reliefrqst_id,
                        item_id=rqst_item_id
                    ).first()
                    
                    if not rqst_item:
                        flash(f'Item {rqst_item_id} not in original request', 'danger')
                        db.session.rollback()
                        return redirect(url_for('packages.create_package'))
                    
                    remaining_qty = rqst_item.request_qty - rqst_item.issue_qty
                    if qty > remaining_qty:
                        flash(f'Quantity {qty} exceeds remaining amount {remaining_qty} for item {rqst_item.item.item_name}', 'danger')
                        db.session.rollback()
                        return redirect(url_for('packages.create_package'))
                    
                    source_inventory = Inventory.query.filter_by(
                        warehouse_id=warehouse_id,
                        item_id=rqst_item_id,
                        status_code='A'
                    ).first()
                    
                    if not source_inventory:
                        flash(f'Item {rqst_item.item.item_name} not available in selected warehouse', 'danger')
                        db.session.rollback()
                        return redirect(url_for('packages.create_package'))
                    
                    if source_inventory.usable_qty < qty:
                        flash(f'Insufficient stock: {source_inventory.usable_qty} available, {qty} requested for {rqst_item.item.item_name}', 'danger')
                        db.session.rollback()
                        return redirect(url_for('packages.create_package'))
                    
                    pkg_item = ReliefPkgItem()
                    pkg_item.reliefpkg_id = package.reliefpkg_id
                    pkg_item.fr_inventory_id = source_inventory.inventory_id
                    pkg_item.item_id = rqst_item_id
                    pkg_item.item_qty = qty
                    pkg_item.uom_code = source_inventory.uom_code
                    
                    add_audit_fields(pkg_item, current_user.email, is_new=True)
                    db.session.add(pkg_item)
                    
                    rqst_item.issue_qty += qty
                    add_audit_fields(rqst_item, current_user.email, is_new=False)
            
            if len(item_rqst_ids) == 0 or all(not qty_str or float(qty_str) <= 0 for qty_str in item_qtys if qty_str):
                flash('Package must contain at least one item with positive quantity', 'danger')
                db.session.rollback()
                return redirect(url_for('packages.create_package'))
            
            db.session.commit()
            
            flash(f'Relief Package #{package.reliefpkg_id} created successfully', 'success')
            return redirect(url_for('packages.view_package', package_id=package.reliefpkg_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating package: {str(e)}', 'danger')
            return redirect(url_for('packages.create_package'))
    
    reliefrqst_id = request.args.get('request_id', type=int)
    selected_request = None
    request_items = []
    
    if reliefrqst_id:
        selected_request = ReliefRqst.query.filter_by(reliefrqst_id=reliefrqst_id).first()
        if selected_request and selected_request.status_code in [2, 3]:
            request_items = selected_request.items
    
    approved_requests = ReliefRqst.query.filter(
        ReliefRqst.status_code.in_([2, 3])
    ).order_by(ReliefRqst.reliefrqst_id.desc()).all()
    
    warehouses = Warehouse.query.filter_by(status_code='A').all()
    today = date.today().isoformat()
    
    return render_template('packages/create.html',
                         approved_requests=approved_requests,
                         selected_request=selected_request,
                         request_items=request_items,
                         warehouses=warehouses,
                         today=today)

@packages_bp.route('/<int:package_id>')
@login_required
def view_package(package_id):
    """View relief package details"""
    package = ReliefPkg.query.get_or_404(package_id)
    
    return render_template('packages/view.html', package=package)

@packages_bp.route('/<int:package_id>/dispatch', methods=['POST'])
@login_required
def dispatch_package(package_id):
    """Mark package as dispatched"""
    package = ReliefPkg.query.get_or_404(package_id)
    
    if package.status_code != 'P':
        flash('Only pending packages can be dispatched', 'danger')
        return redirect(url_for('packages.view_package', package_id=package_id))
    
    package.status_code = 'D'
    package.dispatch_dtime = datetime.now()
    
    add_audit_fields(package, current_user.email, is_new=False)
    
    db.session.commit()
    
    flash(f'Package #{package_id} dispatched successfully', 'success')
    return redirect(url_for('packages.view_package', package_id=package_id))
