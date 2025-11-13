# DRIMS - Disaster Relief Inventory Management System

## Overview

DRIMS (Disaster Relief Inventory Management System) is a comprehensive web-based platform for the Government of Jamaica's ODPEM. It manages the full lifecycle of disaster relief supplies, from inventory tracking and donation management to relief request processing and distribution.

The system uses the authoritative ODPEM `aidmgmt-3.sql` schema for all disaster relief workflows, ensuring complete compliance with established government processes.

Key capabilities include:
- **Multi-warehouse inventory management** with real-time and bin-level tracking.
- **Disaster event coordination** and supply allocation.
- **AIDMGMT relief workflow**: Request → Package → Intake for disaster relief processing.
- **Comprehensive management suite**: User administration with RBAC, donor, agency, custodian management, inventory transfers, and location tracking.
- **Analytics & reporting**: Dashboard with KPIs, notifications, and exportable reports.
- **Donation and transfer management** with audit trails.
- **Robust security**: Role-based access control, warehouse-level permissions, and full audit logging.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### November 13, 2025 - Relief Request Item Referential Integrity Enhancement
- **Critical Business Logic Constraint**: Replaced simple `c_reliefrqst_item_2` with enhanced `c_reliefrqst_item_2a` to enforce workflow semantics
  - **Old Constraint**: Only checked `issue_qty <= request_qty` (allowed illogical states like status='R' with issue_qty>0)
  - **New Constraint**: Enforces proper status/quantity relationships:
    * R/U/W/D statuses → `issue_qty = 0` (not yet fulfilled)
    * P/L statuses → `issue_qty < request_qty` (partially filled)
    * F status → `issue_qty = request_qty` (fully filled)
  - **Migration Method**: Table rebuild via rename → create → copy → drop (2 existing rows migrated successfully)
  - **Validation**: Pre-migration checks confirmed zero constraint violations in existing data
- **Duplicate Constraint Cleanup**: Removed redundant auto-generated constraints during table rebuild
  - Removed: `reliefrqst_item_request_qty_check`, `reliefrqst_item_status_code_check`, `reliefrqst_item_urgency_ind_check`
  - Retained: Named constraints `c_reliefrqst_item_1` through `c_reliefrqst_item_8` for clarity
- **Database Constraint Update**: Added default values to `reliefrqst_item` columns
  - `status_code CHAR(1) NOT NULL DEFAULT 'R'` - New items default to "Requested"
  - `issue_qty DECIMAL(12,2) NOT NULL DEFAULT 0.00` - New items start with zero issued quantity
  - `version_nbr INTEGER NOT NULL DEFAULT 1` - Optimistic locking starts at version 1
- **Status Code Constants**: Created comprehensive status code dictionary in `relief_request_service.py`
  - **Constants**: `ITEM_STATUS_REQUESTED`, `ITEM_STATUS_UNAVAILABLE`, `ITEM_STATUS_WAITING`, `ITEM_STATUS_DENIED`, `ITEM_STATUS_PARTLY_FILLED`, `ITEM_STATUS_LIMIT_ALLOWED`, `ITEM_STATUS_FILLED`
  - **Labels Dictionary**: `ITEM_STATUS_LABELS` maps codes to human-readable labels (e.g., 'R': 'Requested', 'U': 'Unavailable')
- **Model Update**: Updated `ReliefRqstItem` model with `server_default='R'` for consistency
- **Code Standardization**: Updated item creation logic to use `ITEM_STATUS_REQUESTED` constant instead of hardcoded 'R'
- **Template Fixes**: Corrected UOM field access patterns across all templates
  - Fixed: `item.uom.uom_code` → `item.item.default_uom_code` (ReliefRqstItem → Item → default_uom_code)
  - Updated templates: `requests/edit_items.html`, `agency_requests/edit_items.html`, `agency_requests/view.html`
- **Referential Integrity Verification**: Confirmed no orphaned foreign key references (0 invalid reliefrqst_id, 0 invalid item_id)

### November 13, 2025 - Eligibility Approval Workflow Implementation
- **RBAC Extension**: Enhanced role-based access control with permission-based authorization
  - Added `has_permission(resource, action)` function to check user permissions via role_permission table
  - Added `@permission_required(resource, action)` decorator for route protection
  - Added `Permission` and `RolePermission` SQLAlchemy models mapping to existing RBAC tables
  - Database-agnostic implementation using SQLAlchemy ORM (works with both SQLite and PostgreSQL)
- **Eligibility Service Layer**: Created comprehensive service methods in `relief_request_service.py`
  - `get_pending_eligibility_requests()` - Lists requests awaiting review (status=SUBMITTED, no review_by_id)
  - `get_request_eligibility_details()` - Gets full request details with decision status
  - `submit_eligibility_decision()` - Handles Yes/No decisions with validation and notifications
  - `can_process_request()` - Blocks fulfillment of ineligible requests
  - Added STATUS_INELIGIBLE = 8 constant
