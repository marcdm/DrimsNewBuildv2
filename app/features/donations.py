"""
Donation Management Routes
Accept and process donations from donors with full item tracking.

Access: LOGISTICS_MANAGER, LOGISTICS_OFFICER only
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.db import db
from app.db.models import Donation, DonationItem, Donor, Event, Custodian, Item, UnitOfMeasure
from app.core.audit import add_audit_fields, add_verify_fields
from app.core.decorators import feature_required

donations_bp = Blueprint('donations', __name__, url_prefix='/donations')


def _get_adhoc_event():
    """Get the ADHOC event for default selection"""
    return Event.query.filter(Event.event_name.ilike('%ADHOC%')).first()


@donations_bp.route('/')
@login_required
@feature_required('donation_management')
def list_donations():
    """List all donations with filter and search capabilities"""
    status_filter = request.args.get('status', 'all')
    donor_filter = request.args.get('donor_id', type=int)
    event_filter = request.args.get('event_id', type=int)
    search_query = request.args.get('search', '').strip()
    
    query = Donation.query
    
    if status_filter != 'all':
        query = query.filter_by(status_code=status_filter.upper())
    
    if donor_filter:
        query = query.filter_by(donor_id=donor_filter)
    
    if event_filter:
        query = query.filter_by(event_id=event_filter)
    
    if search_query:
        query = query.filter(
            db.or_(
                Donation.donation_desc.ilike(f'%{search_query}%'),
                Donation.comments_text.ilike(f'%{search_query}%')
            )
        )
    
    donations = query.order_by(Donation.received_date.desc()).all()
    
    status_counts = {
        'all': Donation.query.count(),
        'E': Donation.query.filter_by(status_code='E').count(),
        'V': Donation.query.filter_by(status_code='V').count(),
        'P': Donation.query.filter_by(status_code='P').count()
    }
    
    donors = Donor.query.order_by(Donor.donor_name).all()
    events = Event.query.filter_by(status_code='A').order_by(Event.event_name).all()
    
    return render_template('donations/list.html', 
                         donations=donations,
                         status_counts=status_counts,
                         current_filter=status_filter,
                         donor_filter=donor_filter,
                         event_filter=event_filter,
                         search_query=search_query,
                         donors=donors,
                         events=events)


@donations_bp.route('/create', methods=['GET', 'POST'])
@login_required
@feature_required('donation_management')
def create_donation():
    """Create new donation header"""
    if request.method == 'POST':
        try:
            donor_id = request.form.get('donor_id')
            event_id = request.form.get('event_id')
            custodian_id = request.form.get('custodian_id')
            donation_desc = request.form.get('donation_desc', '').strip()
            received_date_str = request.form.get('received_date')
            comments_text = request.form.get('comments_text', '').strip()
            
            errors = []
            
            if not donor_id:
                errors.append('Donor is required')
            if not event_id:
                errors.append('Event is required')
            if not custodian_id:
                errors.append('Custodian is required')
            if not donation_desc:
                errors.append('Donation description is required')
            if not received_date_str:
                errors.append('Received date is required')
            
            if received_date_str:
                received_date = datetime.strptime(received_date_str, '%Y-%m-%d').date()
                if received_date > date.today():
                    errors.append('Received date cannot be in the future')
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                donors = Donor.query.order_by(Donor.donor_name).all()
                events = Event.query.filter_by(status_code='A').order_by(Event.event_name).all()
                custodians = Custodian.query.order_by(Custodian.custodian_name).all()
                adhoc_event = _get_adhoc_event()
                return render_template('donations/create.html', 
                                     donors=donors, 
                                     events=events,
                                     custodians=custodians,
                                     adhoc_event=adhoc_event,
                                     today=date.today().isoformat(),
                                     form_data=request.form)
            
            donation = Donation()
            donation.donor_id = int(donor_id)
            donation.event_id = int(event_id)
            donation.custodian_id = int(custodian_id)
            donation.donation_desc = donation_desc.upper()
            donation.received_date = received_date
            donation.status_code = 'E'
            donation.comments_text = comments_text.upper() if comments_text else None
            
            add_audit_fields(donation, current_user, is_new=True)
            
            db.session.add(donation)
            db.session.commit()
            
            flash(f'Donation #{donation.donation_id} created successfully. Now add donation items.', 'success')
            return redirect(url_for('donations.view_donation', donation_id=donation.donation_id))
            
        except IntegrityError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('donations.create_donation'))
    
    donors = Donor.query.order_by(Donor.donor_name).all()
    events = Event.query.filter_by(status_code='A').order_by(Event.event_name).all()
    custodians = Custodian.query.order_by(Custodian.custodian_name).all()
    adhoc_event = _get_adhoc_event()
    
    if not donors:
        flash('No donors available. Please create a donor first.', 'warning')
        return redirect(url_for('donations.list_donations'))
    
    if not custodians:
        flash('No custodians available. Please create a custodian first.', 'warning')
        return redirect(url_for('donations.list_donations'))
    
    return render_template('donations/create.html', 
                         donors=donors, 
                         events=events,
                         custodians=custodians,
                         adhoc_event=adhoc_event,
                         today=date.today().isoformat())


@donations_bp.route('/<int:donation_id>')
@login_required
@feature_required('donation_management')
def view_donation(donation_id):
    """View donation details including all items"""
    donation = Donation.query.get_or_404(donation_id)
    
    items_with_details = []
    for donation_item in donation.items:
        items_with_details.append({
            'item': donation_item.item,
            'item_qty': donation_item.item_qty,
            'uom': donation_item.uom,
            'location_name': donation_item.location_name,
            'status_code': donation_item.status_code,
            'comments_text': donation_item.comments_text,
            'version_nbr': donation_item.version_nbr
        })
    
    return render_template('donations/view.html', 
                         donation=donation,
                         items=items_with_details)


@donations_bp.route('/<int:donation_id>/edit', methods=['GET', 'POST'])
@login_required
@feature_required('donation_management')
def edit_donation(donation_id):
    """Edit donation header (optimistic locking)"""
    donation = Donation.query.get_or_404(donation_id)
    
    if request.method == 'POST':
        try:
            version_nbr = int(request.form.get('version_nbr', 0))
            
            if version_nbr != donation.version_nbr:
                flash('This donation has been modified by another user. Please reload and try again.', 'danger')
                return redirect(url_for('donations.edit_donation', donation_id=donation_id))
            
            donor_id = request.form.get('donor_id')
            event_id = request.form.get('event_id')
            custodian_id = request.form.get('custodian_id')
            donation_desc = request.form.get('donation_desc', '').strip()
            received_date_str = request.form.get('received_date')
            status_code = request.form.get('status_code')
            comments_text = request.form.get('comments_text', '').strip()
            
            errors = []
            
            if not donor_id:
                errors.append('Donor is required')
            if not event_id:
                errors.append('Event is required')
            if not custodian_id:
                errors.append('Custodian is required')
            if not donation_desc:
                errors.append('Donation description is required')
            if not received_date_str:
                errors.append('Received date is required')
            if not status_code or status_code not in ['E', 'V', 'P']:
                errors.append('Valid status code is required')
            
            if received_date_str:
                received_date = datetime.strptime(received_date_str, '%Y-%m-%d').date()
                if received_date > date.today():
                    errors.append('Received date cannot be in the future')
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                donors = Donor.query.order_by(Donor.donor_name).all()
                events = Event.query.filter_by(status_code='A').order_by(Event.event_name).all()
                custodians = Custodian.query.order_by(Custodian.custodian_name).all()
                return render_template('donations/edit.html', 
                                     donation=donation,
                                     donors=donors,
                                     events=events,
                                     custodians=custodians,
                                     today=date.today().isoformat(),
                                     form_data=request.form)
            
            donation.donor_id = int(donor_id)
            donation.event_id = int(event_id)
            donation.custodian_id = int(custodian_id)
            donation.donation_desc = donation_desc.upper()
            old_status = donation.status_code
            
            donation.received_date = received_date
            donation.status_code = status_code
            donation.comments_text = comments_text.upper() if comments_text else None
            
            add_audit_fields(donation, current_user, is_new=False)
            
            if status_code in ['V', 'P'] and old_status != status_code:
                add_verify_fields(donation, current_user)
            
            db.session.commit()
            
            flash(f'Donation #{donation.donation_id} updated successfully', 'success')
            return redirect(url_for('donations.view_donation', donation_id=donation.donation_id))
            
        except StaleDataError:
            db.session.rollback()
            flash('This donation has been modified by another user. Please reload and try again.', 'danger')
            return redirect(url_for('donations.edit_donation', donation_id=donation_id))
        except IntegrityError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('donations.edit_donation', donation_id=donation_id))
    
    donors = Donor.query.order_by(Donor.donor_name).all()
    custodians = Custodian.query.order_by(Custodian.custodian_name).all()
    
    events = Event.query.filter_by(status_code='A').order_by(Event.event_name).all()
    if donation.event not in events:
        events = [donation.event] + events
    
    return render_template('donations/edit.html', 
                         donation=donation,
                         donors=donors,
                         events=events,
                         custodians=custodians,
                         today=date.today().isoformat())


@donations_bp.route('/<int:donation_id>/delete', methods=['POST'])
@login_required
@feature_required('donation_management')
def delete_donation(donation_id):
    """Delete donation (only if no items exist)"""
    donation = Donation.query.get_or_404(donation_id)
    
    if donation.items:
        flash('Cannot delete donation with existing items. Remove all items first.', 'danger')
        return redirect(url_for('donations.view_donation', donation_id=donation_id))
    
    try:
        db.session.delete(donation)
        db.session.commit()
        flash(f'Donation #{donation_id} deleted successfully', 'success')
        return redirect(url_for('donations.list_donations'))
    except IntegrityError as e:
        db.session.rollback()
        flash(f'Cannot delete donation: {str(e)}', 'danger')
        return redirect(url_for('donations.view_donation', donation_id=donation_id))


@donations_bp.route('/<int:donation_id>/items/add', methods=['GET', 'POST'])
@login_required
@feature_required('donation_management')
def add_donation_item(donation_id):
    """Add item to donation"""
    donation = Donation.query.get_or_404(donation_id)
    
    if request.method == 'POST':
        try:
            item_id = request.form.get('item_id')
            item_qty = request.form.get('item_qty')
            uom_code = request.form.get('uom_code')
            location_name = request.form.get('location_name', '').strip()
            comments_text = request.form.get('comments_text', '').strip()
            
            errors = []
            
            if not item_id:
                errors.append('Item is required')
            if not item_qty:
                errors.append('Quantity is required')
            elif Decimal(item_qty) <= 0:
                errors.append('Quantity must be greater than 0')
            if not uom_code:
                errors.append('Unit of measure is required')
            if not location_name:
                errors.append('Location is required')
            
            if item_id:
                existing = DonationItem.query.filter_by(
                    donation_id=donation_id,
                    item_id=int(item_id)
                ).first()
                if existing:
                    errors.append('This item is already in the donation. Edit the existing item instead.')
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                items = Item.query.order_by(Item.item_name).all()
                uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_code).all()
                return render_template('donations/add_item.html',
                                     donation=donation,
                                     items=items,
                                     uoms=uoms,
                                     form_data=request.form)
            
            donation_item = DonationItem()
            donation_item.donation_id = donation_id
            donation_item.item_id = int(item_id)
            donation_item.item_qty = Decimal(item_qty)
            donation_item.uom_code = uom_code
            donation_item.location_name = location_name.upper()
            donation_item.status_code = 'V'
            donation_item.comments_text = comments_text.upper() if comments_text else None
            
            add_audit_fields(donation_item, current_user, is_new=True)
            
            if donation_item.status_code == 'V':
                add_verify_fields(donation_item, current_user)
            
            db.session.add(donation_item)
            db.session.commit()
            
            flash(f'Item added to donation successfully', 'success')
            return redirect(url_for('donations.view_donation', donation_id=donation_id))
            
        except IntegrityError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('donations.add_donation_item', donation_id=donation_id))
    
    items = Item.query.order_by(Item.item_name).all()
    uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_code).all()
    
    if not items:
        flash('No items available. Please create items first.', 'warning')
        return redirect(url_for('donations.view_donation', donation_id=donation_id))
    
    return render_template('donations/add_item.html',
                         donation=donation,
                         items=items,
                         uoms=uoms)


@donations_bp.route('/<int:donation_id>/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@feature_required('donation_management')
def edit_donation_item(donation_id, item_id):
    """Edit donation item (optimistic locking)"""
    donation = Donation.query.get_or_404(donation_id)
    donation_item = DonationItem.query.get_or_404((donation_id, item_id))
    
    if request.method == 'POST':
        try:
            version_nbr = int(request.form.get('version_nbr', 0))
            
            if version_nbr != donation_item.version_nbr:
                flash('This item has been modified by another user. Please reload and try again.', 'danger')
                return redirect(url_for('donations.edit_donation_item', 
                                      donation_id=donation_id, 
                                      item_id=item_id))
            
            item_qty = request.form.get('item_qty')
            uom_code = request.form.get('uom_code')
            location_name = request.form.get('location_name', '').strip()
            status_code = request.form.get('status_code')
            comments_text = request.form.get('comments_text', '').strip()
            
            errors = []
            
            if not item_qty:
                errors.append('Quantity is required')
            elif Decimal(item_qty) <= 0:
                errors.append('Quantity must be greater than 0')
            if not uom_code:
                errors.append('Unit of measure is required')
            if not location_name:
                errors.append('Location is required')
            if not status_code or status_code not in ['P', 'V']:
                errors.append('Valid status code is required')
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_code).all()
                return render_template('donations/edit_item.html',
                                     donation=donation,
                                     donation_item=donation_item,
                                     uoms=uoms,
                                     form_data=request.form)
            
            donation_item.item_qty = Decimal(item_qty)
            donation_item.uom_code = uom_code
            old_status = donation_item.status_code
            
            donation_item.location_name = location_name.upper()
            donation_item.status_code = status_code
            donation_item.comments_text = comments_text.upper() if comments_text else None
            
            add_audit_fields(donation_item, current_user, is_new=False)
            
            if status_code == 'V' and old_status != status_code:
                add_verify_fields(donation_item, current_user)
            
            db.session.commit()
            
            flash(f'Donation item updated successfully', 'success')
            return redirect(url_for('donations.view_donation', donation_id=donation_id))
            
        except StaleDataError:
            db.session.rollback()
            flash('This item has been modified by another user. Please reload and try again.', 'danger')
            return redirect(url_for('donations.edit_donation_item', 
                                  donation_id=donation_id, 
                                  item_id=item_id))
        except IntegrityError as e:
            db.session.rollback()
            flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('donations.edit_donation_item', 
                                  donation_id=donation_id, 
                                  item_id=item_id))
    
    uoms = UnitOfMeasure.query.order_by(UnitOfMeasure.uom_code).all()
    
    return render_template('donations/edit_item.html',
                         donation=donation,
                         donation_item=donation_item,
                         uoms=uoms)


@donations_bp.route('/<int:donation_id>/items/<int:item_id>/delete', methods=['POST'])
@login_required
@feature_required('donation_management')
def delete_donation_item(donation_id, item_id):
    """Delete donation item"""
    donation_item = DonationItem.query.get_or_404((donation_id, item_id))
    
    try:
        db.session.delete(donation_item)
        db.session.commit()
        flash(f'Donation item removed successfully', 'success')
        return redirect(url_for('donations.view_donation', donation_id=donation_id))
    except IntegrityError as e:
        db.session.rollback()
        flash(f'Cannot delete item: {str(e)}', 'danger')
        return redirect(url_for('donations.view_donation', donation_id=donation_id))
