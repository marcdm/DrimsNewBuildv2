"""
Inventory Reservation Service

Manages inventory reservations during package preparation to prevent
double-allocation across concurrent package fulfillment operations.

Key Functions:
- reserve_inventory(): Updates reserved_qty when saving draft allocations
- release_inventory(): Releases reserved_qty when canceling or abandoning
- commit_inventory(): Converts reservations to actual deductions on dispatch
"""

from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from sqlalchemy.exc import SQLAlchemyError
from app.db import db
from app.db.models import Inventory, ReliefPkgItem, ItemBatch


def get_current_reservations(reliefrqst_id: int) -> Dict[Tuple[int, int], Decimal]:
    """
    Get current inventory reservations for a relief request.
    
    Returns: {(item_id, inventory_id): reserved_qty}
    Note: inventory_id IS the warehouse_id (composite PK pattern)
    """
    # Get the parent ReliefPkg first to get the reliefrqst_id mapping
    from app.db.models import ReliefPkg
    pkg = ReliefPkg.query.filter_by(reliefrqst_id=reliefrqst_id).first()
    
    if not pkg:
        return {}
    
    pkg_items = ReliefPkgItem.query.filter_by(reliefpkg_id=pkg.reliefpkg_id).all()
    
    reservations = {}
    for pkg_item in pkg_items:
        if pkg_item.item_qty and pkg_item.item_qty > 0:
            # inventory_id IS the warehouse_id (composite PK: inventory_id, item_id)
            # fr_inventory_id is the warehouse_id
            key = (pkg_item.item_id, pkg_item.fr_inventory_id)
            reservations[key] = pkg_item.item_qty
    
    return reservations


def reserve_inventory(reliefrqst_id: int, new_allocations: List[Dict], old_allocations: Optional[Dict[Tuple[int, int], Decimal]] = None) -> Tuple[bool, str]:
    """
    Reserve inventory for package allocations.
    
    Updates reserved_qty in inventory table based on difference between
    current and new allocations. Validates that reservations don't exceed
    available inventory.
    
    Args:
        reliefrqst_id: Relief request ID
        new_allocations: List of {item_id, warehouse_id, allocated_qty}
        old_allocations: Dict of {(item_id, inventory_id): allocated_qty} from before update
                        If None, queries database for current reservations
    
    Returns:
        (success, error_message)
    
    Note: inventory_id IS the warehouse_id (composite PK pattern)
    """
    try:
        # Use provided old allocations or query from database
        if old_allocations is None:
            current_reservations = get_current_reservations(reliefrqst_id)
        else:
            current_reservations = old_allocations
        
        # Build new reservations map
        new_reservations = {}
        for alloc in new_allocations:
            if alloc['allocated_qty'] > 0:
                # warehouse_id is stored as inventory_id in the composite PK
                key = (alloc['item_id'], alloc['warehouse_id'])
                new_reservations[key] = alloc['allocated_qty']
        
        # Calculate differences and update inventory
        all_keys = set(current_reservations.keys()) | set(new_reservations.keys())
        
        for key in all_keys:
            item_id, inventory_id = key  # inventory_id IS the warehouse_id
            current_qty = current_reservations.get(key, Decimal('0'))
            new_qty = new_reservations.get(key, Decimal('0'))
            difference = new_qty - current_qty
            
            if difference != 0:
                # Update inventory reserved_qty using composite PK
                inventory = Inventory.query.filter_by(
                    item_id=item_id,
                    inventory_id=inventory_id,  # Use inventory_id, not warehouse_id
                    status_code='A'
                ).with_for_update().first()
                
                if not inventory:
                    # If we're trying to INCREASE reservations (new allocation), this is an error
                    if difference > 0:
                        return False, f'No active inventory found for item {item_id} at warehouse {inventory_id}'
                    
                    # If we're trying to DECREASE reservations (releasing old allocation),
                    # check for inactive inventory and clean it up
                    else:
                        # Query for inactive inventory to clean up stale reservations
                        inactive_inventory = Inventory.query.filter_by(
                            item_id=item_id,
                            inventory_id=inventory_id
                        ).with_for_update().first()
                        
                        if inactive_inventory and inactive_inventory.status_code != 'A':
                            # Found inactive inventory with stale reservation - clean it up
                            from flask import current_app
                            current_app.logger.warning(
                                f'Releasing reservation from inactive inventory: '
                                f'item_id={item_id}, warehouse_id={inventory_id}, '
                                f'status={inactive_inventory.status_code}, '
                                f'releasing {abs(difference)} units'
                            )
                            # Reset reserved_qty to prevent data integrity issues
                            new_reserved = inactive_inventory.reserved_qty + difference
                            inactive_inventory.reserved_qty = max(Decimal('0'), new_reserved)
                        # If no inventory record exists at all, skip silently
                        continue
                
                # Calculate new reserved quantity
                new_reserved = inventory.reserved_qty + difference
                
                # Validate: reserved_qty + difference must not exceed usable_qty
                if new_reserved < 0:
                    # Handle inconsistency: trying to release more than is reserved
                    # This can happen if reservations were released but package items still exist
                    # Just set to 0 instead of failing
                    inventory.reserved_qty = Decimal('0')
                elif new_reserved > inventory.usable_qty:
                    available = inventory.usable_qty - inventory.reserved_qty
                    return False, f'Cannot reserve {difference} units at warehouse {inventory.warehouse.warehouse_name} - only {available} available'
                else:
                    # Normal case: update reserved quantity
                    inventory.reserved_qty = new_reserved
        
        return True, ''
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return False, f'Database error during reservation: {str(e)}'


