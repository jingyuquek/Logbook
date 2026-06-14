# Vehicle Logbook Application - Testing & Navigation Guide

## Quick Start

```bash
cd /workspace/logbook
python run.py
```

Access the app at: http://localhost:5000

## Default Credentials

| Role | Username | Password | Notes |
|------|----------|----------|-------|
| Superadmin | superadmin | admin123 | Full system access |
| Unit Admin | (register new) | (your choice) | Requires unit passcode |
| Company Admin | (register new) | (your choice) | Requires company passcode |
| User | (register new) | (your choice) | Requires approval |

---

## Seeded Test Data

After running the seeder, you'll have:
- **Unit**: First Battalion (passcode: `unit123`)
- **Company**: Alpha Company (passcode: `alpha123`)
- **Vehicle Type**: Bronco Carrier
- **Store**: A-Bay Store
- **Vehicle**: MID1234X

---

## Navigation Flow by Role

### 1. Superadmin Flow (`/superadmin`)

**Purpose**: Create units, approve unit admins, manage system-wide settings

**Endpoints**:
- `GET /superadmin` - Dashboard
- `POST /superadmin` - Add new unit
- `POST /approve_unit_admin` - Approve pending unit admin
- `POST /remove_unit_admin` - Remove unit admin
- `POST /reset_unit_passcode` - Reset unit passcode
- `POST /remove_unit` - Delete unit (if no admins assigned)
- `POST /deny_unit_admin` - Reject unit admin request

**UI Actions**:
1. Login as `superadmin` / `admin123`
2. View all units and their admins
3. Add new units with name + passcode
4. Approve/deny pending unit admin requests
5. Remove problematic unit admins

---

### 2. Unit Admin Flow (`/unit_admin`)

**Purpose**: Create companies under unit, approve company admins

**Endpoints**:
- `GET /unit_admin` - Dashboard
- `POST /unit_admin` - Add new company
- `POST /approve_company_admin` - Approve company admin
- `POST /deny_company_admin` - Reject company admin request
- `POST /remove_company_admin` - Remove company admin
- `POST /reset_company_passcode` - Reset company passcode
- `POST /remove_company` - Delete company

**UI Actions**:
1. Register as unit_admin (requires unit passcode)
2. Wait for superadmin approval
3. Login → Access unit admin dashboard
4. Create companies under your unit
5. Approve company admin requests

---

### 3. Company Admin Flow (`/dashboard`)

**Purpose**: Manage vehicles, stores, users, tasks within company

**Main Dashboard Endpoints**:
- `GET /dashboard` - View vehicles by type
- `POST /add_vehicle_type` - Create vehicle category
- `POST /remove_vehicle_type` - Delete vehicle category
- `POST /add_store` - Add parking bay/store
- `POST /edit_store/<id>` - Rename store
- `POST /remove_store` - Delete store
- `GET /move_store/<id>/<up|down>` - Reorder stores
- `POST /add_vehicle` - Add vehicle to store
- `POST /remove_vehicle` - Remove vehicle from company
- `POST /move_vehicle_store` - Move vehicle between stores
- `POST /add_type_extinguisher` - Add default extinguisher requirement
- `POST /delete_type_extinguisher/<id>` - Remove extinguisher requirement

**User Management**:
- `GET /company_list` - View all company members
- `POST /assign-task` - Assign task to user(s)

**Task Management**:
- `GET /company_tasks` - View all company logbook entries (with filters)
- `POST /delete_task/<id>` - Delete task entry

**Vehicle Detail Endpoints** (via `/vehicle/<plate>`):
- `POST /update_pol_level/<vehicle_id>` - Update fuel level
- `POST /toggle_vor/<vehicle_id>` - Mark VOR/Operational
- `POST /vehicle/<id>/genrun` - Record generator run
- `POST /vehicle/<id>/update_shutter` - Set shutter number
- `POST /vehicle/<id>/initiate_handover` - Start transfer to another company
- `POST /add_extinguisher/<vehicle_id>` - Add fire extinguisher
- `POST /extinguisher/<id>/delete` - Remove extinguisher

**Fault Management**:
- `GET /vehicle/<plate>/faults` - View faults
- `GET /vehicle/<plate>/faults/add` - Report new fault
- `POST /vehicle/<plate>/faults/add` - Submit fault report

**Logbook**:
- `GET /logbook/<plate>` - View/create logbook entries
- `POST /logbook/<plate>` - Submit logbook entry
- `POST /delete_logbook_entry/<id>` - Delete entry (admin only)

**UI Actions**:
1. Register as admin/manager/user (requires company passcode)
2. Wait for unit admin approval
3. Login → Access company dashboard
4. Manage vehicle types, stores, and vehicles
5. Assign tasks to drivers
6. Review company history and logs