- **Eligibility Blueprint**: New `/eligibility` routes for Directors to review relief requests
  - HTML routes: `/eligibility/pending` (worklist), `/eligibility/review/<id>` (review form)
  - JSON API: `/eligibility/api/pending`, `/eligibility/api/<id>`, `/eligibility/api/decision/<id>`
  - Permission-protected with `reliefrqst.approve_eligibility` permission
- **Frontend Templates**: Professional eligibility review interface
  - `pending.html` - Worklist showing tracking number, agency, event, urgency, items count
  - `review.html` - Detailed review form with radio buttons (Eligible/Ineligible), conditional reason textarea
  - JavaScript validation ensures reason is required for ineligible decisions
  - Read-only view when decision already made
- **Navigation Integration**: Added "Eligibility Review" link to AIDMGMT section in sidebar
  - Only visible to users with `reliefrqst.approve_eligibility` permission
  - Uses Bootstrap Icons clipboard-check icon
- **Business Logic**:
  - Pending: Requests with status_code=3 (SUBMITTED) and review_by_id IS NULL
  - Eligible: Sets review_by_id/review_dtime, keeps status=SUBMITTED, notifies logistics team (LO/LM roles)
  - Ineligible: Sets status_code=8, requires reason in status_reason_desc, notifies agency users
  - Blocks processing of ineligible requests in fulfillment workflow
- **Notifications**: Automatic in-app notifications
  - Ineligible: Notifies all active agency users with reason
  - Eligible: Notifies logistics officers and managers for fulfillment processing
- **Schema Compliance**: Uses existing columns (review_by_id, review_dtime, status_reason_desc) - zero schema changes required

### November 12, 2025 - Relief Request Status Lookup Table Migration
- **Database Migration**: Created `reliefrqst_status` lookup table for standardized status management
  - **Table Structure**: status_code (smallint PK), status_desc (varchar 20), is_active_flag (boolean)
  - **Status Codes**: 8 standard values (0=DRAFT, 1=Awaiting approval, 2=CANCELLED, 3=SUBMITTED, 4=DENIED, 5=PART FILLED, 6=CLOSED, 7=FILLED)
  - **Foreign Key**: `reliefrqst.status_code` now references `reliefrqst_status.status_code`
  - **Data Type**: Changed status_code from CHAR(1) to smallint for better type safety
  - **Indexes**: Added performance indexes on (agency_id, request_date), (request_date, status_code), (status_code, urgency_ind)
- **Model Updates**: 
  - Created `ReliefRqstStatus` model for lookup table
  - Updated `ReliefRqst` model with foreign key relationship to status table
  - Added `status` relationship property for easy access to status description
- **Idempotency**: Migration is fully idempotent and can be run multiple times safely
- **Template Fixes**: Corrected workflow stepper macro import and UOM field references in request view

### November 12, 2025 - User Creation Organization Dropdown with Security Enhancements
- **User Interface**: Replaced text input with dropdown for organization field in user creation and editing
  - **Dropdown Structure**: Uses `<optgroup>` to separate active agencies (status='A') from custodians
  - **Value Format**: "AGENCY:<id>" or "CUSTODIAN:<id>" for clear type identification
  - **Current Value Selection**: Edit form pre-selects the user's current organization (agency or custodian)
- **Comprehensive Validation** (8-layer protection stack):
  1. **Tamper Detection**: Field presence check BEFORE value retrieval prevents malicious requests
  2. **Format Validation**: Requires colon separator in value
  3. **Prefix Whitelist**: Only accepts 'AGENCY' or 'CUSTODIAN' prefixes
  4. **Numeric ID Validation**: Verifies ID is numeric before database lookup
  5. **Database Validation**: Confirms entity exists in respective table
  6. **Status Verification**: Agencies must have status_code='A' (active)
  7. **Consistent State**: Agency selection sets both organization name and agency_id FK; custodian selection explicitly clears agency_id=None
  8. **Transaction Protection**: try/except with rollback prevents partial commits
- **Session State Protection**: Edit route calls `db.session.refresh(user)` after rollback to discard stale mutations
- **Security**: Prevents tampered POST requests from wiping organization data when field is missing
- **Data Integrity**: Zero risk of orphaned foreign keys or inconsistent organization/agency_id states
- **User Experience**: Form preserves input on validation errors, friendly error messages guide users

