# DRIMS - Disaster Relief Inventory Management System

## Overview
DRIMS (Disaster Relief Inventory Management System) is a web-based platform for the Government of Jamaica's ODPEM. It is designed to manage the full lifecycle of disaster relief supplies, from inventory tracking and donation management to relief request processing and distribution across multiple warehouses. The system aims to ensure compliance with government processes, support disaster event coordination, supply allocation, and provide robust user administration with RBAC. Its purpose is to deliver a modern, efficient, and user-friendly solution for disaster preparedness and response, emphasizing security and comprehensive management capabilities including inventory transfers, location tracking, analytics, and reporting.

## Recent Changes (2025-11-19)
- **Batch-Level Inventory Commit Fix (Complete)**: Fixed critical bug in `commit_inventory()` where system checked warehouse-level inventory instead of batch-level inventory, causing "Insufficient inventory" errors even when batch allocations were valid. Root cause: Function aggregated all batch allocations per warehouse and checked if warehouse.usable_qty >= total_allocated, but allocations are done at batch level where each batch has its own usable_qty. Fix: Rewrote `commit_inventory()` to work at batch level - for each `ReliefPkgItem`, deduct from the specific `ItemBatch.usable_qty` and `reserved_qty`, validate each batch has sufficient quantity, then aggregate changes to update warehouse-level `Inventory` table. This ensures batch-level FEFO/FIFO allocations are correctly committed to individual batches while maintaining warehouse-level inventory accuracy. Fixes LM "Send for Dispatch" workflow.
- **Batch Allocation Persistence (Complete)**: Implemented full state persistence for batch allocations, allowing users to save drafts and return later to continue exactly where they left off. Backend loads batch-level allocations from `ReliefPkgItem` table on page load, template renders hidden inputs with saved quantities for each batch allocation (format: `batch_allocation_{item_id}_{batch_id}`), JavaScript `loadExistingAllocations()` automatically restores state from hidden inputs when batch drawer opens. When users save draft and leave preparation page, all batch allocations are preserved in database. Upon return, system loads allocations and pre-populates batch drawer with previously selected batches and quantities. Works seamlessly for both initial allocation and re-editing scenarios, ensuring continuity across work sessions for LO and LM workflows.
- **Inventory Reservation Service Fix (Complete)**: Fixed AttributeError in `inventory_reservation_service.py` where code tried to access non-existent `from_inventory` relationship attribute on `ReliefPkgItem` model. Root cause: `get_current_reservations()` was using `pkg_item.from_inventory.inventory_id` when the model only has `fr_inventory_id` column (warehouse ID) with no relationship defined. Fix: Updated to directly use `pkg_item.fr_inventory_id` which is the warehouse ID. Also improved type safety by adding `Optional` type hint for nullable parameters. This error was blocking the "Send for Dispatch" action in LM approval workflow.
- **Batch Drawer Warehouse Grouping Enhancement (Complete)**: Completely redesigned the batch allocation side drawer to group batches by warehouse with collapsible sections, improving usability when allocating from multiple warehouses. Features: (1) **Warehouse Grouping** - Batches organized by warehouse with collapsible headers showing warehouse name and allocation summary (e.g., "15.00 / 20.00 Allocated"). (2) **Jump-to-Warehouse Control** - Dropdown at top of drawer for quick navigation to specific warehouse sections with smooth scrolling. (3) **Per-Warehouse FEFO/FIFO Ordering** - Batches sorted by expiration/batch date within each warehouse group. (4) **Smart Batch Limiting** - Backend optimization shows batches from each warehouse until that warehouse can fulfill the requested quantity (early cutoff), reducing drawer clutter while maintaining full visibility. (5) **Allocated Batch Preservation** - Previously allocated batches always included for editing with deduplication guard. (6) **Real-time UI Updates** - Warehouse summaries update automatically as LM edits allocations. Implementation: Enhanced `BatchAllocationService.get_limited_batches_for_drawer()` with per-warehouse cumulative quantity tracking, updated `batch-allocation.js` with warehouse grouping/collapse/jump logic, added warehouse section styling to `batch-drawer.css`, updated `_batch_drawer.html` template with warehouse section structure and jump control. Works seamlessly for both LO (prepare) and LM (approve) workflows. Maintains existing UI/UX consistency with modern, polished design.
- **Confirmation Dialog Fix (Complete)**: Fixed all confirmation buttons across the application not working due to blocked browser confirm() dialogs. Root cause: Browser's native confirm() dialogs being blocked or auto-dismissed. Solution: Replaced all native confirm() dialogs with Bootstrap modals in 7 template files. Each modal features color-coded styling (green for submit actions, red for danger/delete actions), clear explanations of consequences, proper form submission on confirmation, and console logging for debugging. JavaScript event listeners prevent default form submission, show modal, then submit form when user confirms. Special handling in agency_requests/edit_items.html with DOMContentLoaded wrapper to ensure form exists before attaching listener (form renders conditionally only when items exist). Fixed templates: requests/edit_items.html (Submit to ODPEM, Delete Draft), agency_requests/edit_items.html (Submit Request to ODPEM), requests/view.html (Submit to ODPEM), agency_requests/view.html (Submit to ODPEM), transfers/view.html (Execute Transfer), items/view.html (Inactivate/Reactivate Item), user_admin/view.html (Deactivate/Activate Account).
- **Cancel Package Button Fix**: Fixed cancel button on package preparation page not showing visible confirmation dialog. Root cause: Browser's native confirm() dialog was being blocked or not displaying properly. Solution: Replaced native confirm() with a Bootstrap modal that provides clear, visible confirmation with danger styling (red header), explicit warning about consequences (deletes allocations, releases reservations, releases lock), and two distinct action buttons ("No, Keep Working" and "Yes, Cancel Package"). JavaScript function confirmCancelPackage() creates minimal POST form and submits to cancel_preparation endpoint. Modal trigger uses Bootstrap's data-bs-toggle/data-bs-target attributes for reliable operation. Includes comprehensive console logging for debugging.
- **Multi-Batch Fulfillment Bug Fix**: Fixed critical bug where LM approval queue excluded PART_FILLED requests, breaking multi-batch fulfillment workflow. Previously, after first package dispatch (status→PART_FILLED), subsequent packages submitted by LO wouldn't appear in LM approval queue. Root cause: pending_approval() filtered only STATUS_SUBMITTED requests. Fix: Updated filter to include both STATUS_SUBMITTED and STATUS_PART_FILLED, allowing LMs to approve follow-up packages for partially fulfilled requests. This enables complete multi-batch workflow: LO prepares batch 1→LM approves→status becomes PART_FILLED→LO prepares batch 2→LM can now see and approve batch 2.
- **Status Override Enhancement**: Enhanced LM approval workflow to allow D (Denied), U (Unavailable), W (Awaiting Availability) statuses to override any allocation amount. Previously, these statuses could only be selected with zero allocation. Now LM can allocate batches then manually override to D/U/W if needed. When D/U/W selected, issue_qty automatically sets to 0, preventing dispatch regardless of allocation. Status dropdown now shows: zero allocation → ['R','D','U','W'], partial allocation → ['P','L','D','U','W'], full allocation → ['F','L','D','U','W'].
- **Status Dropdown Auto-Reset Fix**: Fixed status dropdown not resetting from FILLED to PARTLY FILLED when LM reduces allocation below requested amount. Root cause: Code was trying to set dropdown value BEFORE updating options, so when status was 'F' with only ['F'] option and allocation dropped, it couldn't switch to 'P' because that option didn't exist yet. Fix: Swapped order in updateStatusDropdown() to call updateAllowedStatusOptions() FIRST (rebuilds dropdown with correct options ['P', 'L']), then set value. Now when allocation drops from 20/20 to 19/20, status correctly auto-resets from F→P, and LM can manually select 'L' (Allowed Limit) from dropdown.
- **Status Code Fix**: Fixed status auto-update logic in batch-allocation.js to use correct backend status codes ('R'=Requested, 'P'=Partly Filled, 'F'=Filled) instead of incorrect 'A' (Approved), matching item_status_service.py logic.
- **LM Notification Fix**: Fixed Logistics Managers not receiving notifications when Logistics Officers submit packages. Updated role code from 'LOGISTICS_MANAGER' to correct 'LM'.