---

### 4. Regular User Flow

**Purpose**: View assigned tasks, create logbook entries, view personal history

**Endpoints**:
- `GET /my_tasks` - View pending tasks
- `POST /complete_task/<id>` - Complete task (requires matching logbook entry)
- `GET /completed_tasks` - View personal logbook history
- `GET /logbook/<plate>` - Create logbook entry for assigned vehicle

**UI Actions**:
1. Register and wait for approval
2. Login → See dashboard
3. Check "My Tasks" for assignments
4. Complete tasks by creating logbook entries
5. View personal history in "My History"

---

### 5. Vehicle Transfer Flow (Inter-Company)

**Purpose**: Transfer vehicles between companies using OTP tokens

**Endpoints**:
- `GET /vehicles/transit` - View incoming/outgoing vehicles and active tokens
- `POST /generate_handover_token` - Generate 12-hour OTP for vehicle type
- `POST /vehicle/<id>/initiate_handover` - Start transfer (requires OTP)
- `POST /reject_handover/<id>` - Reject incoming vehicle
- `POST /cancel_handover/<id>` - Cancel outgoing transfer

**UI Actions**:
1. Admin generates token for specific vehicle type
2. Share OTP with receiving company
3. Receiving company enters OTP to initiate handover
4. Sending company sees vehicle in "outgoing"
5. Receiving company sees vehicle in "incoming"
6. Process takeover or reject transfer

---

## All Endpoints Reference

### Authentication (`auth` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Redirect to login |
| GET/POST | `/login` | User login |
| GET/POST | `/register` | User registration |
| GET | `/logout` | Logout |

### Admin (`admin` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/superadmin` | Superadmin dashboard |
| POST | `/approve_unit_admin` | Approve unit admin |
| POST | `/remove_unit_admin` | Remove unit admin |
| POST | `/reset_unit_passcode` | Reset unit passcode |
| POST | `/remove_unit` | Delete unit |
| POST | `/deny_unit_admin` | Deny unit admin request |
| GET/POST | `/unit_admin` | Unit admin dashboard |
| POST | `/approve_company_admin` | Approve company admin |

### Core (`core` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Main company dashboard |

### Assets (`assets` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/add_vehicle` | Add vehicle |
| POST | `/move_vehicle` | Move vehicle (API) |
| POST | `/reorder_vehicles` | Reorder vehicles (API) |
| POST | `/add_store` | Add store |
| POST | `/vehicle/<id>/add_extinguisher` | Add extinguisher |
| POST | `/extinguisher/<id>/delete` | Delete extinguisher |
| POST | `/add_type_extinguisher` | Add type extinguisher template |
| POST | `/delete_type_extinguisher/<id>` | Delete type extinguisher |
| POST | `/add_vehicle_type` | Add vehicle type |
| POST | `/remove_vehicle_type` | Remove vehicle type |
| GET | `/move_store/<id>/<direction>` | Move store position |
| POST | `/remove_vehicle` | Remove vehicle |
| POST | `/remove_store` | Remove store |
| POST | `/edit_store/<id>` | Edit store name |
| POST | `/move_vehicle_store` | Move vehicle to different store |

### Logbook (`logbook` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vehicle/<plate>` | View vehicle details |
| POST | `/update_pol_level/<id>` | Update POL level |
| POST | `/toggle_vor/<id>` | Toggle VOR status |
| POST | `/vehicle/<id>/genrun` | Record gen run |
| GET/POST | `/logbook/<plate>` | View/create logbook entries |
| GET | `/api/vehicle/<id>/last_values` | Get last values (API) |
| POST | `/delete_logbook_entry/<id>` | Delete logbook entry |

### Faults (`faults` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vehicle/<plate>/faults` | View faults |
| GET/POST | `/vehicle/<plate>/faults/add` | Add fault |
| POST | `/vehicle/<id>/update_shutter` | Update shutter number |

### Tasks (`tasks` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/company_list` | Company personnel list |
| POST | `/assign-task` | Assign task |
| GET | `/my_tasks` | User's pending tasks |
| GET | `/completed_tasks` | User's completed tasks |
| GET | `/company_tasks` | Company-wide task history |
| POST | `/complete_task/<id>` | Complete task |
| POST | `/delete_task/<id>` | Delete task |

### Transfer (`transfer` blueprint)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/vehicle/<id>/initiate_handover` | Start handover |
| GET | `/vehicles/transit` | Transit hub view |
| POST | `/generate_handover_token` | Generate OTP token |
| POST | `/reject_handover/<id>` | Reject handover |
| POST | `/cancel_handover/<id>` | Cancel handover |

---

## Testing Checklist

