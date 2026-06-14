# Logbook Application Navigation Guide

## Quick Start

1. **Start the application:**
   ```bash
   cd /workspace/logbook
   python run.py
   ```

2. **Open browser:** `http://localhost:5000`

3. **You will land on the Login page automatically**

---

## User Roles & Navigation Flow

### 1. Superadmin (Highest Privilege)
**Credentials:** `superadmin` / `admin123`

**Navigation Flow:**
```
Login → Superadmin Dashboard
```

**What you can do:**
- Create Units (military-style organizational units)
- Assign Unit Admins to Units
- Approve/Deny pending Unit Admin requests
- Reset Unit passcodes
- Delete Units (if no admins assigned)

**Pages accessible:**
- `/superadmin` - Main dashboard for managing Units and Unit Admins

---

### 2. Unit Admin
**Credentials:** Register via Login page → Register (need Unit passcode)

**Navigation Flow:**
```
Login → Unit Admin Dashboard
```

**What you can do:**
- Create Companies under your Unit
- Assign Company Admins to Companies
- Approve/Deny pending Company Admin requests
- Reset Company passcodes
- Delete Companies (if no admins assigned)

**Pages accessible:**
- `/unit_admin` - Main dashboard for managing Companies and Company Admins

---

### 3. Company Admin / Manager / Regular User
**Credentials:** Register via Login page → Register (need Unit + Company passcode)

**Navigation Flow:**
```
Login → Main Dashboard
```

**Top Navigation Bar (appears after login):**

| Menu | Options | Description |
|------|---------|-------------|
| **Vehicles** | • My Vehicles<br>• Vehicles in Transit | View company vehicles or vehicles being transferred |
| **Tasks** | • My Tasks<br>• My History<br>• Company History | View assigned tasks, completed entries, or all company logs |
| **Company** | • View Members | See all users in your company with their assigned vehicles |
| **Admin** (Admins only) | • Approve Users | Approve pending company admin requests |
| **Logout** | - | Sign out |

---

## Page-by-Page Navigation Map

### Authentication Pages
| Page | URL | Access |
|------|-----|--------|
| Login | `/login` | Public (redirects here from `/`) |
| Register | `/register` | Public |
| Logout | `/logout` | Logged-in users |

### Superadmin Pages
| Page | URL | How to Access |
|------|-----|---------------|
| Superadmin Dashboard | `/superadmin` | Auto-redirect after login as superadmin |

### Unit Admin Pages
| Page | URL | How to Access |
|------|-----|---------------|
| Unit Admin Dashboard | `/unit_admin` | Auto-redirect after login as unit_admin |

### Company/User Pages
| Page | URL | How to Access |
|------|-----|---------------|
| Main Dashboard | `/dashboard` | Auto-redirect after login OR click "My Vehicles" |
| Vehicle Details | `/vehicle/<plate>` | Click vehicle license plate on dashboard |
| Logbook Entry | `/logbook/<plate>` | From vehicle details page |
| Add Fault | `/vehicle/<plate>/faults/add` | From vehicle details page |
| View Faults | `/vehicle/<plate>/faults` | From vehicle details page |
| My Tasks | `/my_tasks` | Top nav: Tasks → My Tasks |
| Completed Tasks | `/completed_tasks` | Top nav: Tasks → My History |
| Company Tasks | `/company_tasks` | Top nav: Tasks → Company History |
| Company List | `/company_list` | Top nav: Company → View Members |
| Vehicles in Transit | `/vehicles/transit` | Top nav: Vehicles → Vehicles in Transit |

---

## Testing Checklist

### For Superadmin:
- [ ] Login with `superadmin`/`admin123`
- [ ] Create a new Unit
- [ ] Reset Unit passcode
- [ ] (After Unit Admin registers) Approve Unit Admin

### For Unit Admin:
- [ ] Register with Unit passcode
- [ ] Wait for Superadmin approval
- [ ] Login → Create a Company
- [ ] Reset Company passcode
- [ ] (After Company Admin registers) Approve Company Admin

### For Company Admin:
- [ ] Register with Unit + Company passcode
- [ ] Wait for Unit Admin approval
- [ ] Login → View Dashboard
- [ ] Add Vehicle Type
- [ ] Add Store
- [ ] Add Vehicle
- [ ] Navigate to vehicle details
- [ ] Create logbook entry
- [ ] Assign task to user (from Company List)
- [ ] View Company Tasks history

### For Regular User:
- [ ] Login
- [ ] View Dashboard
- [ ] View My Tasks
- [ ] Complete a task (by creating matching logbook entry)
- [ ] View My History

---

## Common Issues & Solutions

### "I can't see any pages after login"
- Check your user role in the database
- Superadmin → redirects to `/superadmin`
- Unit Admin → redirects to `/unit_admin`
- Others → redirects to `/dashboard`

### "I registered but can't login"
- Your account needs approval
- Superadmin approves Unit Admins
- Unit Admin approves Company Admins/Users

### "I don't see the navigation bar"
- Ensure you're logged in
- Navigation bar only appears for authenticated users
- Check `taskbar.html` is being extended by your template

### "BuildError: Could not build url"
- All endpoints are now properly registered
- Clear Flask cache and restart if needed

---

## Database Seeding Info

Default seeded data includes:
- **Superadmin:** `superadmin` / `admin123`
- **Unit:** First Battalion
- **Company:** Alpha Company
- **Vehicle Type:** Bronco Carrier
- **Store:** A-Bay Store
- **Vehicle:** MID1234X

Use these to test the full navigation flow immediately.
