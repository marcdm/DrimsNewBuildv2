# DRIMS - Disaster Relief Inventory Management System

## Overview

DRIMS (Disaster Relief Inventory Management System) is a comprehensive web-based platform for the Government of Jamaica's ODPEM, designed to manage the full lifecycle of disaster relief supplies. It ensures compliance with established government processes by utilizing the authoritative ODPEM `aidmgmt-3.sql` schema.

The system's core purpose is to streamline inventory tracking, donation management, relief request processing, and distribution across multiple warehouses, supporting disaster event coordination and supply allocation. It offers a robust management suite including user administration with RBAC, donor/agency/custodian management, inventory transfers, and location tracking. Key capabilities also include analytics, reporting, donation management with audit trails, and strong security features like role-based access control and audit logging. The project aims to provide a centralized, efficient, and transparent system for disaster relief operations in Jamaica.

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
- **Modular Blueprint Architecture**: `app.py` for main application, with feature-specific blueprints organized under `app/features/`.
- **Database-First Approach**: SQLAlchemy models (`app/db/models.py`) map to a pre-existing ODPEM `aidmgmt-3.sql` schema.
- **Shared Utilities**: Located in `app/core/`.
- **Templates**: Jinja2 templates (`templates/`) enforce consistent Government of Jamaica (GOJ) branding.

### UI/UX Design
- **Consistent Styling**: Global CSS utilities (`.drims-card`, `.drims-table`) ensure uniform appearance with rounded corners and subtle shadows.
- **Navigation**: `table-clickable` class provides row-click navigation.
- **Button Styling**: Standardized `btn-sm` for actions (view, edit, delete).
- **Responsive Design**: Fixed header, collapsible sidebar, dynamic content margins, and touch-friendly interactions.
- **Branding**: Utilizes GOJ branding with primary green (`#009639`) and gold accent (`#FDB913`), including official logos on login, navigation, and footer with accessibility features.
- **User Experience**: Icon-based empty states and professional eligibility review interfaces.

### Database Architecture
- **Schema**: Based on the authoritative ODPEM `aidmgmt-3.sql` schema, comprising 40 tables.
- **Key Design Decisions**:
    - **Data Consistency**: All `varchar` fields are stored in uppercase.
    - **Auditability**: `create_by_id`, `create_dtime`, `update_by_id`, `update_dtime`, and `version_nbr` are standard on ODPEM tables.
    - **Precision**: `DECIMAL(15,4)` for all quantity fields.
    - **Status Management**: Integer/character codes for entity statuses.
    - **Composite Keys**: Utilized in many tables for unique identification.
    - **Referential Integrity**: Enforced via foreign keys and complex `CHECK` constraints (e.g., `c_agency_5` for agency types).
    - **Optimistic Locking**: Implemented across all 40 tables using SQLAlchemy's `version_id_col` to prevent concurrent update conflicts, raising `OptimisticLockError`.
    - **Standardized Status Management**: Migration to `reliefrqst_status` lookup table for standardized request statuses.
    - **User Account Management**: Enhanced `public.user` table with fields for MFA, account lockout, password management, agency linkage, and account status, and `citext` extension for case-insensitive email.
    - **New Workflows**: Introduced `agency_account_request` and `agency_account_request_audit` tables for managing agency account creation workflows without altering existing schema.

### Data Flow Patterns
- **AIDMGMT Relief Workflow**: Complete end-to-end workflow covering:
  1. **Relief Request Creation** (agencies) - Status: DRAFT (0) → AWAITING_APPROVAL (1)
  2. **Eligibility Review** (ODPEM directors) - Status: AWAITING_APPROVAL (1) → SUBMITTED (3) or INELIGIBLE (8)
  3. **Package Preparation** (logistics officers/managers) - Status: SUBMITTED (3) → PART_FILLED (5) → FILLED (7)
  4. **Distribution & Intake** (agencies receive goods)
- **Inventory Management**: Tracks stock by warehouse and item in the `inventory` table, including `usable_qty`, `reserved_qty`, `defective_qty`, `expired_qty`, with bin-level tracking via the `location` table.
- **Eligibility Approval Workflow**: Integrated role-based access control (RBAC) with `has_permission` and `@permission_required` decorators. Service layer for eligibility decisions, notifications, and workflow enforcement.
- **Package Fulfillment Workflow**: LO/LM access "Pending Fulfillment" list showing SUBMITTED (3) and PART_FILLED (5) requests, create relief packages from approved requests with real-time inventory checking.

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
- **DRIMS_Complete_Schema.sql**: Used for initial database setup and seeding reference data.
- `scripts/init_db.py`: Executes the complete schema.
- `scripts/seed_demo.py`: Populates minimal test data.