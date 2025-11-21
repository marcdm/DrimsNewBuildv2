"""
Dashboard Blueprint - Role-Based Dashboards with Modern UI

Provides role-specific dashboard views matching the Relief Package preparation
UI/UX standards with summary cards, filter tabs, and modern styling.
"""

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func, desc, or_, and_
from app.db.models import (
    db, Inventory, Item, Warehouse, 
    Event, Donor, Agency, User, ReliefRqst, ReliefRequestFulfillmentLock, ReliefPkg, ReliefPkgItem
)
from app.services import relief_request_service as rr_service
from app.services.dashboard_service import DashboardService
from app.core.feature_registry import FeatureRegistry
from app.core.rbac import has_role
from datetime import datetime, timedelta
from collections import defaultdict

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """
    Main dashboard with role-based routing.
    Routes users to role-specific dashboards with modern UI.
    """
    primary_role = FeatureRegistry.get_primary_role(current_user)
    
    # Route to role-specific dashboards
    if primary_role == 'SYSTEM_ADMINISTRATOR':
        return admin_dashboard()
    elif primary_role in ['ODPEM_DG', 'ODPEM_DDG', 'ODPEM_DIR_PEOD']:
        return director_dashboard()
    elif primary_role == 'LOGISTICS_MANAGER':
        return logistics_dashboard()
    elif primary_role == 'LOGISTICS_OFFICER':
        return lo_dashboard()
    elif primary_role in ['AGENCY_DISTRIBUTOR', 'AGENCY_SHELTER']:
        return agency_dashboard()
    elif primary_role == 'INVENTORY_CLERK':
        return inventory_dashboard()
    else:
        # Default dashboard for unrecognized roles
        return general_dashboard()


