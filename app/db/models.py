"""
SQLAlchemy models for DRIMS
Maps to existing database schema (no auto-create)
"""
from app.db import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import CheckConstraint

class User(UserMixin, db.Model):
    """User authentication model (DRIMS extension)"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    full_name = db.Column(db.String(200))
    role = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    organization = db.Column(db.String(200))
    job_title = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    roles = db.relationship('Role', secondary='user_role', back_populates='users')
    warehouses = db.relationship('Warehouse', secondary='user_warehouse', back_populates='users')

class Role(db.Model):
    """Role definitions for RBAC"""
    __tablename__ = 'role'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users = db.relationship('User', secondary='user_role', back_populates='roles')

class UserRole(db.Model):
    """User-Role assignment (many-to-many)"""
    __tablename__ = 'user_role'
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserWarehouse(db.Model):
    """User-Warehouse access control"""
    __tablename__ = 'user_warehouse'
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.warehouse_id'), primary_key=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    """Disaster Event (from aidmgmt-3.sql)"""
    __tablename__ = 'event'
    
    event_id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(16), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    event_name = db.Column(db.String(60), nullable=False)
    event_desc = db.Column(db.String(255), nullable=False)
    impact_desc = db.Column(db.Text, nullable=False)
    status_code = db.Column(db.CHAR(1), nullable=False)
    closed_date = db.Column(db.Date)
    reason_desc = db.Column(db.String(255))
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)

class Custodian(db.Model):
    """GOJ Agency (ODPEM)"""
    __tablename__ = 'custodian'
    
    custodian_id = db.Column(db.Integer, primary_key=True)
    custodian_name = db.Column(db.String(120), nullable=False)
    address1_text = db.Column(db.String(255), nullable=False)
    address2_text = db.Column(db.String(255))
    parish_code = db.Column(db.CHAR(2), db.ForeignKey('parish.parish_code'), nullable=False)
    contact_name = db.Column(db.String(50), nullable=False)
    phone_no = db.Column(db.String(20), nullable=False)
    email_text = db.Column(db.String(100))
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)

class Warehouse(db.Model):
    """Warehouse/Storage Location (from aidmgmt-3.sql)"""
    __tablename__ = 'warehouse'
    
    warehouse_id = db.Column(db.Integer, primary_key=True)
    warehouse_name = db.Column(db.Text, nullable=False)
    warehouse_type = db.Column(db.String(10), nullable=False)
    address1_text = db.Column(db.String(255), nullable=False)
    address2_text = db.Column(db.String(255))
    parish_code = db.Column(db.CHAR(2), db.ForeignKey('parish.parish_code'), nullable=False)
    contact_name = db.Column(db.String(50), nullable=False)
    phone_no = db.Column(db.String(20), nullable=False)
    email_text = db.Column(db.String(100))
    custodian_id = db.Column(db.Integer, db.ForeignKey('custodian.custodian_id'), nullable=False)
    status_code = db.Column(db.CHAR(1), nullable=False)
    reason_desc = db.Column(db.String(255))
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    parish = db.relationship('Parish', backref='warehouses')
    custodian = db.relationship('Custodian', backref='warehouses')
    users = db.relationship('User', secondary='user_warehouse', back_populates='warehouses')

class Agency(db.Model):
    """Agency (Request-only locations)"""
    __tablename__ = 'agency'
    
    agency_id = db.Column(db.Integer, primary_key=True)
    agency_name = db.Column(db.String(120), nullable=False, unique=True)
    address1_text = db.Column(db.String(255), nullable=False)
    address2_text = db.Column(db.String(255))
    parish_code = db.Column(db.CHAR(2), db.ForeignKey('parish.parish_code'), nullable=False)
    contact_name = db.Column(db.String(50), nullable=False)
    phone_no = db.Column(db.String(20), nullable=False)
    email_text = db.Column(db.String(100))
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    parish = db.relationship('Parish', backref='agencies')

class Parish(db.Model):
    """Jamaican Parish"""
    __tablename__ = 'parish'
    
    parish_code = db.Column(db.CHAR(2), primary_key=True)
    parish_name = db.Column(db.String(40), nullable=False)

class UnitOfMeasure(db.Model):
    """Unit of Measure"""
    __tablename__ = 'unitofmeasure'
    
    uom_code = db.Column(db.String(25), primary_key=True)
    uom_desc = db.Column(db.String(60), nullable=False)
    comments_text = db.Column(db.Text)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)

class ItemCategory(db.Model):
    """Item Category"""
    __tablename__ = 'itemcatg'
    
    category_code = db.Column(db.String(30), primary_key=True)
    category_desc = db.Column(db.String(60), nullable=False)
    comments_text = db.Column(db.Text)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)

class Item(db.Model):
    """Relief Item (from aidmgmt-3.sql)"""
    __tablename__ = 'item'
    
    item_id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(60), nullable=False, unique=True)
    sku_code = db.Column(db.String(30), nullable=False, unique=True)
    category_code = db.Column(db.String(30), db.ForeignKey('itemcatg.category_code'), nullable=False)
    item_desc = db.Column(db.Text, nullable=False)
    reorder_qty = db.Column(db.Numeric(12, 2), nullable=False)
    default_uom_code = db.Column(db.String(25), db.ForeignKey('unitofmeasure.uom_code'), nullable=False)
    usage_desc = db.Column(db.Text)
    storage_desc = db.Column(db.Text)
    expiration_apply_flag = db.Column(db.Boolean, nullable=False)
    comments_text = db.Column(db.Text)
    status_code = db.Column(db.CHAR(1), nullable=False)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    category = db.relationship('ItemCategory', backref='items')
    default_uom = db.relationship('UnitOfMeasure', backref='items')

class Inventory(db.Model):
    """Inventory (from aidmgmt-3.sql)"""
    __tablename__ = 'inventory'
    
    inventory_id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.warehouse_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'), nullable=False)
    usable_qty = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    reserved_qty = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    defective_qty = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    expired_qty = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    uom_code = db.Column(db.String(25), db.ForeignKey('unitofmeasure.uom_code'), nullable=False)
    last_verified_by = db.Column(db.String(20))
    last_verified_date = db.Column(db.Date)
    status_code = db.Column(db.CHAR(1), nullable=False)
    comments_text = db.Column(db.Text)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    warehouse = db.relationship('Warehouse', backref='inventories')
    item = db.relationship('Item', backref='inventories')
    uom = db.relationship('UnitOfMeasure', backref='inventories')

class Donor(db.Model):
    """Donor"""
    __tablename__ = 'donor'
    
    donor_id = db.Column(db.Integer, primary_key=True)
    donor_type = db.Column(db.CHAR(1), nullable=False)
    donor_name = db.Column(db.String(255), nullable=False, unique=True)
    org_type_desc = db.Column(db.String(30))
    address1_text = db.Column(db.String(255), nullable=False)
    address2_text = db.Column(db.String(255))
    country_id = db.Column(db.SmallInteger, default=388)
    phone_no = db.Column(db.String(20), nullable=False)
    email_text = db.Column(db.String(100))
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)

class Donation(db.Model):
    """Donation"""
    __tablename__ = 'donation'
    
    donation_id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('donor.donor_id'), nullable=False)
    donation_desc = db.Column(db.Text, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.event_id'), nullable=False)
    custodian_id = db.Column(db.Integer, db.ForeignKey('custodian.custodian_id'), nullable=False)
    received_date = db.Column(db.Date, nullable=False)
    status_code = db.Column(db.CHAR(1), nullable=False)
    comments_text = db.Column(db.Text)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    verify_by_id = db.Column(db.String(20), nullable=False)
    verify_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    donor = db.relationship('Donor', backref='donations')
    event = db.relationship('Event', backref='donations')
    custodian = db.relationship('Custodian', backref='donations')

class ReliefRqst(db.Model):
    """Relief Request / Needs List (AIDMGMT workflow)"""
    __tablename__ = 'reliefrqst'
    
    reliefrqst_id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.agency_id'), nullable=False)
    request_date = db.Column(db.Date, nullable=False)
    urgency_ind = db.Column(db.CHAR(1), nullable=False)
    status_code = db.Column(db.SmallInteger, nullable=False)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    review_by_id = db.Column(db.String(20))
    review_dtime = db.Column(db.DateTime)
    action_by_id = db.Column(db.String(20))
    action_dtime = db.Column(db.DateTime)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    agency = db.relationship('Agency', backref='relief_requests')

class ReliefRqstItem(db.Model):
    """Relief Request Item"""
    __tablename__ = 'reliefrqst_item'
    
    reliefrqst_id = db.Column(db.Integer, db.ForeignKey('reliefrqst.reliefrqst_id'), primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'), primary_key=True)
    request_qty = db.Column(db.Numeric(12, 2), nullable=False)
    issue_qty = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    urgency_ind = db.Column(db.CHAR(1), nullable=False)
    rqst_reason_desc = db.Column(db.String(255))
    required_by_date = db.Column(db.Date)
    status_code = db.Column(db.CHAR(1), nullable=False, default='R')
    status_reason_desc = db.Column(db.String(255))
    action_by_id = db.Column(db.String(20))
    action_dtime = db.Column(db.DateTime)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    relief_request = db.relationship('ReliefRqst', backref='items')
    item = db.relationship('Item', backref='request_items')

class ReliefPkg(db.Model):
    """Relief Package / Fulfilment (AIDMGMT workflow)"""
    __tablename__ = 'reliefpkg'
    
    reliefpkg_id = db.Column(db.Integer, primary_key=True)
    to_inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.inventory_id'), nullable=False)
    reliefrqst_id = db.Column(db.Integer, db.ForeignKey('reliefrqst.reliefrqst_id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    dispatch_dtime = db.Column(db.DateTime)
    transport_mode = db.Column(db.String(255))
    comments_text = db.Column(db.String(255))
    status_code = db.Column(db.CHAR(1), nullable=False)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime)
    verify_by_id = db.Column(db.String(20), nullable=False)
    verify_dtime = db.Column(db.DateTime)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    relief_request = db.relationship('ReliefRqst', backref='packages')
    to_inventory = db.relationship('Inventory', backref='relief_packages')

class ReliefPkgItem(db.Model):
    """Relief Package Item"""
    __tablename__ = 'reliefpkg_item'
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['fr_inventory_id', 'item_id'],
            ['inventory.inventory_id', 'inventory.item_id']
        ),
    )
    
    reliefpkg_id = db.Column(db.Integer, db.ForeignKey('reliefpkg.reliefpkg_id'), primary_key=True)
    fr_inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.inventory_id'), primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'), primary_key=True)
    item_qty = db.Column(db.Numeric(12, 2), nullable=False)
    uom_code = db.Column(db.String(25), db.ForeignKey('unitofmeasure.uom_code'), nullable=False)
    reason_text = db.Column(db.String(255))
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    package = db.relationship('ReliefPkg', backref='items')
    item = db.relationship('Item', backref='package_items')
    from_inventory = db.relationship('Inventory', foreign_keys=[fr_inventory_id, item_id])

class DBIntake(db.Model):
    """Distribution/Donation Intake (AIDMGMT workflow step 3)"""
    __tablename__ = 'dbintake'
    
    reliefpkg_id = db.Column(db.Integer, db.ForeignKey('reliefpkg.reliefpkg_id'), primary_key=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.inventory_id'), primary_key=True)
    intake_date = db.Column(db.Date, nullable=False)
    comments_text = db.Column(db.String(255))
    status_code = db.Column(db.CHAR(1), nullable=False)
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime)
    verify_by_id = db.Column(db.String(20))
    verify_dtime = db.Column(db.DateTime)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    package = db.relationship('ReliefPkg', backref='intake_records')
    inventory = db.relationship('Inventory', backref='intake_records')

class DBIntakeItem(db.Model):
    """Distribution/Donation Intake Item"""
    __tablename__ = 'dbintake_item'
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['reliefpkg_id', 'inventory_id'],
            ['dbintake.reliefpkg_id', 'dbintake.inventory_id']
        ),
    )
    
    reliefpkg_id = db.Column(db.Integer, primary_key=True)
    inventory_id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'), primary_key=True)
    usable_qty = db.Column(db.Numeric(12, 2), nullable=False)
    location1_id = db.Column(db.Integer, db.ForeignKey('location.location_id'))
    defective_qty = db.Column(db.Numeric(12, 2), nullable=False)
    location2_id = db.Column(db.Integer, db.ForeignKey('location.location_id'))
    expired_qty = db.Column(db.Numeric(12, 2), nullable=False)
    location3_id = db.Column(db.Integer, db.ForeignKey('location.location_id'))
    uom_code = db.Column(db.String(25), db.ForeignKey('unitofmeasure.uom_code'), nullable=False)
    status_code = db.Column(db.CHAR(1), nullable=False)
    comments_text = db.Column(db.String(255))
    create_by_id = db.Column(db.String(20), nullable=False)
    create_dtime = db.Column(db.DateTime, nullable=False)
    update_by_id = db.Column(db.String(20), nullable=False)
    update_dtime = db.Column(db.DateTime, nullable=False)
    version_nbr = db.Column(db.Integer, nullable=False, default=1)
    
    item = db.relationship('Item', backref='intake_items')