### Superadmin Tests
- [ ] Login with superadmin credentials
- [ ] Create new unit with passcode
- [ ] View pending unit admin requests
- [ ] Approve unit admin
- [ ] Remove unit admin
- [ ] Reset unit passcode
- [ ] Remove empty unit

### Unit Admin Tests
- [ ] Register as unit admin (with unit passcode)
- [ ] Wait for superadmin approval
- [ ] Login and access unit admin dashboard
- [ ] Create new company with passcode
- [ ] Approve company admin request
- [ ] Remove company admin
- [ ] Reset company passcode

### Company Admin Tests
- [ ] Register as company admin (with company passcode)
- [ ] Wait for unit admin approval
- [ ] Login and see company dashboard
- [ ] Add vehicle type
- [ ] Add store to vehicle type
- [ ] Reorder stores (up/down)
- [ ] Edit store name
- [ ] Add vehicle to store
- [ ] Move vehicle between stores
- [ ] Remove vehicle
- [ ] Remove store
- [ ] Add extinguisher template to vehicle type
- [ ] View vehicle details
- [ ] Update POL level
- [ ] Toggle VOR status
- [ ] Record generator run
- [ ] Update shutter number
- [ ] Add fire extinguisher to vehicle
- [ ] Delete fire extinguisher
- [ ] Remove vehicle type

### User Tests
- [ ] Register as regular user
- [ ] Wait for approval
- [ ] Login and see dashboard
- [ ] View company member list
- [ ] Receive task assignment
- [ ] View "My Tasks"
- [ ] Create logbook entry for task
- [ ] Complete task (auto-verifies with logbook)
- [ ] View "My History" (completed tasks)

### Logbook Tests
- [ ] Navigate to vehicle detail page
- [ ] Click "Add Logbook Entry"
- [ ] Fill in location, meter reading, POSO
- [ ] Enter start/end times (HHMM format)
- [ ] Enter moving/stationary time
- [ ] Submit entry (validates time conflicts)
- [ ] View entry in vehicle history
- [ ] Admin deletes logbook entry

### Fault Tests
- [ ] Navigate to vehicle faults page
- [ ] Click "Add Fault"
- [ ] Enter fault description
- [ ] Submit fault report
- [ ] View fault in vehicle fault list
- [ ] Verify fault number increments

### Transfer Tests
- [ ] Admin generates handover token for vehicle type
- [ ] Note the OTP code
- [ ] Initiate handover for specific vehicle (enter OTP)
- [ ] Verify vehicle appears in "outgoing" for sender
- [ ] Verify vehicle appears in "incoming" for receiver
- [ ] Receiver processes takeover
- [ ] OR reject/cancel handover

---

## Common Issues & Solutions

### BuildError: Could not build url for endpoint
**Cause**: Missing route definition or wrong blueprint prefix
**Solution**: Check if route is registered in correct blueprint

### Template not found
**Cause**: Template file missing or wrong path
**Solution**: Ensure template exists in `/app/templates/`

### Database locked
**Cause**: SQLite database in use
**Solution**: Stop running app, remove `app.db`, restart

### Session expires
**Cause**: Browser session cleared
**Solution**: Re-login

---

## File Structure

```
logbook/
├── run.py                 # Application entry point
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── config.py          # Configuration settings
│   ├── models.py          # SQLAlchemy models
│   ├── seed.py            # Database seeding script
│   ├── routes/
│   │   ├── auth.py        # Authentication routes
│   │   ├── admin.py       # Admin management routes
│   │   ├── core.py        # Dashboard routes
│   │   ├── assets.py      # Vehicle/store management
│   │   ├── logbook.py     # Logbook entry routes
│   │   ├── faults.py      # Fault reporting routes
│   │   ├── tasks.py       # Task management routes
│   │   └── transfer.py    # Vehicle transfer routes
│   └── templates/
│       ├── base.html              # Base template
│       ├── login.html             # Login page
│       ├── register.html          # Registration page
│       ├── dashboard.html         # Company dashboard
│       ├── view_vehicle.html      # Vehicle detail page
│       ├── logbook.html           # Logbook entry form
│       ├── my_tasks.html          # User tasks
│       ├── company_list.html      # Company members
│       ├── superadmin_dashboard.html
│       ├── unit_admin_dashboard.html
│       └── ... (other templates)
```

---

## API Endpoints (JSON responses)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/move_vehicle` | POST | Move vehicle between stores |
| `/reorder_vehicles` | POST | Reorder vehicles in store |
| `/api/vehicle/<id>/last_values` | GET | Get last logbook values |

---

## Notes

- All times are in Singapore Time (SGT, UTC+8)
- Generator runs expire after 14 days
- Handover tokens expire after 12 hours
- Users need approval before accessing system (except superadmin)
- Vehicle transfers require matching vehicle type on OTP token