@dashboard_bp.route('/logistics')
@login_required
def logistics_dashboard():
    """
    Logistics dashboard with modern UI matching Relief Package preparation.
    For Logistics Officers and Logistics Managers.
    """
    # Get dashboard data from service
    dashboard_data = DashboardService.get_dashboard_data(current_user)
    
    # Get filter parameter
    current_filter = request.args.get('filter', 'pending')
    
    # Determine if user is LM (sees global data) or LO (sees only their work)
    is_lm = has_role('LOGISTICS_MANAGER')
    is_lo = has_role('LOGISTICS_OFFICER') and not is_lm
    
    # Query fulfillment requests
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_
    
    base_query = ReliefRqst.query.options(
        joinedload(ReliefRqst.agency),
        joinedload(ReliefRqst.items),
        joinedload(ReliefRqst.status),
        joinedload(ReliefRqst.fulfillment_lock).joinedload(ReliefRequestFulfillmentLock.fulfiller)
    )
    
    # For LOs: Filter to only show requests they're involved with
    if is_lo:
        base_query = base_query.outerjoin(ReliefPkg).filter(
            or_(
                ReliefRqst.create_by_id == current_user.user_name,
                ReliefRqst.action_by_id == current_user.user_name,
                ReliefPkg.create_by_id == current_user.user_name,
                ReliefPkg.update_by_id == current_user.user_name,
                ReliefRqst.fulfillment_lock.has(ReliefRequestFulfillmentLock.fulfiller_user_id == current_user.user_id)
            )
        )
    
    # Apply filters
    if current_filter == 'pending':
        requests = base_query.filter(
            ReliefRqst.status_code == rr_service.STATUS_SUBMITTED,
            ~ReliefRqst.fulfillment_lock.has()
        ).order_by(desc(ReliefRqst.request_date)).all()
    elif current_filter == 'in_progress':
        requests = base_query.filter(
            ReliefRqst.fulfillment_lock.has()
        ).order_by(desc(ReliefRqst.request_date)).all()
    elif current_filter == 'ready':
        requests = base_query.filter(
            ReliefRqst.status_code == rr_service.STATUS_PART_FILLED
        ).order_by(desc(ReliefRqst.request_date)).all()
    elif current_filter == 'completed':
        requests = base_query.filter(
            ReliefRqst.status_code == rr_service.STATUS_FILLED
        ).order_by(desc(ReliefRqst.action_dtime)).all()
    else:  # 'all'
        requests = base_query.filter(
            ReliefRqst.status_code.in_([
                rr_service.STATUS_SUBMITTED,
                rr_service.STATUS_PART_FILLED,
                rr_service.STATUS_FILLED
            ])
        ).order_by(desc(ReliefRqst.request_date)).all()
    
    # Calculate counts for filter tabs
    # LMs see global counts (supervisory), LOs see only their own work
    if is_lo:
        # Build count queries with LO filtering
        count_base = ReliefRqst.query.outerjoin(ReliefPkg).filter(
            or_(
                ReliefRqst.create_by_id == current_user.user_name,
                ReliefRqst.action_by_id == current_user.user_name,
                ReliefPkg.create_by_id == current_user.user_name,
                ReliefPkg.update_by_id == current_user.user_name,
                ReliefRqst.fulfillment_lock.has(ReliefRequestFulfillmentLock.fulfiller_user_id == current_user.user_id)
            )
        )
        
        counts = {
            'pending': count_base.filter(
                ReliefRqst.status_code == rr_service.STATUS_SUBMITTED,
                ~ReliefRqst.fulfillment_lock.has()
            ).count(),
            'in_progress': count_base.filter(
                ReliefRqst.fulfillment_lock.has()
            ).count(),
            'ready': count_base.filter(
                ReliefRqst.status_code == rr_service.STATUS_PART_FILLED
            ).count(),
            'completed': count_base.filter(
                ReliefRqst.status_code == rr_service.STATUS_FILLED
            ).count(),
        }
    else:
        # LMs see global counts
        counts = {
            'pending': ReliefRqst.query.filter(
                ReliefRqst.status_code == rr_service.STATUS_SUBMITTED,
                ~ReliefRqst.fulfillment_lock.has()
            ).count(),
            'in_progress': ReliefRqst.query.filter(
                ReliefRqst.fulfillment_lock.has()
            ).count(),
            'ready': ReliefRqst.query.filter(
                ReliefRqst.status_code == rr_service.STATUS_PART_FILLED
            ).count(),
            'completed': ReliefRqst.query.filter(
                ReliefRqst.status_code == rr_service.STATUS_FILLED
            ).count(),
        }
    
    counts['all'] = sum(counts.values())
    
    # Inventory metrics
    low_stock_count = db.session.query(Item).join(Inventory).filter(
        Item.status_code == 'A'
    ).group_by(Item.item_id).having(
        func.sum(Inventory.usable_qty) <= Item.reorder_qty
    ).count()
    
    # Total inventory count (value calculation not available - no cost field in schema)
    total_inventory_value = 0
    
    context = {
        **dashboard_data,
        'requests': requests,
        'current_filter': current_filter,
        'counts': counts,
        'global_counts': counts,  # For LMs: global counts; For LOs: their own counts
        'low_stock_count': low_stock_count,
        'total_inventory_value': total_inventory_value,
        'STATUS_SUBMITTED': rr_service.STATUS_SUBMITTED,
        'STATUS_PART_FILLED': rr_service.STATUS_PART_FILLED,
        'STATUS_FILLED': rr_service.STATUS_FILLED,
        'is_lo': is_lo,
        'is_lm': is_lm,
    }
    
    return render_template('dashboard/logistics.html', **context)


