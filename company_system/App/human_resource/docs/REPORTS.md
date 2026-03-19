# HR/Payroll System Reports Documentation

This document provides comprehensive documentation for all reports available in the Rockstar HR/Payroll System. It includes technical details for developers, user guides for end users, and management summaries with key metrics.

---

## Table of Contents

1. [Payroll Reports](#1-payroll-reports)
2. [Attendance Reports](#2-attendance-reports)
3. [Leave Reports](#3-leave-reports)
4. [Employee/User Reports](#4-employeeuser-reports)
5. [Loan Reports](#5-loan-reports)
6. [Export Capabilities](#6-export-capabilities)
7. [URL Reference](#7-url-reference)

---

## 1. Payroll Reports

### 1.1 Payroll History List

**URL:** `/hr_dashboard/payroll-settings/history/`

**Purpose:** View historical payroll records with summary statistics.

**User Access:** HR Dashboard → Payroll Settings → Payroll History

**Filters Available:**
- Year (dropdown - current year ±3 years)
- Month (dropdown - January through December)

**Summary Metrics (Key Management Indicators):**
| Metric | Description |
|--------|-------------|
| Total Payroll Months | Number of payroll periods processed |
| Total Gross | Sum of all gross salaries for filtered period |
| Total Net | Sum of all net salaries for filtered period |

**Data Fields:**
- Payroll Period (Year/Month)
- Cutoff (1st or 2nd Cutoff)
- Number of Employees
- Total Gross (per cutoff)
- Total Deductions (per cutoff)
- Total Net (per cutoff)

**Grouping:** Data is grouped by Year/Month with expandable cutoff details.

---

### 1.2 Payroll History Detail

**URL:** `/hr_dashboard/payroll-settings/history/<pk>/`

**Purpose:** Detailed view of a specific payroll period.

**Access:** Click on any period from Payroll History List

**Summary Metrics:**
| Metric | Description |
|--------|-------------|
| Period | Month, Year, and Cutoff |
| Total Employees | Count of employees in this payroll |
| Total Gross | Sum of all gross salaries |
| Total Net | Sum of all net salaries |

**Employee Payout Table Fields:**
- Employee Name
- Employee ID
- Department
- Gross Pay
- Total Deductions
- Net Pay
- Release Status (Released/Unreleased)

---

### 1.3 Payout List

**URL:** `/hr_dashboard/payout/`

**Purpose:** View all employee payouts with filtering and export capabilities.

**User Access:** HR Dashboard → Payouts

**Filters Available:**
- Year (dropdown)
- Month (dropdown)
- Department (dropdown - dynamically filters employees)
- Employee (dropdown)
- Status (Finalized/Draft)
- Release Status (Released/Unreleased)

**Summary Metrics:**
| Metric | Description |
|--------|-------------|
| Total Earnings | Sum of all earnings including basic salary, tips, incentives |
| Total De Minimis | Sum of all de minimis benefits |
| Total Gross | Sum of gross pay |
| Total Deductions | Sum of all deductions |
| Total Net | Sum of all net pay |

**Actions:**
- Add new Batch Payroll
- Add new Individual Payroll
- Export to CSV

---

### 1.4 Payout Detail

**URL:** `/hr_dashboard/payout/<pk>/`

**Purpose:** Complete breakdown of a single employee payout.

**Employee Information Section:**
- Name
- Employee ID
- Period (Month/Year - Cutoff)
- Status (Finalized/Draft)

**Earnings Breakdown:**
| Field | Description |
|-------|-------------|
| Basic Salary | Base salary for the period |
| Tips/Others | Additional tips or other earnings |
| Lodging Allowance | Housing or lodging benefit |
| Incentives | Performance incentives |
| Holiday Pay | Pay for holiday worked |
| Holiday Hours | Hours worked on holidays |
| Regular Holiday Pay | Pay for regular holidays |
| Overtime Pay | Additional hours worked |
| Night Shift Differential | Pay for night shift work |

**Deductions Breakdown:**
| Field | Description |
|-------|-------------|
| Withholding Tax | Tax deducted at source |
| Late Minutes | Deduction for tardiness |
| Late Deduction | Peso value of late minutes |
| Days Absent | Number of days absent |
| Absence Deduction | Peso value of absent days |
| SSS Contribution | Social Security System |
| PhilHealth | Philippine Health Insurance |
| Pag-IBIG | Home Development Mutual Fund |

**Government Contributions:**
- SSS Contribution
- PhilHealth
- Pag-IBIG

**De Minimis Section:**
- Total De Minimis Benefits
- Individual de minimis entries

**Summary:**
- Gross Pay
- Total Deductions
- **NET PAY** (highlighted in green)

**Actions:**
- Download PDF
- Edit (if unfinalized)
- Finalize (if unfinalized)
- Delete (if unfinalized)
- Unfinalize (if finalized)

---

### 1.5 Individual Payroll

**URL:** `/hr_dashboard/payroll/individual/`

**Purpose:** Process payroll for a single employee.

**Features:**
- Select Employee
- Select Month/Year
- Select Cutoff (1st: Days 1-15, 2nd: Days 16-End)
- View attendance summary
- Adjust earnings, deductions, incentives
- Real-time calculation of gross and net pay

**Attendance Summary Metrics:**
- Total Days Worked
- Total Hours Worked
- Late Minutes
- Days Absent
- Overtime Hours
- Night Hours

---

### 1.6 Batch Payroll Preview

**URL:** `/hr_dashboard/payroll/batch-preview/`

**Purpose:** Process payroll for multiple employees at once.

**Features:**
- Filter by department/employee
- Select cutoff period
- Preview all employee payrolls
- Individual adjustment per employee
- Bulk finalize option

---

### 1.7 Payroll Finalize

**URL:** `/hr_dashboard/payroll/finalize/`

**Purpose:** Finalize processed payroll to lock records.

**Features:**
- Review all pending payouts
- Confirm finalization
- Generate payroll records

---

## 2. Attendance Reports

### 2.1 Attendance List

**URL:** `/hr_dashboard/attendance/`

**Purpose:** View and manage employee attendance records.

**User Access:** HR Dashboard → Attendance Management → Attendance View

**Filters Available:**
- Search Employee (by name)
- Date From
- Date To
- Department
- Status (multi-select)

**Status Options:**
- Present
- Absent
- Late
- On Leave
- Failed to Clock Out
- Early Leave
- Overlunch Pending
- Missing Lunch

**Summary Metrics (Dashboard Cards):**
| Metric | Description |
|--------|-------------|
| Total Records | Total attendance records displayed |
| Present | Number of employees present |
| Absent | Number of employees absent |
| Late | Number of employees who arrived late |
| On Leave | Number of employees on leave |
| Failed Clock Out | Employees who forgot to clock out |
| Overlunch Pending | Employees with overlunch issues |
| Missing Lunch | Employees without lunch clock |

**Data Fields per Record:**
- Employee Name
- Department
- Position
- Status (with color-coded badges)
- Date
- Clock In Time
- Clock Out Time
- Hours Worked
- Late Minutes
- Lunch In/Out times
- Actions (Edit, View History)

**Export Options:**
- Print Report
- Export to CSV

---

### 2.2 Attendance Clock / History

**URL:** `/hr_dashboard/attendance/clock/`

**Purpose:** Employee self-service clock in/out and view personal attendance history.

**Features:**
- Clock In button
- Clock Out button
- Today's attendance summary
- Attendance history table

---

## 3. Leave Reports

### 3.1 Leave Request List

**URL:** `/hr_dashboard/leave-requests/`

**Purpose:** View and manage employee leave requests.

**User Access:** HR Dashboard → Leave Requests

**Filters Available:**
- Search (employee name)
- Leave Type (Vacation Leave/Sick Leave)
- Status (Pending/Approved/Disapproved)
- Credits Year

**Summary Metrics:**
| Metric | Description |
|--------|-------------|
| Total Requests | Total leave requests in filtered view |
| Pending | Requests awaiting approval |
| Approved | Requests approved |
| Disapproved | Requests rejected |

**Status Colors:**
- Pending: Yellow/Amber
- Approved: Green
- Disapproved: Red

**Data Fields:**
- Employee Name
- Leave Type
- Start Date
- End Date
- Total Days
- Purpose/Reason
- Status
- Credits Year
- Actions (Approve, Disapprove, Edit, Delete)

---

### 3.2 Leave Credit List

**URL:** `/hr_dashboard/leave-credits/`

**Purpose:** View and manage employee leave credits.

**User Access:** HR Dashboard → Leave Credits

**Filters Available:**
- Year
- Leave Type (Vacation Leave/Sick Leave)
- Search Employee

**Summary Metrics:**
| Metric | Description |
|--------|-------------|
| Total Records | Total leave credit records |
| Vacation Leave Days | Sum of all VL remaining |
| Sick Leave Days | Sum of all SL remaining |
| Low Credits | Employees with less than 2 days remaining |

**Alerts:**
- **Low Leave Credits Warning** (Yellow): Employees with less than 2 days remaining
- **No Leave Credits Available** (Red): Employees with 0 days remaining

**Data Fields:**
- Employee Name
- Leave Type (VL/SL)
- Year
- Total Days Allocated
- Days Used
- Days Remaining
- Actions (Edit, View Requests)

---

## 4. Employee/User Reports

### 4.1 User Management

**URL:** `/hr_dashboard/user-mgnt/`

**Purpose:** Manage employee user accounts and roles.

**User Access:** HR Dashboard → User Management

**Summary Metrics:**
| Metric | Description |
|--------|-------------|
| Total Users | Total number of user accounts |
| Active Users | Number of active accounts |
| Departments | Number of departments |
| Roles Assigned | Number of roles in system |

**Data Fields:**
- Employee Name
- Username
- Email
- Role
- Status (Active/Inactive)
- Actions (Edit, Delete, Change Role)

**Features:**
- Add new user/employee
- Edit user details
- Change user role
- Delete user

---

### 4.2 Employee List

**URL:** `/hr_dashboard/employees/`

**Purpose:** View list of all employees in the system.

**Data Fields:**
- Employee Number
- First Name
- Last Name
- Department
- Position
- Employment Status

---

### 4.3 Employee Profile

**URL:** `/hr_dashboard/employees/<employee_id>/`

**Purpose:** Detailed view of employee information.

**Sections:**
- Personal Information
- Employment Details
- Contact Information
- Department Assignment
- Position

---

### 4.4 Staff History / Employee History

**URL:** `/hr_dashboard/dashboard/staff-history/`

**Purpose:** Track all staff profile changes and modifications.

**User Access:** HR Dashboard → Employee History

**Filters Available:**
- Employee (dropdown)
- Field (dropdown - what was changed)
- Start Date
- End Date

**Field Change Options:**
- Department
- Position
- Salary
- Role
- Status

**Data Fields:**
- Date & Time of Change
- Employee Name
- Field Changed
- Old Value
- New Value
- Changed By (User)

---

## 5. Loan Reports

### 5.1 Loan List

**URL:** `/hr_dashboard/loans/`

**Purpose:** View and manage employee loans.

**User Access:** HR Dashboard → Loans

**Data Fields:**
| Field | Description |
|-------|-------------|
| Employee | Name of employee with loan |
| Employee ID | Unique employee identifier |
| Principal | Original loan amount |
| Balance | Remaining balance to pay |
| Term | Loan term in months |
| Start Date | When loan started |
| Status | Loan status (Pending/Approved/Disapproved/Closed) |

**Status Options:**
- Pending: Yellow badge
- Approved: Green badge
- Disapproved: Red badge
- Closed: Gray badge

**Actions:**
- Add new loan
- Edit loan
- View loan details
- Update status (quick dropdown)

---

### 5.2 Loan Detail

**URL:** `/hr_dashboard/loans/<pk>/`

**Purpose:** Complete breakdown of a loan.

**Sections:**
- Loan Information (Principal, Interest Rate, Term)
- Payment Schedule
- Payment History
- Current Balance

---

## 6. Export Capabilities

### 6.1 CSV Export - Payouts

**URL:** `/hr_dashboard/payout/export-csv/`

**Purpose:** Export payout data to CSV for external analysis.

**Export Includes:**
- All filtered payout records
- Employee information
- Gross, deductions, and net amounts
- Status information

**Usage:** Click "Export CSV" button on Payout List page with desired filters applied.

---

### 6.2 CSV Export - Attendance

**Purpose:** Export attendance records to CSV.

**Usage:** Click "Export CSV" button on Attendance List page with desired filters applied.

---

### 6.3 PDF Generation - Payslip

**URL:** `/hr_dashboard/payout/<payout_id>/pdf/`

**Purpose:** Generate individual employee payslips in PDF format.

**PDF Contents:**
- Company Header
- Employee Information
- Period Covered
- Earnings Breakdown
- Deductions Breakdown
- Government Contributions
- Summary (Gross, Deductions, Net)
- Authorized Signatures section

---

### 6.4 Print Functionality

All list views include print functionality for quick physical copies.

---

## 7. URL Reference

| Report | URL | View Name |
|--------|-----|-----------|
| Payroll History List | `/hr_dashboard/payroll-settings/history/` | `payroll_history_list` |
| Payroll History Detail | `/hr_dashboard/payroll-settings/history/<pk>/` | `payroll_history_detail` |
| Payout List | `/hr_dashboard/payout/` | `payout_list` |
| Payout Detail | `/hr_dashboard/payout/<pk>/` | `payout_detail` |
| Payout PDF | `/hr_dashboard/payout/<payout_id>/pdf/` | `payout_pdf` |
| Payout CSV Export | `/hr_dashboard/payout/export-csv/` | `payout_export_csv` |
| Individual Payroll | `/hr_dashboard/payroll/individual/` | `individual_payroll` |
| Batch Payroll Preview | `/hr_dashboard/payroll/batch-preview/` | `batch_payroll_preview` |
| Attendance List | `/hr_dashboard/attendance/` | `attendance_list` |
| Attendance Clock | `/hr_dashboard/attendance/clock/` | `attendance_clock` |
| Leave Request List | `/hr_dashboard/leave-requests/` | `leave_request_list` |
| Leave Credit List | `/hr_dashboard/leave-credits/` | `leave_credit_list` |
| User Management | `/hr_dashboard/user-mgnt/` | `hr_user_mgnt` |
| Employee List | `/hr_dashboard/employees/` | `employee_list` |
| Employee Profile | `/hr_dashboard/employees/<employee_id>/` | `employee_profile` |
| Staff History | `/hr_dashboard/dashboard/staff-history/` | `staff_history_hr_list` |
| Loan List | `/hr_dashboard/loans/` | `loan_list` |
| Loan Detail | `/hr_dashboard/loans/<pk>/` | `loan_detail` |

---

## Quick Reference Guide

### For Management - Key Metrics to Monitor

**Monthly:**
- Total Payroll (Gross and Net)
- Number of employees processed
- Deduction totals (tax, SSS, PhilHealth, Pag-IBIG)
- Released vs Unreleased payouts

**Daily/Weekly:**
- Attendance summary (Present, Absent, Late)
- Leave requests pending approval

**As Needed:**
- Loan portfolio status
- Leave credit balances

### For HR Users - Common Tasks

1. **Run Monthly Payroll:** Payout List → Batch Payroll → Finalize
2. **View Attendance:** Attendance List → Apply filters → Export if needed
3. **Process Leave:** Leave Request List → Approve/Disapprove
4. **Generate Payslip:** Payout Detail → Download PDF
5. **Export Data:** Any list page → Apply filters → Export CSV

---

*Document Version: 1.0*
*Last Updated: March 2026*
*System: Rockstar HR/Payroll System*
