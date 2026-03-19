# Technical Specification Document
## Rockstar Beta Company Management System

**Document Version:** 1.0  
**Date:** March 2026  
**Project:** Company Management System (Rockstar Beta)  
**Technology Stack:** Django 5.2.7 | PostgreSQL | Python 3.x

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [System Architecture](#3-system-architecture)
4. [Application Modules](#4-application-modules)
5. [Database Models](#5-database-models)
6. [Key Features](#6-key-features)
7. [API & URL Structure](#7-api--url-structure)
8. [Authentication & Security](#8-authentication--security)
9. [Payroll Processing System](#9-payroll-processing-system)
10. [Attendance & Time Tracking](#10-attendance--time-tracking)
11. [Deployment Configuration](#11-deployment-configuration)

---

## 1. System Overview

The Rockstar Beta Company Management System is a comprehensive web-based ERP application built with Django framework. It provides integrated management for:

- **Human Resources** - Employee management, payroll processing, attendance tracking
- **Authentication & Authorization** - Role-based access control, login monitoring
- **Finance** - Financial tracking and reporting
- **Sales & Marketing** - Client and campaign management
- **KPI Tracking** - Performance metrics and analytics
- **Multi-Company Support** - Sub-company system management

### 1.1 Project Structure

```
company_system/
├── 0. master_dashboard/     # Master dashboard application
├── authentication/          # Authentication & authorization
├── employees/              # Employee management
├── finance/                # Finance module
├── human_resource/          # HR & Payroll core
├── kpi/                    # KPI tracking
├── marketing/              # Marketing management
├── master_dashboard/       # Main dashboard
├── sales/                  # Sales module
├── sub_company_system/     # Multi-company support
├── users/                  # User & staff management
├── templates/              # Global templates
└── theme/                  # Theme assets
```

---

## 2. Technology Stack

### 2.1 Backend

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Django | 5.2.7 |
| Database | PostgreSQL | - |
| ORM | Django ORM | Built-in |
| Authentication | Django Auth | Built-in |
| Template Engine | Django Templates | Built-in |

### 2.2 Python Dependencies

```
asgiref==3.10.0
beautifulsoup4==4.14.2
bs4==0.0.2
dj-database-url==3.0.1
Django==5.2.7
gunicorn==23.0.0
numpy==2.3.4
openpyxl==3.1.5
pandas==2.3.3
psycopg2==2.9.11
psycopg2-binary==2.9.11
python-dateutil==2.9.0
pytz==2025.2
whitenoise==6.11.0
```

### 2.3 Frontend

- **HTML5/CSS3** - Bootstrap-based templates
- **JavaScript** - jQuery for interactivity
- **Icons** - Font Awesome
- **Charts** - Chart.js for analytics

---

## 3. System Architecture

### 3.1 MVC Pattern

The system follows Django's MTV (Model-Template-View) architecture:

- **URL Routing (urls.py)** - Maps requests to views
- **Views (views.py)** - Business logic
- **Models (models.py)** - Database abstraction
- **Templates (HTML)** - Presentation layer

### 3.2 Multi-Tenant Design

The system supports multiple companies through:
- `sub_company_system` app for company separation
- Department-based data filtering
- Role-based access control per company

---

## 4. Application Modules

### 4.1 Authentication Module (`authentication/`)

**Purpose:** Handle user login, registration, and session management

**Key Components:**
- `models.py` - UserAccount, LoginHistory
- `views.py` - Login, logout, signup, department selection
- `forms.py` - Authentication forms
- `middleware.py` - Session and role validation
- `decorators.py` - Login required, role-based access

**Features:**
- Employee-based user accounts
- Password hashing with Django's hasher
- Login history tracking with IP/browser logging
- Role-based access control (RBAC)
- Department selection on login

### 4.2 Users Module (`users/`)

**Purpose:** Core staff/employee management

**Key Models:**
- `Staff` - Main employee model
- `StaffHistory` - Audit trail for changes
- `Role` - User roles
- `Department` - Organizational departments
- `Position` - Job positions

**Staff Fields:**
```
- Personal: first_name, middle_name, last_name, birthdate, age, sex
- Employment: employee_number, status, job_title, type, department, rank
- Schedule: shift (morning/afternoon/night/flexible)
- Government: sss_number, pagibig_number, philhealth_number
- Contact: email_address, phone_number, emergency_contact
- Tenure: start_date, tenure_active
```

### 4.3 Human Resource Module (`human_resource/`)

**Purpose:** Complete HR management including payroll

**Sub-modules:**
- Attendance tracking
- Leave management (Vacation/Sick leave)
- Payroll processing
- Bank account management
- Shift rules configuration

### 4.4 Employees Module (`employees/`)

**Purpose:** Employee-facing interface and self-service

**Features:**
- Employee dashboard
- Profile viewing and editing
- Attendance viewing

### 4.5 Finance Module (`finance/`)

**Purpose:** Financial tracking and reporting

### 4.6 Other Modules

| Module | Purpose |
|--------|---------|
| `kpi/` | Key Performance Indicators |
| `marketing/` | Marketing campaigns |
| `sales/` | Sales tracking |
| `master_dashboard/` | Executive dashboard |
| `0. master_dashboard/` | Alternative dashboard |

---

## 5. Database Models

### 5.1 Core Models Relationship

The system uses the following key relationships:

- Staff has one UserAccount (authentication)
- Staff has many Attendance records
- Staff has LeaveCredit and LeaveRequest records
- Staff has BankAccount for payroll
- Staff receives Payout records

### 5.2 Key Database Tables

#### Authentication Tables
- `UserAccount` - User credentials
- `LoginHistory` - Login audit trail

#### User Management Tables
- `Master_Employee` (Staff) - Employee records
- `users_role` - Roles
- `users_department` - Departments
- `users_position` - Positions

#### HR Tables
- `human_resource_attendance` - Daily attendance
- `human_resource_leavecredit` - Leave balances
- `human_resource_leaverequest` - Leave applications
- `human_resource_employeeshiftrule` - Shift rules
- `EmployeeProfileSettings` - Per-employee settings

#### Payroll Tables
- `BankType` - Banks list
- `BankAccount` - Employee bank accounts
- `PayrollRecord` - Payroll batches
- `Payout` - Individual employee payouts
- `PayrollOverride` - Manual adjustments
- `PayrollAuditLog` - Audit trail

---

## 6. Key Features

### 6.1 Authentication & Security

- **Password Management:** Django's PBKDF2 hasher
- **Session Management:** Custom middleware for role validation
- **Login Monitoring:** IP, browser, device tracking
- **Role-Based Access:** Permission system by role

### 6.2 Employee Management

- Employee CRUD operations
- Profile settings per employee
- Government ID tracking (SSS, Pag-IBIG, PhilHealth)
- Employment status tracking
- Department and position assignment
- Staff history tracking

### 6.3 Attendance System

- Clock in/out recording
- Multiple status tracking (present, late, absent, early leave)
- Late minutes calculation
- Overtime hours tracking
- Night Shift Differential (NSD) hours
- Lunch break tracking
- Manual attendance entry
- HR notes/adjustments

### 6.4 Leave Management

- Vacation Leave (VL) and Sick Leave (SL) tracking
- Leave credit allocation
- Leave request submission
- Approval workflow
- Half-day leave support
- Leave balance calculation

### 6.5 Payroll Processing

- Cutoff-based payroll (1st and 2nd cutoff)
- Monthly payroll cycles
- Gross pay calculation
- Additions (allowances, bonuses, overtime)
- Deductions (loans, absences, late)
- Net pay computation
- Bank account integration
- Payslip generation
- Payroll finalization workflow
- Release tracking

---

## 7. API & URL Structure

### 7.1 Authentication URLs

| URL | View | Description |
|-----|------|-------------|
| `/accounts/login/` | `login_view` | User login |
| `/accounts/logout/` | `logout_view` | User logout |
| `/accounts/signup/` | `signup_view` | User registration |
| `/accounts/select-department/` | `select_department` | Department selection |

### 7.2 HR URLs

| URL | Description |
|-----|-------------|
| `/hr/dashboard/` | HR main dashboard |
| `/hr/attendance/` | Attendance list |
| `/hr/attendance/add/` | Add attendance |
| `/hr/attendance/clock/` | Clock in/out |
| `/hr/leave/` | Leave management |
| `/hr/payroll/` | Payroll list |
| `/hr/payroll/process/` | Process payroll |
| `/hr/payroll/finalize/` | Finalize payroll |

### 7.3 Employee URLs

| URL | Description |
|-----|-------------|
| `/employees/dashboard/` | Employee dashboard |
| `/employees/profile/` | View profile |
| `/employees/attendance/` | View attendance |

---

## 8. Authentication & Security

### 8.1 User Account Model

```python
class UserAccount(models.Model):
    employee = OneToOneField(Staff)
    password = CharField(max_length=255)  # Hashed
    is_active = BooleanField(default=True)
    created_at = DateTimeField
    last_login = DateTimeField
```

### 8.2 Login History Tracking

Records:
- Employee reference
- Login timestamp
- IP address
- Browser (User-Agent)
- Status (success/failed)
- Failure reason

### 8.3 Security Features

- Password hashing using Django's default hasher
- Session timeout handling
- Role-based permission checks
- Active/inactive account status
- Login attempt tracking

---

## 9. Payroll Processing System

### 9.1 Payroll Flow

1. **Create Payroll Batch** - Select Cutoff/Month
2. **Calculate Employee Payouts** - Automatic computation
3. **Preview Payroll** - Review calculations
4. **Review & Adjust** - Manual overrides if needed
5. **Finalize Payroll** - Lock the payroll
6. **Release Payments** - Mark as released
7. **Generate Payslips** - Create PDF payslips

### 9.2 Payroll Models

#### PayrollRecord
- Cutoff selection (1st/2nd)
- Month and year
- Finalized status
- Created by user

#### Payout (per employee per cutoff)
- Employee reference
- Gross pay
- Total additions
- Total deductions
- Net pay
- Bank account
- Released status
- Payslip file

#### PayrollOverride
- Tracks manual adjustments
- Original vs override values
- Reason for change

### 9.3 Payroll Settings

Comprehensive settings in `payroll_settings_models.py`:
- Salary settings per employee
- Government contribution rates
- Tax tables
- Deduction types
- Benefit types
- Loan types
- De minimis types
- Leave encashment rates

---

## 10. Attendance & Time Tracking

### 10.1 Attendance Model

```python
class Attendance(models.Model):
    employee = ForeignKey(Staff)
    date = DateField
    clock_in = TimeField
    clock_out = TimeField
    statuses = CharField  # Multi-select
    lunch_in = TimeField
    lunch_out = TimeField
    hours_worked = DecimalField
    late_minutes = IntegerField
    ot_hours = DecimalField
    nsd_hours = DecimalField
    note = TextField
```

### 10.2 Attendance Statuses

- `present` - Present
- `late` - Late arrival
- `absent` - Absent
- `early_leave` - Early departure
- `failed_to_clock_out` - Missing clock out
- `missing_lunch` - Missing lunch break

### 10.3 Shift Rules

```python
class EmployeeShiftRule(models.Model):
    shift = CharField  # morning/afternoon/night/flexible
    rank = CharField  # rank_and_file/supervisory/managerial
    clock_in_start = TimeField
    clock_out = TimeField
    lunch_start = TimeField
    lunch_end = TimeField
    lunch_required = BooleanField
    total_hours = DecimalField
    nsd_applicable = BooleanField
```

---

## 11. Deployment Configuration

### 11.1 Production Setup

**Web Server:** Gunicorn
```bash
gunicorn company_system.wsgi:application
```

**Static Files:** WhiteNoise
- Enabled in settings.py
- Storage for compressed static assets

**Database:** PostgreSQL
- Using psycopg2 driver
- dj-database-url for connection string

### 11.2 Environment Variables

Required configurations:
- `DATABASE_URL` - PostgreSQL connection
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode flag
- `ALLOWED_HOSTS` - Allowed domains

### 11.3 Management Commands

- `python manage.py migrate` - Database migrations
- `python manage.py createsuperuser` - Admin account
- `python manage.py collectstatic` - Static files
- Custom command: `mark_absent` - Auto-mark absent employees

---

## Appendix: Code Statistics

| Metric | Value |
|--------|-------|
| Total Django Apps | 12+ |
| Models | 40+ |
| Views | 100+ |
| Templates | 50+ |
| URL Patterns | 200+ |

---

**Document End**

*This technical specification provides an overview of the Rockstar Beta Company Management System architecture and components.*
