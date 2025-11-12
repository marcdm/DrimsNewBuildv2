# DRIMS - Disaster Relief Inventory Management System

## Recent Changes

**November 12, 2025 - UI/UX Rebuild (In Progress - 8 of 11 tasks complete)**
- ✅ **Role-Based Dashboards**: Three logistics dashboards with Chart.js visualizations
  - Logistics Manager: 6 KPIs, category distribution chart, 3-column approval queues
  - Logistics Officer: Operational focus with 4 KPIs
  - Logistics Executive: Strategic metrics with grouped bar chart
- ✅ **Needs List Detail Page**: Visual activity timeline with colored markers, improved card layout, context-aware quick actions
- ✅ **Multi-Step Create Wizard**: 4-step process (Basic Info → Add Items → Review → Submit) with draft/submit differentiation, searchable items table, and validation
- ✅ **Enhanced Prepare Fulfilment**: Modern card layout with real-time stock checking API, warehouse allocation table, client-side validation
- ✅ **Role-Based Access Control**: Comprehensive RBAC module with @role_required decorator, template helpers, applied to user administration
- 🔄 **Remaining Tasks**: Table styling updates, responsive testing, documentation

**November 12, 2025 - Complete Management Features Suite Implementation**
- ✅ **User Administration**: Full CRUD with role-based access control and warehouse assignments
- ✅ **Donor Management**: Donor tracking with contact information and donation history
- ✅ **Agency Management**: Relief agency management with parish locations and contact tracking
- ✅ **Custodian Management**: Warehouse custodian/manager tracking system
- ✅ **Dashboard**: Analytics dashboard with KPIs, low stock alerts, warehouse status, recent activities
- ✅ **Transfer Management**: Complete inventory transfer workflow (create → execute) with automatic inventory adjustments
- ✅ **Location Management**: Bin/shelf level inventory tracking with aisle and bin numbering
- ✅ **Notifications System**: Real-time alerts for low stock items and pending approvals
- ✅ **Reports System**: Inventory summary, needs/fulfilment reports, donations summary with CSV export
- ✅ All 9 management features integrated into navigation with consistent GOJ branding

**November 12, 2025 - DRIMS Modern Workflow Implementation**
- ✅ Needs List feature: Create, submit, approve relief needs with full workflow state management
- ✅ Fulfilment feature: Multi-step processing (In Preparation → Ready → Dispatched → Received → Completed)
- ✅ Dispatch Manifest feature: Track shipment logistics with vehicle/driver information
- ✅ Receipt Record feature: Confirm delivery with condition notes and discrepancy tracking
- ✅ Status badge macro system for consistent UI across both workflows
- ✅ Cascading status updates: Completing fulfilment auto-updates parent needs list
- ✅ End-to-end workflow tested: NL000001/NL000002 → FUL000001/FUL000002 → RR000001

## Overview

DRIMS (Disaster Relief Inventory Management System) is a comprehensive web-based platform designed for the Government of Jamaica's Office of Disaster Preparedness and Emergency Management (ODPEM). The system manages the complete lifecycle of disaster relief supplies—from inventory tracking and donation management to relief request processing and distribution.

The application implements a **dual workflow architecture**, combining the authoritative ODPEM aidmgmt-3.sql schema with modern DRIMS workflow enhancements. This hybrid approach provides both compliance with established disaster management protocols and an improved user experience through contemporary UI patterns.

Key capabilities include:
- **Multi-warehouse inventory management** with real-time stock tracking and bin-level location tracking
- **Disaster event coordination** and supply allocation
- **Dual relief workflows**: 
  - AIDMGMT (Request → Package → Intake)
  - DRIMS (Needs List → Fulfilment → Dispatch → Receipt)
- **Complete management suite**:
  - User administration with role-based access control
  - Donor, agency, and custodian management
  - Inventory transfers with automatic stock adjustments
  - Warehouse location/bin tracking
