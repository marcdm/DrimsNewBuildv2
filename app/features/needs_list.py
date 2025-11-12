from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.db.models import db, NeedsList, NeedsListItem, Agency, Event, Item
from app.core.status import get_status_badge_class, get_status_label
from datetime import datetime
from decimal import Decimal

needs_list_bp = Blueprint('needs_list', __name__)

@needs_list_bp.route('/')
@login_required
def index():
    needs_lists = NeedsList.query.order_by(NeedsList.created_at.desc()).all()
    return render_template('needs_list/index.html', needs_lists=needs_lists)

@needs_list_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            latest_list = NeedsList.query.order_by(NeedsList.id.desc()).first()
            next_id = (latest_list.id + 1) if latest_list else 1
            list_number = f"NL{next_id:06d}"
            
            needs_list = NeedsList(
                list_number=list_number,
                agency_id=int(request.form['agency_id']),
                event_id=int(request.form['event_id']),
                submission_type=request.form.get('submission_type', 'DRAFT'),
                requested_by_name=request.form.get('requested_by_name'),
                requested_by_contact=request.form.get('requested_by_contact'),
                priority=request.form.get('priority', 'MEDIUM'),
                urgency=request.form.get('urgency', 'ROUTINE'),
                status='Draft',
                is_draft=True,
                notes=request.form.get('notes'),
                justification=request.form.get('justification'),
                created_by=current_user.email
            )
            
            db.session.add(needs_list)
            db.session.flush()
            
            item_count = 0
            for key in request.form:
                if key.startswith('item_') and '_qty' in key:
                    item_id = int(key.split('_')[1])
                    qty = request.form.get(key)
                    if qty and float(qty) > 0:
                        item_notes = request.form.get(f'item_{item_id}_notes', '')
                        item_justification = request.form.get(f'item_{item_id}_justification', '')
                        
                        needs_item = NeedsListItem(
                            needs_list_id=needs_list.id,
                            item_id=item_id,
                            requested_qty=Decimal(qty),
                            notes=item_notes,
                            justification=item_justification,
                            status='Pending'
                        )
                        db.session.add(needs_item)
                        item_count += 1
            
            if item_count == 0:
                flash('Please add at least one item to the needs list', 'danger')
                db.session.rollback()
                agencies = Agency.query.order_by(Agency.agency_name).all()
                events = Event.query.filter_by(status_code='A').order_by(Event.event_name).all()
                items = Item.query.filter_by(status_code='A').order_by(Item.item_name).all()
                return render_template('needs_list/create.html', agencies=agencies, events=events, items=items)
            
            db.session.commit()
            flash(f'Needs list {list_number} created successfully with {item_count} items', 'success')
            return redirect(url_for('needs_list.view', needs_list_id=needs_list.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating needs list: {str(e)}', 'danger')
    
    agencies = Agency.query.order_by(Agency.agency_name).all()
    events = Event.query.filter_by(status_code='A').order_by(Event.event_name).all()
    items = Item.query.filter_by(status_code='A').order_by(Item.item_name).all()
    return render_template('needs_list/create.html', agencies=agencies, events=events, items=items)

@needs_list_bp.route('/<int:needs_list_id>')
@login_required
def view(needs_list_id):
    needs_list = NeedsList.query.get_or_404(needs_list_id)
    return render_template('needs_list/view.html', needs_list=needs_list)

@needs_list_bp.route('/<int:needs_list_id>/submit', methods=['POST'])
@login_required
def submit(needs_list_id):
    needs_list = NeedsList.query.get_or_404(needs_list_id)
    
    if not needs_list.is_draft:
        flash('This needs list has already been submitted', 'warning')
        return redirect(url_for('needs_list.view', needs_list_id=needs_list_id))
    
    try:
        needs_list.is_draft = False
        needs_list.status = 'Submitted'
        needs_list.submitted_at = datetime.now()
        needs_list.updated_at = datetime.now()
        
        db.session.commit()
        flash(f'Needs list {needs_list.list_number} submitted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting needs list: {str(e)}', 'danger')
    
    return redirect(url_for('needs_list.view', needs_list_id=needs_list_id))

@needs_list_bp.route('/<int:needs_list_id>/approve', methods=['POST'])
@login_required
def approve(needs_list_id):
    needs_list = NeedsList.query.get_or_404(needs_list_id)
    
    if needs_list.status != 'Submitted':
        flash('Only submitted needs lists can be approved', 'warning')
        return redirect(url_for('needs_list.view', needs_list_id=needs_list_id))
    
    try:
        needs_list.status = 'Approved'
        needs_list.approved_by = current_user.email
        needs_list.approved_at = datetime.now()
        needs_list.updated_at = datetime.now()
        
        for item in needs_list.items:
            item.approved_qty = item.requested_qty
            item.status = 'Approved'
        
        db.session.commit()
        flash(f'Needs list {needs_list.list_number} approved successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving needs list: {str(e)}', 'danger')
    
    return redirect(url_for('needs_list.view', needs_list_id=needs_list_id))

@needs_list_bp.route('/<int:needs_list_id>/reject', methods=['POST'])
@login_required
def reject(needs_list_id):
    needs_list = NeedsList.query.get_or_404(needs_list_id)
    
    try:
        needs_list.status = 'Rejected'
        needs_list.reviewed_by = current_user.email
        needs_list.reviewed_at = datetime.now()
        needs_list.review_notes = request.form.get('review_notes', '')
        needs_list.updated_at = datetime.now()
        
        db.session.commit()
        flash(f'Needs list {needs_list.list_number} rejected', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting needs list: {str(e)}', 'danger')
    
    return redirect(url_for('needs_list.view', needs_list_id=needs_list_id))