### November 12, 2025 - Agency Account Creation Workflow Tables
- **New Tables**: Added two tables for agency account request workflow without altering any existing tables
  - **`agency_account_request`**: Main request table with optimistic locking (version_nbr)
    - Workflow status: S=submitted, R=review, A=approved, D=denied
    - Links to agency and user upon approval/provisioning
    - Partial unique constraint on contact_email while status in ('S','R')
    - Auto-update trigger using existing `set_updated_at()` function
  - **`agency_account_request_audit`**: Immutable audit log for all workflow events
    - Event types: submitted, moved_to_review, approved, denied, provisioned
    - Tracks actor, timestamp, and notes for full audit trail
- **Foreign Keys**: Both tables properly linked to existing `agency` and `user` tables
- **Constraints**: CHECK constraint on status_code, foreign keys enforced
- **Indexes**: Unique partial index on active email, composite index on status/created_at
- **Models**: Created `AgencyAccountRequest` and `AgencyAccountRequestAudit` SQLAlchemy models
- **Optimistic Locking**: Fully supports concurrent request processing with version_nbr
- **Safety**: All changes isolated to new tables; zero modifications to existing schema

### November 12, 2025 - User Table Enhancement for Full Account Management
- **Database Migration**: Added comprehensive user account management columns to `public.user` table
  - **MFA Support**: `mfa_enabled` (boolean), `mfa_secret` (varchar) for multi-factor authentication
  - **Account Lockout**: `failed_login_count` (smallint), `lock_until_at` (timestamp) for security lockout controls
  - **Password Management**: `password_algo` (varchar, default 'argon2id'), `password_changed_at` (timestamp)
  - **Agency Linkage**: `agency_id` foreign key to `agency.agency_id` with index for user-agency relationships
  - **Account Status**: `status_code` (char, default 'A') with CHECK constraint ('A'=Active, 'I'=Inactive, 'L'=Locked)
  - **Username**: `username` (varchar, unique) for alternative login method
  - **Optimistic Locking**: `version_nbr` (integer, NOT NULL) for concurrent update protection
- **Database Constraints**: Added unique index on `username`, foreign key to agency table, status code validation
- **Audit Triggers**: Created `set_updated_at()` trigger function to automatically update `updated_at` timestamp
- **Model Updates**: Updated `User` model in `app/db/models.py` with all new columns and agency relationship
- **Data Preservation**: Migration is idempotent and preserves all existing user data (4 users updated with version_nbr=1)
- **citext Extension**: Enabled for case-insensitive email comparisons

### November 12, 2025 - Optimistic Locking Implementation
- **Configuration**: Automatic optimistic locking using SQLAlchemy's `version_id_col` feature
- **Coverage**: All 40 database tables with `version_nbr` column now have optimistic locking enabled
- **Mechanism**: Version numbers automatically increment on updates; concurrent modifications raise `StaleDataError`
- **Implementation**: `app/core/optimistic_locking.py` configures all mappers during app initialization
- **Custom Exception**: `OptimisticLockError` class in `app/core/exceptions.py` for application-specific error handling
- **Verification**: Version increments confirmed working (e.g., 4→5→6 on successive updates)
- **Documentation**: Comprehensive guide in `docs/OPTIMISTIC_LOCKING.md` with usage examples and testing patterns
- **Benefits**: Prevents lost updates, no database locks needed, automatic version management, audit compliance

### November 12, 2025 - DRIMS Needs/Fulfillment Workflow Removal (System Simplification)
- **Scope**: Removed entire Needs List/Fulfillment/Dispatch/Receipt workflow to focus exclusively on AIDMGMT
- **Database**: Dropped 7 tables (needs_list, needs_list_item, fulfilment, fulfilment_line_item, fulfilment_edit_log, dispatch_manifest, receipt_record)
- **Schema Reduction**: Database reduced from 47 to 40 tables
- **Backup Created**: drims_backup_20251112180328.sql (131KB) - full backup before destructive changes
- **Code Cleanup**: Removed 4 Flask blueprints, 7 model classes, navigation menu items, and 3 RBAC functions (can_approve_needs_lists, can_prepare_fulfilments, can_submit_needs_lists)
- **Rationale**: Streamlined system to use only the authoritative ODPEM AIDMGMT workflow for all relief operations

### November 12, 2025 - Official Government Branding Implementation
- **Login Screen**: Integrated Jamaica Coat of Arms and ODPEM logo with proper hierarchy
- **Navigation Header**: ODPEM logo with DRIMS branding in top navigation bar
- **Footer**: Professional government footer with both official logos and copyright information
- **Static Assets**: Organized logos in `/static/images/` directory
- **Accessibility**: All logos include proper alt text for screen readers
- **Responsive Design**: Logo sizing adapts to different screen sizes
- **Best Practices**: Follows international standards for government web applications