@dashboard_bp.route('/agency')
@login_required
def agency_dashboard():
    """
    Agency dashboard for relief agencies.
    Shows agency's relief requests with modern UI.
    """
    # Get dashboard data from service
    dashboard_data = DashboardService.get_dashboard_data(current_user)
    
    # Get filter parameter
    current_filter = request.args.get('filter', 'active')
    
    # Query agency's requests
    from sqlalchemy.orm import joinedload
    
    base_query = ReliefRqst.query.options(
        joinedload(ReliefRqst.items),
        joinedload(ReliefRqst.status),
        joinedload(ReliefRqst.eligible_event)
    ).filter_by(agency_id=current_user.agency_id)
    
    # Apply filters
    if current_filter == 'draft':
        requests = base_query.filter_by(status_code=0).order_by(desc(ReliefRqst.create_dtime)).all()
    elif current_filter == 'pending':
        requests = base_query.filter_by(status_code=1).order_by(desc(ReliefRqst.request_date)).all()
    elif current_filter == 'approved':
        requests = base_query.filter(
            ReliefRqst.status_code.in_([3, 5])
        ).order_by(desc(ReliefRqst.review_dtime)).all()
    elif current_filter == 'completed':
        requests = base_query.filter_by(status_code=7).order_by(desc(ReliefRqst.action_dtime)).all()
    else:  # 'active' - default
        requests = base_query.filter(
            ReliefRqst.status_code.in_([0, 1, 3, 5])
        ).order_by(desc(ReliefRqst.create_dtime)).all()
    
    # Calculate counts
    global_counts = {
        'draft': base_query.filter_by(status_code=0).count(),
        'pending': base_query.filter_by(status_code=1).count(),
        'approved': base_query.filter(ReliefRqst.status_code.in_([3, 5])).count(),
        'completed': base_query.filter_by(status_code=7).count(),
    }
    global_counts['active'] = global_counts['draft'] + global_counts['pending'] + global_counts['approved']
    
    context = {
        **dashboard_data,
        'requests': requests,
        'current_filter': current_filter,
        'global_counts': global_counts,
        'counts': global_counts,
    }
    
    return render_template('dashboard/agency.html', **context)


@dashboard_bp.route('/director')
@login_required
def director_dashboard():
    """
    Director dashboard for ODPEM executives.
    Shows eligibility review queue with modern UI.
    """
    # Get dashboard data from service
    dashboard_data = DashboardService.get_dashboard_data(current_user)
    
    # Get filter parameter
    current_filter = request.args.get('filter', 'pending')
    
    # Query requests
    from sqlalchemy.orm import joinedload
    
    base_query = ReliefRqst.query.options(
        joinedload(ReliefRqst.agency),
        joinedload(ReliefRqst.items),
        joinedload(ReliefRqst.status),
        joinedload(ReliefRqst.eligible_event)
    )
    
    # Apply filters
    if current_filter == 'pending':
        requests = base_query.filter_by(status_code=1).order_by(desc(ReliefRqst.request_date)).all()
    elif current_filter == 'approved':
        requests = base_query.filter_by(status_code=3).order_by(desc(ReliefRqst.review_dtime)).all()
    elif current_filter == 'in_progress':
        requests = base_query.filter(
            ReliefRqst.status_code.in_([1, 3, 5])
        ).order_by(desc(ReliefRqst.request_date)).all()
    elif current_filter == 'completed':
        requests = base_query.filter_by(status_code=7).order_by(desc(ReliefRqst.action_dtime)).all()
    else:  # 'all'
        requests = base_query.order_by(desc(ReliefRqst.request_date)).all()
    
    # Calculate counts
    global_counts = {
        'pending': base_query.filter_by(status_code=1).count(),
        'approved': base_query.filter_by(status_code=3).count(),
        'in_progress': base_query.filter(ReliefRqst.status_code.in_([1, 3, 5])).count(),
        'completed': base_query.filter_by(status_code=7).count(),
    }
    global_counts['all'] = base_query.count()
    
    context = {
        **dashboard_data,
        'requests': requests,
        'current_filter': current_filter,
        'global_counts': global_counts,
        'counts': global_counts,
    }
    
    return render_template('dashboard/director.html', **context)