- **Analytics & reporting**: Dashboard with KPIs, notifications, exportable reports
- **Donation and transfer management** with full audit trails
- **Comprehensive security**: Role-based access control, warehouse-level permissions, full audit logging

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Technology Stack
- **Backend**: Python 3.11 + Flask 3.0.3
- **Database ORM**: SQLAlchemy 2.0.32 with Flask-SQLAlchemy
- **Authentication**: Flask-Login 0.6.3 with Werkzeug password hashing
- **Frontend**: Server-side rendering with Jinja2 templates
- **UI Framework**: Bootstrap 5.3.3 with Bootstrap Icons
- **Data Processing**: Pandas 2.2.2 for analytics capabilities

### Application Structure

**Modular Blueprint Architecture**:
- `app.py` - Main Flask application with blueprint registration
- `app/features/*` - Feature-specific blueprints:
  - **AIDMGMT workflow**: `requests.py`, `packages.py`, `intake.py`
  - **DRIMS workflow**: `needs_list.py`, `fulfilment.py`, `dispatch.py`, `receipt.py`
  - **Core entities**: `events.py`, `warehouses.py`, `items.py`, `inventory.py`, `donations.py`
  - **Management features**: `user_admin.py`, `donors.py`, `agencies.py`, `custodians.py`, `transfers.py`, `locations.py`
  - **System features**: `dashboard.py`, `notifications.py`, `reports.py`
- `app/db/models.py` - SQLAlchemy models mapping to existing database schema
- `app/core/*` - Shared utilities (audit helpers, status mappings)
- `templates/` - Jinja2 templates organized by feature with consistent GOJ branding

**Design Pattern**: The application uses a **database-first approach** where SQLAlchemy models map to pre-existing tables created by SQL schema. No auto-create or migrations—the database schema is the source of truth.

### Database Architecture

**Hybrid Schema Strategy** (51 tables total):

1. **Core ODPEM Tables** (aidmgmt-3.sql - 26 tables):
   - Reference data: `country`, `parish`, `unitofmeasure`, `itemcatg`, `custodian`
   - Master entities: `event`, `warehouse`, `item`, `donor`, `agency`, `inventory`, `location`
   - AIDMGMT workflow: `reliefrqst` → `reliefpkg` → `dbintake` (with detail tables)
   - Supporting workflows: `donation`, `transfer` (with detail tables)

2. **DRIMS Extensions** (16 tables):
   - User management: `user`, `role`, `user_role`, `user_warehouse`
   - Modern workflow: `needs_list`, `fulfilment`, `dispatch_manifest`, `receipt_record`, `distribution_package`
   - Audit capabilities: `fulfilment_edit_log`

**Key Design Decisions**:
- **UPPERCASE Enforcement**: All varchar fields are stored in UPPERCASE per ODPEM standards
- **Audit Fields**: Every aidmgmt-3.sql table requires `create_by_id`, `create_dtime`, `update_by_id`, `update_dtime`, `version_nbr`
- **DECIMAL Quantities**: All quantity fields use DECIMAL(15,4) for precision
- **Status Codes**: Integer codes for requests (0-7), character codes for items/warehouses ('A'/'I')
- **Composite Keys**: Many tables use multi-column primary keys (e.g., `dbintake`, `reliefpkg_item`)

### Configuration Management

**Environment-Based Settings** (`settings.py`):
- `DATABASE_URL` - PostgreSQL connection (production) or SQLite (development)
- `WORKFLOW_MODE` - Toggle between 'AIDMGMT' (official workflow) and 'DRIMS' (modern workflow)
- `SECRET_KEY` - Flask session security
- `GOJ_GREEN`/`GOJ_GOLD` - Government of Jamaica branding colors
- `MAX_CONTENT_LENGTH` - File upload limits (16MB)

**Rationale**: Configuration through environment variables enables seamless deployment across development, staging, and production without code changes.

### Authentication & Security

**Flask-Login Integration**:
- Session-based authentication with secure password hashing (Werkzeug)
- User model implements UserMixin for Flask-Login compatibility
- Login required decorators protect all application routes
- User context available throughout request lifecycle via `current_user`

