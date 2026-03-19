# Software Requirements Specification
## HR Module - Individual Payroll Processing Feature

**Document Version:** 1.0  
**Date:** February 2026  
**Author:** HR Development Team  
**Status:** Draft

---

## Table of Contents
1. [Introduction](#1-introduction)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [Technical Specifications](#4-technical-specifications)
5. [Data Models](#5-data-models)
6. [User Interface Specifications](#6-user-interface-specifications)
7. [Security Requirements](#7-security-requirements)
8. [Appendix](#8-appendix)

---

## 1. Introduction

### 1.1 Purpose
This document specifies the software requirements for the Individual Payroll Processing feature within the HR Module. This feature enables HR personnel to manually process payroll for individual employees on a per-period basis.

### 1.2 Scope
The Individual Payroll Processing feature covers:
- Manual payroll entry and calculation for single employees
- Attendance-based deduction calculations
- Government contribution computations
- Tax calculations with progressive brackets
- Payroll preview and finalization workflow
- HR self-service status checking

### 1.3 Definitions and Acronyms
| Term | Definition |
|------|------------|
| HR | Human Resources |
| SRS | Software Requirements Specification |
| SSS | Social Security System |
| PhilHealth | Philippine Health Insurance Corporation |
| Pag-IBIG | Home Development Mutual Fund |
| NSD | Night Shift Differential |
| OT | Overtime |

---

## 2. Functional Requirements

### 2.1 Individual Payroll Processing

#### 2.1.1 Manual Payroll Entry Screen
**FR-001:** The system shall provide a manual payroll entry screen accessible to authorized HR users.

**FR-002:** The entry screen shall include the following period selection fields:
| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| Month | Dropdown (1-12) | Required | Processing month |
| Year | Number (4-digit) | Required, Range: 2000-2100 | Processing year |
| Cutoff | Dropdown | Required | Options: "1st Cutoff (1-15)" or "2nd Cutoff (16-end)" |

**FR-003:** The system shall implement an employee selection mechanism with the following specifications:
- Searchable dropdown component
- Data source: `Staff.objects.filter(status='active')`
- Search fields: first_name, last_name, employee_number
- Minimum 2 characters to trigger search

**FR-004:** The employee selection panel shall display:
| Field | Source | Format |
|-------|--------|--------|
| Employee Name | `{first_name} {middle_name} {last_name}` | Text |
| Employee ID | `employee_number` | Text |
| Job Title | `job_title` | Display value from choices |
| Department | `department` | Display value from choices |

**FR-005:** The system shall enforce single-employee selection per payroll operation. Multi-select functionality shall be disabled.

#### 2.1.2 Data Retrieval and Calculation

**FR-006:** Upon employee selection, the system shall automatically retrieve and display:

**Employee Information:**
| Data Point | Source Model | Field |
|------------|--------------|-------|
| Full Name | Staff | first_name, middle_name, last_name |
| Employee ID | Staff | employee_number |
| Department | Staff | department |
| Job Title | Staff | job_title |
| Bank Name | BankAccount → BankType | bank.name |
| Account Number | BankAccount | account_number |
| Primary Account | BankAccount | is_primary |

**FR-007:** The system shall fetch attendance records for the selected period:
| Metric | Calculation Method |
|--------|-------------------|
| Total Working Days | Count of weekdays in period (excluding holidays) |
| Days Present | Count of Attendance records with status='present' |
| Days Absent | Total Working Days - Days Present - Approved Leaves |
| Late Arrivals | Count of records where clock_in > shift_rule.clock_in_end |
| Late Minutes | Sum of (clock_in - clock_in_end) for late records |
| Early Departures | Count of records where clock_out < shift_rule.clock_out |

**FR-008:** The system shall retrieve salary structure:

**Basic Salary:**
```python
# Source: Staff.monthly_salary or EmployeeProfileSettings.monthly_salary
basic_salary = Decimal(employee.monthly_salary)
salary_per_cutoff = basic_salary / 2
```

**Allowances (from EmployeeBenefit model):**
| Allowance Type | Field | Calculation |
|----------------|-------|-------------|
| Housing | benefit.amount | Fixed or percentage |
| Transportation | benefit.amount | Fixed or percentage |
| Meal | benefit.amount | Fixed or percentage |
| Medical | benefit.amount | Fixed or percentage |
| Other | benefit.amount | As configured |

**Deductions (from Loan and EmployeeBenefit models):**
| Deduction Type | Source | Calculation |
|----------------|--------|-------------|
| Loan Repayment | Loan.per_cutoff | Sum of active loans |
| Insurance | EmployeeBenefit | As configured |
| Other Recurring | EmployeeBenefit | As configured |

#### 2.1.3 Payroll Calculation Formulas

**FR-009:** The system shall calculate payroll components using the following formulas:

**Gross Salary Calculation:**
```
Gross Salary = Basic Salary + Σ(All Allowances)
```

**Absence Deduction:**
```
Daily Rate = Basic Salary / Working Days per Month (default: 22)
Absence Deduction = Daily Rate × Number of Absent Days
```

**Late Arrival Deduction:**
```
Hourly Rate = Daily Rate / Working Hours per Day (default: 8)
Late Deduction = (Total Late Minutes / 60) × Hourly Rate × Penalty Rate
Penalty Rate = Configurable (default: 1.0)
```

**Government Contributions:**
| Contribution | Rate | Calculation |
|--------------|------|-------------|
| SSS | Based on salary bracket | Lookup table |
| PhilHealth | 4% of basic (split 50/50) | basic_salary × 0.02 |
| Pag-IBIG | ₱100 (employee share) | Fixed amount |

**Tax Calculation:**
```python
# Progressive Tax Brackets (Philippines BIR)
taxable_income = gross_salary - total_deductions - exemptions

if taxable_income <= 250000:
    tax = 0
elif taxable_income <= 400000:
    tax = (taxable_income - 250000) * 0.15
elif taxable_income <= 800000:
    tax = 22500 + (taxable_income - 400000) * 0.20
elif taxable_income <= 2000000:
    tax = 102500 + (taxable_income - 800000) * 0.25
elif taxable_income <= 8000000:
    tax = 402500 + (taxable_income - 2000000) * 0.30
else:
    tax = 2202500 + (taxable_income - 8000000) * 0.35
```

**Net Pay Calculation:**
```
Net Pay = Gross Salary - Total Deductions - Government Contributions - Tax
```

#### 2.1.4 Payroll Preview Display

**FR-010:** The system shall present a detailed payroll preview with the following sections:

**Section 1: Employee Information**
| Field | Display |
|-------|---------|
| Name | Full name |
| Employee ID | employee_number |
| Department | department display value |
| Position | job_title display value |
| Period | Month/Year Cutoff X |

**Section 2: Earnings**
| Item | Amount |
|------|--------|
| Basic Salary | ₱XX,XXX.XX |
| Housing Allowance | ₱X,XXX.XX |
| Transportation Allowance | ₱X,XXX.XX |
| Meal Allowance | ₱X,XXX.XX |
| Medical Allowance | ₱X,XXX.XX |
| Other Allowances | ₱X,XXX.XX |
| Overtime Pay | ₱X,XXX.XX |
| Night Differential | ₱X,XXX.XX |
| **Total Earnings** | **₱XX,XXX.XX** |

**Section 3: Deductions**
| Item | Details | Amount |
|------|---------|--------|
| Absence | X days | ₱X,XXX.XX |
| Late Arrivals | X occurrences, Y minutes | ₱XXX.XX |
| Loan Repayment | Loan #XXX | ₱X,XXX.XX |
| Other Deductions | Description | ₱XXX.XX |
| **Total Deductions** | | **₱X,XXX.XX** |

**Section 4: Government Contributions**
| Contribution | Rate | Amount |
|--------------|------|--------|
| SSS | Based on bracket | ₱XXX.XX |
| PhilHealth | 2% | ₱XXX.XX |
| Pag-IBIG | Fixed | ₱100.00 |
| **Total Contributions** | | **₱X,XXX.XX** |

**Section 5: Tax**
| Item | Value |
|------|-------|
| Taxable Income | ₱XX,XXX.XX |
| Tax Bracket | XX% |
| Tax Amount | ₱X,XXX.XX |

**Section 6: Summary**
| Item | Amount |
|------|--------|
| Gross Salary | ₱XX,XXX.XX |
| Total Deductions | (₱X,XXX.XX) |
| Government Contributions | (₱X,XXX.XX) |
| Tax | (₱X,XXX.XX) |
| **Net Pay** | **₱XX,XXX.XX** |

**FR-011:** The system shall provide a printable format option generating a PDF payslip.

#### 2.1.5 Review and Finalization Workflow

**FR-012:** The payroll preview shall display all calculations with editable override fields.

**FR-013:** Manual override functionality:
| Requirement | Specification |
|-------------|---------------|
| Editable Fields | All calculated amounts |
| Override Logging | HR user ID, timestamp, original value, new value, reason |
| Reason Field | Required text field (min 10 characters) |

**FR-014:** The system shall provide a "Calculate & Update" button that:
- Recalculates all dependent values when any amount is modified
- Highlights changed values
- Maintains override log

**FR-015:** The "Confirm & Save" button shall:
1. Validate all required fields are populated
2. Display summary confirmation dialog with:
   - Employee name and ID
   - Period details
   - Net pay amount
   - Confirmation checkbox
3. Save to PayrollRecord model with:
   - `created_by = request.user`
   - `finalized = True`
   - `created_at = timezone.now()`

**FR-016:** Transaction locking requirements:
```python
# Prevent concurrent processing
existing = Payout.objects.filter(
    employee=employee,
    month=month,
    year=year,
    cutoff=cutoff
).exists()

if existing:
    raise ValidationError("Payroll already processed for this period")
```

### 2.2 HR Self-Service Status Check

**FR-017:** Authenticated HR users shall view their employment status:
| Information | Source |
|-------------|--------|
| Current Department | Staff.department |
| Job Title | Staff.job_title |
| Employment Type | Staff.type |
| Date of Hire | Staff.start_date |
| Tenure | Staff.tenure_active |

**FR-018:** Personal attendance summary for current month:
| Metric | Calculation |
|--------|-------------|
| Total Days Worked | Count of present attendance records |
| Total Days Absent | Working days - present - approved leaves |
| Total Late Arrivals | Count of late clock-ins |
| Total Early Departures | Count of early clock-outs |

**FR-019:** Leave balance display:
| Leave Type | Fields |
|------------|--------|
| Annual Leave | LeaveCredit.total, LeaveCredit.used |
| Sick Leave | LeaveCredit.total, LeaveCredit.used |
| Personal Leave | LeaveCredit.total, LeaveCredit.used |
| Other Types | As configured |

**FR-020:** Payroll history access:
| Column | Source |
|--------|--------|
| Period | Payout.month, Payout.year, Payout.cutoff |
| Gross Salary | Payout.gross |
| Net Pay | Payout.net |
| Status | PayrollRecord.finalized |
| Payslip | Payout.payslip (download link) |

---

## 3. Non-Functional Requirements

### 3.1 Performance Requirements

**NFR-001:** Individual payroll computation shall complete within 3 seconds.

**NFR-002:** Data retrieval and display shall complete within 5 seconds.

**NFR-003:** PDF generation shall complete within 10 seconds.

### 3.2 Validation Requirements

**NFR-004:** Data validation rules:
| Field | Validation |
|-------|------------|
| Month | Required, 1-12 |
| Year | Required, 2000-2100 |
| Cutoff | Required, '1' or '2' |
| Employee | Required, must exist and be active |
| Override Reason | Required if override applied, min 10 chars |

**NFR-005:** Error messages shall:
- Be displayed prominently (red text, alert box)
- Clearly indicate the field with error
- Provide actionable guidance

### 3.3 Confirmation Requirements

**NFR-006:** Finalization confirmation shall require:
- Summary review
- Explicit checkbox confirmation
- "Confirm" button click

### 3.4 Audit Requirements

**NFR-007:** All payroll operations shall be logged:
| Log Field | Description |
|-----------|-------------|
| user_id | HR user performing action |
| timestamp | Date and time of action |
| employee_id | Affected employee |
| action | CREATE, UPDATE, OVERRIDE, FINALIZE |
| details | JSON of changes |

---

## 4. Technical Specifications

### 4.1 Database Queries

**Active Employee Retrieval:**
```python
Staff.objects.filter(status='active').select_related(
    'role', 'departmentlink', 'positionlink'
)
```

**Attendance Retrieval:**
```python
Attendance.objects.filter(
    employee=employee,
    date__range=(cutoff_start, cutoff_end)
).select_related('employee')
```

**Bank Account Retrieval:**
```python
BankAccount.objects.filter(
    employee=employee,
    is_primary=True
).select_related('bank').first()
```

### 4.2 Transaction Management

```python
from django.db import transaction

@transaction.atomic
def finalize_individual_payroll(employee, period_data, calculated_data, user):
    # Lock the row to prevent concurrent updates
    with transaction.atomic():
        # Check for existing record
        if Payout.objects.select_for_update().filter(
            employee=employee,
            month=period_data['month'],
            year=period_data['year'],
            cutoff=period_data['cutoff']
        ).exists():
            raise ValidationError("Payroll already exists")
        
        # Create PayrollRecord
        pr = PayrollRecord.objects.create(
            month=period_data['month'],
            year=period_data['year'],
            cutoff=period_data['cutoff'],
            created_by=user,
            finalized=True
        )
        
        # Create Payout
        payout = Payout.objects.create(
            payroll_record=pr,
            employee=employee,
            **calculated_data
        )
        
        return payout
```

### 4.3 Error Handling

```python
class PayrollProcessingError(Exception):
    """Base exception for payroll processing errors"""
    pass

class MissingAttendanceError(PayrollProcessingError):
    """Raised when attendance records are missing"""
    pass

class InvalidSalaryStructureError(PayrollProcessingError):
    """Raised when salary structure is incomplete"""
    pass

class IncompleteEmployeeDataError(PayrollProcessingError):
    """Raised when employee data is incomplete"""
    pass
```

### 4.4 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/payroll/individual/` | POST | Process individual payroll |
| `/api/payroll/individual/preview/` | POST | Get payroll preview |
| `/api/payroll/individual/<id>/` | GET | Get specific payroll record |
| `/api/payroll/employee/<id>/history/` | GET | Get employee payroll history |

### 4.5 Audit Trail

```python
class PayrollAuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    employee = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # CREATE, UPDATE, OVERRIDE, FINALIZE
    payout = models.ForeignKey(Payout, on_delete=models.SET_NULL, null=True)
    before_values = models.JSONField(null=True, blank=True)
    after_values = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
```

---

## 5. Data Models

### 5.1 Existing Models Used

| Model | Location | Purpose |
|-------|----------|---------|
| Staff | users/models.py | Employee information |
| BankAccount | human_resource/payroll_models.py | Bank details |
| BankType | human_resource/payroll_models.py | Bank types |
| Attendance | human_resource/models.py | Attendance records |
| EmployeeShiftRule | human_resource/models.py | Shift configurations |
| Loan | human_resource/payroll_models.py | Loan records |
| Benefit | human_resource/payroll_models.py | Benefit definitions |
| EmployeeBenefit | human_resource/payroll_models.py | Employee benefits |
| PayrollRecord | human_resource/payroll_models.py | Payroll batch records |
| Payout | human_resource/payroll_models.py | Individual payouts |
| LeaveCredit | human_resource/models.py | Leave balances |
| LeaveRequest | human_resource/models.py | Leave requests |

### 5.2 New Models Required

```python
class PayrollOverride(models.Model):
    """Tracks manual overrides to calculated payroll values"""
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name='overrides')
    field_name = models.CharField(max_length=100)
    original_value = models.DecimalField(max_digits=12, decimal_places=2)
    override_value = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    overridden_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    overridden_at = models.DateTimeField(auto_now_add=True)

class PayrollAuditLog(models.Model):
    """Audit trail for all payroll operations"""
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('OVERRIDE', 'Override Applied'),
        ('FINALIZE', 'Finalized'),
        ('VOID', 'Voided'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    employee = models.ForeignKey('users.Staff', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    payout = models.ForeignKey(Payout, on_delete=models.SET_NULL, null=True, blank=True)
    before_values = models.JSONField(null=True, blank=True)
    after_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
```

---

## 6. User Interface Specifications

### 6.1 Individual Payroll Processing Screen

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Individual Payroll Processing                               │
├─────────────────────────────────────────────────────────────┤
│ Period Selection                                            │
│ ┌─────────┐ ┌─────────┐ ┌─────────────────┐                │
│ │ Month ▼ │ │ Year    │ │ Cutoff        ▼ │                │
│ └─────────┘ └─────────┘ └─────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│ Employee Selection                                          │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 🔍 Search employee by name or ID...                     ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Selected Employee:                                      ││
│ │ Name: Juan Dela Cruz                                    ││
│ │ ID: EMP-2024-001                                        ││
│ │ Department: Human Resource                              ││
│ │ Position: HR Manager                                    ││
│ └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│ [Load Payroll Data]                                         │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Payroll Preview Screen

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Payroll Preview - Juan Dela Cruz (EMP-2024-001)             │
│ Period: January 2026 - 1st Cutoff                           │
├─────────────────────────────────────────────────────────────┤
│ EARNINGS                                          Amount    │
│ ─────────────────────────────────────────────────────────── │
│ Basic Salary                                   ₱15,000.00   │
│ Housing Allowance                               ₱2,000.00   │
│ Transportation Allowance                        ₱1,500.00   │
│ Meal Allowance                                  ₱1,000.00   │
│ Overtime (5 hrs @ ₱93.75/hr × 1.25)              ₱585.94   │
│ Night Differential (8 hrs @ ₱75.00/hr × 0.1)      ₱60.00   │
│ ─────────────────────────────────────────────────────────── │
│ Total Earnings                                ₱20,145.94   │
├─────────────────────────────────────────────────────────────┤
│ DEDUCTIONS                                        Amount    │
│ ─────────────────────────────────────────────────────────── │
│ Absence (1 day)                                  ₱681.82   │
│ Late Arrivals (3 times, 45 mins)                  ₱56.82   │
│ Loan Repayment (Loan #123)                     ₱1,000.00   │
│ ─────────────────────────────────────────────────────────── │
│ Total Deductions                               ₱1,738.64   │
├─────────────────────────────────────────────────────────────┤
│ GOVERNMENT CONTRIBUTIONS                          Amount    │
│ ─────────────────────────────────────────────────────────── │
│ SSS (Employee Share)                             ₱800.00   │
│ PhilHealth (Employee Share)                      ₱300.00   │
│ Pag-IBIG (Employee Share)                        ₱100.00   │
│ ─────────────────────────────────────────────────────────── │
│ Total Contributions                            ₱1,200.00   │
├─────────────────────────────────────────────────────────────┤
│ TAX                                                         │
│ ─────────────────────────────────────────────────────────── │
│ Taxable Income                                ₱17,207.30   │
│ Tax Bracket                                          15%   │
│ Withholding Tax                                  ₱456.10   │
├─────────────────────────────────────────────────────────────┤
│ SUMMARY                                                     │
│ ─────────────────────────────────────────────────────────── │
│ Gross Salary                                  ₱20,145.94   │
│ Less: Deductions                              (₱1,738.64)  │
│ Less: Government Contributions                (₱1,200.00)  │
│ Less: Tax                                       (₱456.10)  │
│ ═══════════════════════════════════════════════════════════ │
│ NET PAY                                       ₱16,751.20   │
├─────────────────────────────────────────────────────────────┤
│ [Print Preview] [Apply Override] [Calculate & Update]       │
│                                    [Cancel] [Confirm & Save]│
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Override Dialog

```
┌─────────────────────────────────────────────────────────────┐
│ Apply Manual Override                                       │
├─────────────────────────────────────────────────────────────┤
│ Field: Late Arrival Deduction                               │
│ Original Value: ₱56.82                                      │
│                                                             │
│ New Value: ┌────────────────┐                               │
│            │ ₱0.00          │                               │
│            └────────────────┘                               │
│                                                             │
│ Reason for Override: *                                      │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Employee submitted approved late excuse form for all    ││
│ │ three instances. Reference: HR-2026-001                 ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│                              [Cancel] [Apply Override]      │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Security Requirements

### 7.1 Access Control

**SR-001:** Only users with HR role shall access individual payroll processing.

**SR-002:** Payroll data shall be accessible only to:
- HR personnel (full access)
- Finance personnel (read-only for approved payrolls)
- Employee (own payroll history only)

### 7.2 Data Protection

**SR-003:** All payroll data shall be encrypted at rest.

**SR-004:** All payroll API endpoints shall require authentication.

**SR-005:** Session timeout for payroll screens: 15 minutes of inactivity.

### 7.3 Audit Compliance

**SR-006:** All payroll operations shall be logged with immutable audit trail.

**SR-007:** Audit logs shall be retained for minimum 7 years.

---

## 8. Appendix

### 8.1 Government Contribution Tables

**SSS Contribution Table (2024):**
| Monthly Salary Credit | Employee Share | Employer Share |
|----------------------|----------------|----------------|
| Below ₱4,250 | ₱180.00 | ₱380.00 |
| ₱4,250 - ₱4,749.99 | ₱202.50 | ₱427.50 |
| ₱4,750 - ₱5,249.99 | ₱225.00 | ₱475.00 |
| ... | ... | ... |
| ₱29,750 and above | ₱1,350.00 | ₱2,850.00 |

**PhilHealth Contribution (2024):**
- Rate: 4% of basic monthly salary
- Split: 50% employee, 50% employer
- Minimum: ₱400/month
- Maximum: ₱3,200/month

**Pag-IBIG Contribution:**
- Employee: ₱100/month (fixed)
- Employer: ₱100/month (fixed)

### 8.2 Tax Brackets (Philippines BIR - 2024)

| Taxable Income | Tax Rate |
|----------------|----------|
| ₱0 - ₱250,000 | 0% |
| ₱250,001 - ₱400,000 | 15% of excess over ₱250,000 |
| ₱400,001 - ₱800,000 | ₱22,500 + 20% of excess over ₱400,000 |
| ₱800,001 - ₱2,000,000 | ₱102,500 + 25% of excess over ₱800,000 |
| ₱2,000,001 - ₱8,000,000 | ₱402,500 + 30% of excess over ₱2,000,000 |
| Over ₱8,000,000 | ₱2,202,500 + 35% of excess over ₱8,000,000 |

### 8.3 Related Documents

- [Payroll Models Documentation](../payroll_models.py)
- [Payroll Utilities Documentation](../payroll_utils.py)
- [HR Module URLs](../urls.py)
- [Views Implementation](../views_payroll.py)

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Manager | | | |
| HR Manager | | | |
| IT Manager | | | |
| QA Lead | | | |