@dashboard_bp.route('/admin')
@login_required
def admin_dashboard():
    """
    System administrator dashboard with system-wide metrics.
    """
    dashboard_data = DashboardService.get_dashboard_data(current_user)
    
    # System metrics
    total_users = User.query.count()
    total_agencies = Agency.query.filter_by(status_code='A').count()
    total_warehouses = Warehouse.query.filter_by(status_code='A').count()
    total_items = Item.query.filter_by(status_code='A').count()
    total_events = Event.query.filter_by(status_code='A').count()
    
    # Recent activity
    recent_requests = ReliefRqst.query.order_by(desc(ReliefRqst.create_dtime)).limit(10).all()
    recent_users = User.query.order_by(desc(User.create_dtime)).limit(5).all()
    
    context = {
        **dashboard_data,
        'total_users': total_users,
        'total_agencies': total_agencies,
        'total_warehouses': total_warehouses,
        'total_items': total_items,
        'total_events': total_events,
        'recent_requests': recent_requests,
        'recent_users': recent_users,
    }
    
    return render_template('dashboard/admin.html', **context)


@dashboard_bp.route('/inventory')
@login_required
def inventory_dashboard():
    """
    Inventory clerk dashboard focused on stock management.
    """
    dashboard_data = DashboardService.get_dashboard_data(current_user)
    
    # Inventory metrics
    low_stock_items = db.session.query(
        Item.item_id, 
        Item.item_name,
        func.sum(Inventory.usable_qty).label('total_qty'),
        Item.reorder_qty
    ).join(Inventory).filter(
        Item.status_code == 'A'
    ).group_by(
        Item.item_id, Item.item_name, Item.reorder_qty
    ).having(
        func.sum(Inventory.usable_qty) <= Item.reorder_qty
    ).limit(10).all()
    
    context = {
        **dashboard_data,
        'low_stock_items': low_stock_items,
    }
    
    return render_template('dashboard/inventory.html', **context)


@dashboard_bp.route('/general')
@login_required
def general_dashboard():
    """
    General dashboard for users without specific role dashboards.
    """
    dashboard_data = DashboardService.get_dashboard_data(current_user)
    
    context = {
        **dashboard_data,
    }
    
    return render_template('dashboard/general.html', **context)


