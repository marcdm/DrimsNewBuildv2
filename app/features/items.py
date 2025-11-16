"""
Item Management Routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from decimal import Decimal
import re

from app.db import db
from app.db.models import Item, ItemCategory, UnitOfMeasure
from app.core.audit import add_audit_fields

items_bp = Blueprint('items', __name__, url_prefix='/items')

def get_or_create_uom(uom_value, user):
    """
    Get existing UOM or create a new one if it doesn't exist.
    Returns the UOM code (uppercase).
    
    Args:
        uom_value: The UOM value to create
        user: User object (for audit fields)
    """
    # Validate and clean the UOM value
    uom_value = uom_value.strip()
    
    # Server-side validation: 2-20 characters, alphanumeric with allowed special chars
    if not re.match(r'^[A-Za-z0-9\s\-\.\/]{2,20}$', uom_value):
        raise ValueError('UOM must be 2-20 characters and contain only letters, numbers, spaces, hyphens, dots, or slashes')
    
    # Convert to uppercase (database constraint)
    uom_code = uom_value.upper()
    
    # Check if UOM already exists
    existing_uom = UnitOfMeasure.query.filter_by(uom_code=uom_code).first()
    
    if existing_uom:
        return uom_code
    
    # Create new UOM entry
    new_uom = UnitOfMeasure()
    new_uom.uom_code = uom_code
    new_uom.uom_desc = uom_code  # Use code as description for custom UOMs
    new_uom.comments_text = 'Custom UOM created by user'
    add_audit_fields(new_uom, user, is_new=True)
    
    db.session.add(new_uom)
    # Don't commit here - will be committed with the item
    
    return uom_code

@items_bp.route('/')
@login_required
def list_items():
    """List all items"""
    status_filter = request.args.get('status', 'active')
    
    query = Item.query
    if status_filter == 'active':
        query = query.filter_by(status_code='A')
    elif status_filter == 'inactive':
        query = query.filter_by(status_code='I')
    
    items = query.order_by(Item.item_name).all()
    return render_template('items/list.html', items=items, status_filter=status_filter)

@items_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_item():
    """Create new item"""
    if request.method == 'POST':
        try:
            # Get UOM selection
            uom_select = request.form.get('uom_select', '').strip()
            
            # Determine the final UOM value
            if uom_select == 'OTHER':
                # User chose "Other (specify)", get custom UOM
                uom_value = request.form.get('custom_uom', '').strip()
                if not uom_value:
                    flash('Custom UOM is required when "Other (specify)" is selected', 'danger')
                    categories = ItemCategory.query.order_by(ItemCategory.category_desc).all()
                    uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_desc).all()
                    return render_template('items/create.html', categories=categories, uoms=uoms)
                # Create new UOM entry
                uom_code = get_or_create_uom(uom_value, current_user)
            elif uom_select:
                # User selected a standard UOM from dropdown
                uom_code = uom_select
            else:
                flash('Unit of Measure is required', 'danger')
                categories = ItemCategory.query.order_by(ItemCategory.category_desc).all()
                uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_desc).all()
                return render_template('items/create.html', categories=categories, uoms=uoms)
            
            # Create item
            item = Item()
            item.item_name = (request.form.get('item_name') or '').upper()
            item.sku_code = (request.form.get('sku_code') or '').upper()
            item.category_code = request.form.get('category_code')
            item.item_desc = request.form.get('item_desc')
            item.reorder_qty = Decimal(request.form.get('reorder_qty') or '0')
            item.default_uom_code = uom_code
            item.usage_desc = request.form.get('usage_desc')
            item.storage_desc = request.form.get('storage_desc')
            item.expiration_apply_flag = request.form.get('expiration_apply_flag') == 'on'
            item.comments_text = request.form.get('comments_text')
            item.status_code = 'A'
            
            add_audit_fields(item, current_user, is_new=True)
            
            db.session.add(item)
            db.session.commit()
            
            flash(f'Item "{item.item_name}" created successfully', 'success')
            return redirect(url_for('items.list_items'))
            
        except ValueError as e:
            # Validation error
            flash(str(e), 'danger')
            categories = ItemCategory.query.order_by(ItemCategory.category_desc).all()
            uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_desc).all()
            return render_template('items/create.html', categories=categories, uoms=uoms)
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating item: {str(e)}', 'danger')
            categories = ItemCategory.query.order_by(ItemCategory.category_desc).all()
            uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_desc).all()
            return render_template('items/create.html', categories=categories, uoms=uoms)
    
    categories = ItemCategory.query.order_by(ItemCategory.category_desc).all()
    uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_desc).all()
    return render_template('items/create.html', categories=categories, uoms=uoms)