### November 12, 2025 - Agency Table Referential Integrity Enhancement
- **Database Schema Update**: Added `warehouse_id` field to agency table with full referential integrity
  - Foreign key constraint to `warehouse(warehouse_id)`
  - Complex CHECK constraint (`c_agency_5`): SHELTER agencies must have NULL warehouse_id, DISTRIBUTOR agencies must have non-NULL warehouse_id
  - Ensures business rules are enforced at database level
- **Model Update**: Agency model now includes `warehouse_id` field and relationship to Warehouse
- **Form Enhancements**: Dynamic warehouse field visibility based on agency type
  - JavaScript-based toggle: shows warehouse selector only for DISTRIBUTOR agencies
  - Client-side and server-side validation
- **UI Improvements**: Agency view page displays associated warehouse with clickable link
- **Validation**: Backend validation ensures DISTRIBUTOR agencies must select a warehouse

### November 12, 2025 - Agency Management Enhancement
- **Updated Agency Forms**: Added new AIDMGMT-3.1 fields to agency management
  - `agency_type`: Categorize as DISTRIBUTOR or SHELTER
  - `status_code`: Track Active (A) or Inactive (I) status
  - `ineligible_event_id`: Link to events the agency cannot participate in
- **Updated Templates**: All agency forms (create, edit, view, index) now display new fields with badges
- **Backend Integration**: Routes updated to handle new fields with proper validation
- **UI Enhancement**: Status and type badges for visual clarity in agency listings

## System Architecture

### Technology Stack
- **Backend**: Python 3.11 + Flask 3.0.3
- **Database ORM**: SQLAlchemy 2.0.32 with Flask-SQLAlchemy
- **Authentication**: Flask-Login 0.6.3 with Werkzeug
- **Frontend**: Server-side rendering with Jinja2, Bootstrap 5.3.3, Bootstrap Icons
- **Data Processing**: Pandas 2.2.2

### Application Structure
- **Modular Blueprint Architecture**: `app.py` for main application, `app/features/*` for feature-specific blueprints (AIDMGMT workflow, core entities, management features, system features).
- `app/db/models.py`: SQLAlchemy models mapping to a pre-existing database schema (database-first approach).
- `app/core/*`: Shared utilities.
- `templates/`: Jinja2 templates with consistent GOJ branding.

### UI/UX Design
- **Global CSS Utilities**: Reusable classes (`.drims-card`, `.drims-table`) for consistent styling (rounded corners, subtle shadows, specific header/row styles).
- **Row-Click Navigation**: `table-clickable` class enables navigation on row click via `data-href` attributes, ignoring nested buttons.
- **Standard Button Classes**: Consistent `btn-sm` styling for view (outline-primary), edit (warning), and delete (danger) actions.
- **Responsive Design**: Fixed header, collapsible sidebar (260px to 70px on mobile), dynamic main content margins, touch-friendly interactions.
- **GOJ Branding**: Consistent use of primary green (`#009639`) and gold accent (`#FDB913`).
- **Empty States**: Icon-based empty states for improved user experience.

### Database Architecture
- **Schema**: 40 tables total from the authoritative ODPEM `aidmgmt-3.sql` schema.
- **Key Design Decisions**:
    - **UPPERCASE Enforcement**: All `varchar` fields stored in uppercase.
    - **Audit Fields**: `create_by_id`, `create_dtime`, `update_by_id`, `update_dtime`, `version_nbr` on ODPEM tables.
    - **DECIMAL Quantities**: `DECIMAL(15,4)` for all quantity fields.
    - **Status Codes**: Integer/character codes for various entities.
    - **Composite Keys**: Used in many tables.

### Data Flow Patterns
- **AIDMGMT Relief Workflow**: Relief Request Creation → Package Preparation → Distribution & Intake.
- **Inventory Management**: Central `inventory` table tracks stock by warehouse and item, with `usable_qty`, `reserved_qty`, `defective_qty`, `expired_qty`. `location` table provides bin-level tracking.

## External Dependencies

### Required Database
- **PostgreSQL 16+** (production) with `citext` extension.
- **SQLite3** (development fallback).

### Python Packages
- Flask 3.0.3
- Flask-SQLAlchemy 3.1.1
- Flask-Login 0.6.3
- SQLAlchemy 2.0.32
- psycopg2-binary 2.9.9
- Werkzeug 3.0.3
- pandas 2.2.2
- python-dotenv 1.0.1

### Frontend CDN Resources
- Bootstrap 5.3.3 CSS/JS
- Bootstrap Icons 1.11.3

### Database Schema and Initialization
- **DRIMS_Complete_Schema.sql**: Must be executed to set up all tables and seed reference data.
- `scripts/init_db.py`: Executes the complete schema.
- `scripts/seed_demo.py`: Populates minimal test data.