@dashboard_bp.route('/lo')
@login_required
def lo_dashboard():
    """
    Logistics Officer-specific dashboard with charts and activity metrics.
    Shows only data related to the current LO's work.
    """
    from app.core.rbac import is_logistics_officer
    if not is_logistics_officer():
        from flask import flash, redirect, url_for, abort
        abort(403)
    
    current_user_name = current_user.user_name
    now = datetime.now()
    
    # Date ranges
    today = now.date()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    # ========== KPI METRICS ==========
    
    # Total relief requests the LO has worked on (via packages they created/updated)
    total_requests_worked = db.session.query(
        func.count(func.distinct(ReliefPkg.reliefrqst_id))
    ).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        )
    ).scalar() or 0
    
    # Relief requests prepared in last 7 days
    # Count distinct requests where LO's last activity (create or update by them) was within the window
    # Use CASE to select timestamp based on what the LO did:
    #  - If LO updated: use update_dtime
    #  - If LO created but didn't update: use create_dtime
    #  - This ensures we only count packages the LO actually worked on in the time window
    from sqlalchemy import case
    
    lo_activity_timestamp = case(
        (and_(ReliefPkg.update_by_id == current_user_name, ReliefPkg.update_dtime.isnot(None)), ReliefPkg.update_dtime),
        (ReliefPkg.create_by_id == current_user_name, ReliefPkg.create_dtime),
        else_=None  # If LO didn't create or update, don't count
    )
    
    requests_last_7_days = db.session.query(
        func.count(func.distinct(ReliefPkg.reliefrqst_id))
    ).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        ),
        lo_activity_timestamp.isnot(None),  # Ensure valid timestamp
        lo_activity_timestamp >= seven_days_ago
    ).scalar() or 0
    
    # Relief requests prepared in last 30 days (using same logic)
    requests_last_30_days = db.session.query(
        func.count(func.distinct(ReliefPkg.reliefrqst_id))
    ).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        ),
        lo_activity_timestamp.isnot(None),  # Ensure valid timestamp
        lo_activity_timestamp >= thirty_days_ago
    ).scalar() or 0
    
    # Total packages created/updated by LO
    total_packages = ReliefPkg.query.filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        )
    ).count()
    
    # Total items allocated by LO (sum of all item quantities in packages LO worked on)
    total_items_allocated = db.session.query(
        func.coalesce(func.sum(ReliefPkgItem.item_qty), 0)
    ).join(ReliefPkg).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        )
    ).scalar() or 0
    
    # ========== PACKAGE STATUS BREAKDOWN ==========
    
    # Count packages by status that LO worked on
    package_statuses = db.session.query(
        ReliefPkg.status_code,
        func.count(ReliefPkg.reliefpkg_id).label('count')
    ).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        )
    ).group_by(ReliefPkg.status_code).all()
    
    # Map status codes to labels (using actual package status codes)
    status_labels_map = {
        'P': 'Pending (Being Prepared)',
        'D': 'Dispatched (Approved)',
        'C': 'Closed (Received)',
        'X': 'Cancelled'
    }
    
    status_breakdown = {
        'labels': [],
        'data': [],
        'total': 0
    }
    
    for status_code, count in package_statuses:
        status_breakdown['labels'].append(status_labels_map.get(status_code, status_code))
        status_breakdown['data'].append(count)
        status_breakdown['total'] += count
    
    # ========== ACTIVITY TIMELINE (Last 14 days) ==========
    
    fourteen_days_ago = now - timedelta(days=14)
    
    # Query packages created by day in last 14 days
    daily_packages = db.session.query(
        func.date(ReliefPkg.create_dtime).label('date'),
        func.count(ReliefPkg.reliefpkg_id).label('count')
    ).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        ),
        ReliefPkg.create_dtime >= fourteen_days_ago
    ).group_by(func.date(ReliefPkg.create_dtime)).all()
    
    # Build complete timeline with zeros for missing days
    timeline_data = defaultdict(int)
    for pkg_date, count in daily_packages:
        timeline_data[pkg_date.strftime('%Y-%m-%d')] = count
    
    # Fill in all 14 days
    timeline_labels = []
    timeline_values = []
    for i in range(13, -1, -1):  # 14 days, newest first
        day = (now - timedelta(days=i)).date()
        day_str = day.strftime('%Y-%m-%d')
        timeline_labels.append(day.strftime('%b %d'))
        timeline_values.append(timeline_data.get(day_str, 0))
    
    # ========== TOP ITEMS ALLOCATED ==========
    
    top_items = db.session.query(
        Item.item_name,
        func.sum(ReliefPkgItem.item_qty).label('total_qty')
    ).join(ReliefPkgItem).join(ReliefPkg).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        )
    ).group_by(Item.item_name).order_by(desc('total_qty')).limit(10).all()
    
    top_items_data = {
        'labels': [item[0] for item in top_items],
        'data': [float(item[1]) for item in top_items]
    }
    
    # ========== RECENT ACTIVITY ==========
    
    recent_packages = ReliefPkg.query.options(
        db.joinedload(ReliefPkg.relief_request).joinedload(ReliefRqst.agency)
    ).filter(
        or_(
            ReliefPkg.create_by_id == current_user_name,
            ReliefPkg.update_by_id == current_user_name
        )
    ).order_by(desc(ReliefPkg.create_dtime)).limit(5).all()
    
    context = {
        # KPIs
        'total_requests_worked': total_requests_worked,
        'total_packages': total_packages,
        'total_items_allocated': int(total_items_allocated),
        'requests_last_7_days': requests_last_7_days,
        'requests_last_30_days': requests_last_30_days,
        
        # Charts data
        'status_breakdown': status_breakdown,
        'timeline_labels': timeline_labels,
        'timeline_values': timeline_values,
        'top_items': top_items_data,
        
        # Recent activity
        'recent_packages': recent_packages,
        
        # Status labels for rendering
        'status_labels_map': status_labels_map,
        
        # Service constants
        'PKG_STATUS_PENDING': rr_service.PKG_STATUS_PENDING,
        'PKG_STATUS_DISPATCHED': rr_service.PKG_STATUS_DISPATCHED,
        'PKG_STATUS_CLOSED': rr_service.PKG_STATUS_CLOSED
    }
    
    return render_template('dashboard/lo.html', **context)