## User Preferences
- **Communication style**: Simple, everyday language.
- **UI/UX Requirements**:
  - All pages MUST have consistent look and feel with Relief Package preparation pages
  - Modern, polished design with summary cards, filter tabs, and clean layouts
  - Easy to use and user-friendly across all features
  - Consistent navigation patterns throughout the application

## System Architecture

### Technology Stack
- **Backend**: Python 3.11, Flask 3.0.3
- **Database ORM**: SQLAlchemy 2.0.32 with Flask-SQLAlchemy
- **Authentication**: Flask-Login 0.6.3 with Werkzeug
- **Frontend**: Server-side rendering with Jinja2, Bootstrap 5.3.3, Bootstrap Icons
- **Data Processing**: Pandas 2.2.2

### System Design
The application utilizes a modular blueprint architecture with a database-first approach based on a pre-existing ODPEM `aidmgmt-3.sql` schema. Key architectural decisions include:
- **UI/UX Design**: Consistent modern UI with a comprehensive design system, shared Jinja2 components, GOJ branding, accessibility (WCAG 2.1 AA), and standardized workflow patterns. It features role-specific dashboards and comprehensive management modules for various entities (Event, Warehouse, User, etc.) with CRUD operations, validation, and optimistic locking.
- **Notification System**: Real-time in-app notifications with badge counters, offcanvas panels, deep-linking, read/unread tracking, and bulk operations.
- **Donation Processing**: Full workflow for donation management, including intake, verification, batch-level tracking, expiry date management, and integration with warehouse inventory. Automatic verification on acceptance is an MVP feature.
- **Database Architecture**: Based on a 40-table ODPEM schema, ensuring data consistency (uppercase varchars), auditability, precision (`DECIMAL(15,4)`), and optimistic locking across all tables. Features an enhanced `public.user` table, a new `itembatch` table for batch-level inventory (FEFO/FIFO), and a composite primary key for the `inventory` table.
- **Data Flow Patterns**: End-to-end AIDMGMT Relief Workflow, role-based dashboards, two-tier inventory management, eligibility approval, and package fulfillment with batch-level editing capabilities. Utilizes dedicated services like `ItemStatusService` and `InventoryReservationService`.
- **Role-Based Access Control (RBAC)**: Implemented via a centralized feature registry, dynamic navigation, security decorators, smart routing based on primary roles, and a defined role hierarchy. Specific CRUD operations are restricted by role (e.g., CUSTODIAN for item management).

## External Dependencies

### Required Database
- **PostgreSQL 16+** (production) with `citext` extension.
- **SQLite3** (development fallback).

### Python Packages
- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLAlchemy
- psycopg2-binary
- Werkzeug
- pandas
- python-dotenv

### Frontend CDN Resources
- Bootstrap 5.3.3 CSS/JS
- Bootstrap Icons 1.11.3
- Flatpickr (latest)