def release_all_reservations(reliefrqst_id: int) -> Tuple[bool, str]:
    """
    Release all inventory reservations for a relief request.
    
    Called when:
    - User cancels package preparation
    - Lock expires without saving
    - Package is abandoned
    
    Args:
        reliefrqst_id: Relief request ID
    
    Returns:
        (success, error_message)
    
    Note: inventory_id IS the warehouse_id (composite PK pattern)
    """
    try:
        current_reservations = get_current_reservations(reliefrqst_id)
        
        for (item_id, inventory_id), reserved_qty in current_reservations.items():
            if reserved_qty > 0:
                # Use inventory_id (which IS the warehouse_id) in composite PK
                inventory = Inventory.query.filter_by(
                    item_id=item_id,
                    inventory_id=inventory_id,  # Use inventory_id, not warehouse_id
                    status_code='A'
                ).with_for_update().first()
                
                if inventory:
                    inventory.reserved_qty = max(Decimal('0'), inventory.reserved_qty - reserved_qty)
        
        return True, ''
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return False, f'Database error during release: {str(e)}'


def commit_inventory(reliefrqst_id: int) -> Tuple[bool, str]:
    """
    Commit inventory allocations on package dispatch at BATCH LEVEL.
    
    Converts reservations to actual deductions:
    - Decreases batch.usable_qty by allocated amounts for each batch
    - Decreases batch.reserved_qty by allocated amounts for each batch
    - Updates warehouse-level inventory.usable_qty and inventory.reserved_qty
    
    Called when Logistics Manager sends package for dispatch.
    
    Args:
        reliefrqst_id: Relief request ID
    
    Returns:
        (success, error_message)
    """
    try:
        # Get all package items with their batch-level allocations
        from app.db.models import ReliefPkg
        pkg = ReliefPkg.query.filter_by(reliefrqst_id=reliefrqst_id).first()
        
        if not pkg:
            return False, 'No package found for this relief request'
        
        pkg_items = ReliefPkgItem.query.filter_by(reliefpkg_id=pkg.reliefpkg_id).all()
        
        # Track warehouse-level changes for updating Inventory table
        warehouse_changes = {}  # {(item_id, inventory_id): total_allocated_qty}
        
        # Process each batch allocation
        for pkg_item in pkg_items:
            if pkg_item.item_qty and pkg_item.item_qty > 0:
                # Deduct from the specific batch
                batch = ItemBatch.query.filter_by(
                    batch_id=pkg_item.batch_id,
                    inventory_id=pkg_item.fr_inventory_id,
                    item_id=pkg_item.item_id
                ).with_for_update().first()
                
                if not batch:
                    return False, f'Batch {pkg_item.batch_id} not found for item {pkg_item.item_id}'
                
                # Validate sufficient batch quantity
                if batch.usable_qty < pkg_item.item_qty:
                    from app.db.models import Warehouse
                    warehouse = Warehouse.query.get(pkg_item.fr_inventory_id)
                    warehouse_name = warehouse.warehouse_name if warehouse else f'ID {pkg_item.fr_inventory_id}'
                    return False, f'Insufficient inventory at warehouse {warehouse_name}: need {pkg_item.item_qty}, have {batch.usable_qty}'
                
                # Commit batch allocation
                batch.usable_qty -= pkg_item.item_qty
                batch.reserved_qty = max(Decimal('0'), batch.reserved_qty - pkg_item.item_qty)
                
                # Track warehouse-level changes
                key = (pkg_item.item_id, pkg_item.fr_inventory_id)
                if key not in warehouse_changes:
                    warehouse_changes[key] = Decimal('0')
                warehouse_changes[key] += pkg_item.item_qty
        
        # Update warehouse-level inventory
        for (item_id, inventory_id), total_qty in warehouse_changes.items():
            inventory = Inventory.query.filter_by(
                item_id=item_id,
                inventory_id=inventory_id,
                status_code='A'
            ).with_for_update().first()
            
            if inventory:
                inventory.usable_qty -= total_qty
                inventory.reserved_qty = max(Decimal('0'), inventory.reserved_qty - total_qty)
        
        return True, ''
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return False, f'Database error during commit: {str(e)}'
