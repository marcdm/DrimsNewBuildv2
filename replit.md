# DRIMS - Disaster Relief Inventory Management System

## Overview
DRIMS (Disaster Relief Inventory Management System) is a web-based platform for the Government of Jamaica's ODPEM, managing the entire lifecycle of disaster relief supplies. It ensures compliance with the authoritative ODPEM `aidmgmt-3.sql` schema and supports multi-warehouse inventory, disaster event coordination, and the AIDMGMT relief workflow (Request → Package → Intake). The system includes comprehensive management for users, donors, agencies, and custodians, along with analytics, reporting, donation tracking, and robust security via role-based access control and audit logging.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Technology Stack
- **Backend**: Python 3.11 + Flask 3.0.3
- **Database ORM**: SQLAlchemy 2.0.32 with Flask-SQLAlchemy
- **Authentication**: Flask-Login 0.6.3 with Werkzeug
- **Frontend**: Server-side rendering with Jinja2, Bootstrap 5.3.3, Bootstrap Icons
- **Data Processing**: Pandas 2.2.2

### Application Structure
- **Modular Blueprint Architecture**: `app.py` for main application, `app/features/*` for feature-specific blueprints.
- `app/db/models.py`: SQLAlchemy models mapping to a pre-existing database schema (database-first).
- `app/core/*`: Shared utilities.
- `templates/`: Jinja2 templates with consistent GOJ branding.

### UI/UX Design
- **Consistent Styling**: Reusable CSS utilities (`.drims-card`, `.drims-table`), standard button classes (`btn-sm` for view, edit, delete).
- **Navigation**: Row-click navigation for tables, fixed header, collapsible sidebar.
- **Branding**: GOJ branding with primary green (`#009639`) and gold accent (`#FDB913`), integrated Jamaica Coat of Arms and ODPEM logo on login, navigation header, and footer.
- **Accessibility**: Alt text for logos.
- **User Experience**: Icon-based empty states, responsive design.

### Database Architecture
- **Schema**: 40 tables from the authoritative ODPEM `aidmgmt-3.sql` schema.
- **Key Design Decisions**:
    - **UPPERCASE Enforcement**: All `varchar` fields stored in uppercase.
    - **Audit Fields**: `create_by_id`, `create_dtime`, `update_by_id`, `update_dtime`, `version_nbr` on ODPEM tables.
    - **DECIMAL Quantities**: `DECIMAL(15,4)` for all quantity fields.
    - **Status Codes**: Integer/character codes for various entities.
    - **Composite Keys**: Used in many tables.
    - **Optimistic Locking**: Implemented across all `version_nbr` enabled tables to prevent lost updates.
    - **Referential Integrity**: `warehouse_id` on agency table with `CHECK` constraints for agency types.
    - **User Account Management**: Enhanced `public.user` table with MFA support, account lockout, password management, agency linkage, and optimistic locking.
    - **Agency Account Request Workflow**: New `agency_account_request` and `agency_account_request_audit` tables for managing agency onboarding.

### Data Flow Patterns
- **AIDMGMT Relief Workflow**: Relief Request Creation → Package Preparation → Distribution & Intake.
- **Inventory Management**: Central `inventory` table tracks stock by warehouse and item (`usable_qty`, `reserved_qty`, `defective_qty`, `expired_qty`), with `location` table for bin-level tracking.

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
- **DRIMS_Complete_Schema.sql**: For full schema setup and reference data seeding.
- `scripts/init_db.py`: Executes the complete schema.
- `scripts/seed_demo.py`: Populates minimal test data.