**Audit Trail Pattern**:
- `app/core/audit.py` provides `add_audit_fields()` helper
- Automatically sets create/update timestamps and user IDs
- Version numbering for optimistic locking
- UPPERCASE enforcement for user IDs to match database constraints

### Data Flow Patterns

**AIDMGMT Relief Workflow** (Official ODPEM Process):
1. **Relief Request Creation** (`reliefrqst` + `reliefrqst_item`) - Agencies submit needs
2. **Package Preparation** (`reliefpkg` + `reliefpkg_item`) - Warehouse staff allocate inventory
3. **Distribution & Intake** (`dbintake` + `dbintake_item`) - Receiving locations confirm receipt

**DRIMS Modern Workflow** (Enhanced User Experience):
1. **Needs Assessment** (`needs_list`) - Create, submit, approve relief needs
   - Status flow: Draft → Submitted → Approved → Completed
   - Tracks agency, event, priority, and requested items
2. **Fulfilment Processing** (`fulfilment` + `fulfilment_item`) - Allocate inventory and prepare shipments
   - Status flow: In Preparation → Ready → Dispatched → Received → Completed
   - Maintains edit logs for accountability (`fulfilment_edit_log`)
   - Auto-updates parent needs list status when completed
3. **Dispatch Tracking** (`dispatch_manifest`) - Document shipment logistics
   - Records vehicle, driver, route information
   - Links to fulfilment for complete chain of custody
4. **Receipt Confirmation** (`receipt_record`) - Verify delivery and condition
   - Captures received_by, condition notes, discrepancy tracking
   - Triggers fulfilment status update to "Received"

**Inventory Management**:
- Central `inventory` table tracks stock by warehouse + item
- Separate quantity columns: `usable_qty`, `reserved_qty`, `defective_qty`, `expired_qty`
- `location` table provides bin-level tracking within warehouses
- Status codes control availability ('A' = Available, 'U' = Unavailable)

**Pros of Current Approach**:
- Clear separation of concerns through blueprints
- Proven ODPEM workflow compliance
- Comprehensive audit capabilities
- Flexible dual-workflow support

**Cons & Trade-offs**:
- No database migrations (schema changes require manual SQL)
- UPPERCASE enforcement adds complexity to forms/validation
- Composite keys complicate ORM relationships
- Dual workflow creates some code duplication

## External Dependencies

### Required Database
- **PostgreSQL 16+** (production) with `citext` extension for case-insensitive text
- **SQLite3** (development fallback, but PostgreSQL strongly recommended)

### Python Packages
All dependencies managed via `requirements.txt`:
- Flask 3.0.3 - Web framework
- Flask-SQLAlchemy 3.1.1 - ORM integration
- Flask-Login 0.6.3 - Authentication
- SQLAlchemy 2.0.32 - Database toolkit
- psycopg2-binary 2.9.9 - PostgreSQL adapter
- Werkzeug 3.0.3 - Security utilities
- pandas 2.2.2 - Data analysis
- python-dotenv 1.0.1 - Environment configuration

### Frontend CDN Resources
- Bootstrap 5.3.3 CSS/JS - UI framework
- Bootstrap Icons 1.11.3 - Icon library

### Database Schema
- **DRIMS_Complete_Schema.sql** - Must be executed before application startup
- Contains both aidmgmt-3.sql tables and DRIMS extensions
- Includes reference data seeding (parishes, item categories, units of measure)
- Requires PostgreSQL `citext` extension for case-insensitive email matching

### Initialization Scripts
- `scripts/init_db.py` - Executes complete schema against database
- `scripts/seed_demo.py` - Populates minimal test data (admin user, sample records)

**Integration Notes**:
- Application assumes database is pre-populated via SQL execution
- No Alembic or Flask-Migrate—schema evolution is manual
- Connection pooling handled by SQLAlchemy defaults
- No caching layer currently implemented (future enhancement opportunity)