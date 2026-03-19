# Payroll System Enhancement - Migration Guide

This document provides step-by-step instructions for migrating to the enhanced dynamic payroll system.

## Overview

The enhanced payroll system introduces:
- **Date-effective salary settings** with full audit trail
- **Configurable tier thresholds** for KPI integration
- **Dynamic de minimis types** 
- **Configurable deduction types**
- **Immutable payroll history**
- **Manual tax handling**

## Pre-Migration Checklist

### 1. Backup Your Database

```bash
# PostgreSQL
pg_dump -U username -d database_name > backup_$(date +%Y%m%d).sql

# Or use Django's dumpdata
python manage.py dumpdata human_resource > backup.json
```

### 2. Review Current Data

Check for employees with existing salary data:
```python
from users.models import Staff
from human_resource.payroll_computation import migrate_employee_salary_from_staff

# Preview employees with monthly_salary > 0
Staff.objects.filter(monthly_salary__gt=0).count()
Staff.objects.filter(monthly_salary=0).count()
Staff.objects.filter(monthly_salary__isnull=True).count()
```

### 3. Plan Cutoff Dates

Decide on your first payroll cutoff for the new system. Example:
- 1st cutoff: Day 1-15 of month
- 2nd cutoff: Day 16-end of month

## Migration Steps

### Step 1: Create Database Migrations

```bash
cd company_system
python manage.py makemigrations human_resource --name payroll_enhancement
```

### Step 2: Review Generated Migration

Inspect the migration file to ensure it creates all required tables:
- `human_resource_tierthresholdsetting`
- `human_resource_employeesalarysetting`
- `human_resource_deminimistype`
- `human_resource_deductiontype`
- `human_resource_payrollpreview`
- `human_resource_payrollhistory`
- `human_resource_deminimisentry`
- `human_resource_deductionentry`
- `human_resource_payrolladjustment`

### Step 3: Run Migrations

```bash
python manage.py migrate human_resource
```

### Step 4: Initialize Tier Threshold Settings

Create default tier thresholds for your organization:

```python
from human_resource.payroll_settings_models import TierThresholdSetting
from datetime import date

# Example tier setup
tiers = [
    {
        'tier_name': 'TIER1',
        'tier_label': 'Entry Level',
        'threshold_percentage': Decimal('85.00'),
        'multiplier': Decimal('1.0000'),
        'effective_start_date': date.today(),
    },
    {
        'tier_name': 'TIER2',
        'tier_label': 'Junior',
        'threshold_percentage': Decimal('88.00'),
        'multiplier': Decimal('1.0500'),
        'effective_start_date': date.today(),
    },
    {
        'tier_name': 'TIER3',
        'tier_label': 'Senior',
        'threshold_percentage': Decimal('92.00'),
        'multiplier': Decimal('1.1000'),
        'effective_start_date': date.today(),
    },
    {
        'tier_name': 'TIER4',
        'tier_label': 'Expert',
        'threshold_percentage': Decimal('95.00'),
        'multiplier': Decimal('1.1500'),
        'effective_start_date': date.today(),
    },
    {
        'tier_name': 'TIER5',
        'tier_label': 'Master',
        'threshold_percentage': Decimal('98.00'),
        'multiplier': Decimal('1.2000'),
        'effective_start_date': date.today(),
    },
]

for tier_data in tiers:
    TierThresholdSetting.objects.create(**tier_data)
```

### Step 5: Initialize De Minimis Types

Set up de minimis allowance types:

```python
from human_resource.payroll_settings_models import DeMinimisType
from datetime import date
from decimal import Decimal

de_minimis_types = [
    {
        'name': 'Rice Allowance',
        'code': 'RICE',
        'is_taxable': False,
        'display_order': 1,
        'effective_start_date': date.today(),
    },
    {
        'name': 'Food Allowance',
        'code': 'FOOD',
        'is_taxable': False,
        'display_order': 2,
        'effective_start_date': date.today(),
    },
    {
        'name': 'Gas Allowance',
        'code': 'GAS',
        'is_taxable': False,
        'display_order': 3,
        'effective_start_date': date.today(),
    },
    {
        'name': 'Phone Allowance',
        'code': 'PHONE',
        'is_taxable': True,
        'display_order': 4,
        'effective_start_date': date.today(),
    },
    {
        'name': 'Clothing Allowance',
        'code': 'CLOTHING',
        'is_taxable': True,
        'display_order': 5,
        'effective_start_date': date.today(),
    },
]

for dm in de_minimis_types:
    DeMinimisType.objects.create(**dm)
```

### Step 6: Initialize Deduction Types

Set up deduction types:

```python
from human_resource.payroll_settings_models import DeductionType
from datetime import date

deduction_types = [
    # Attendance deductions
    {
        'name': 'Late Deduction',
        'code': 'LATE',
        'category': 'ATTENDANCE',
        'is_government': False,
        'display_order': 1,
        'effective_start_date': date.today(),
    },
    {
        'name': 'Absent Deduction',
        'code': 'ABSENT',
        'category': 'ATTENDANCE',
        'is_government': False,
        'display_order': 2,
        'effective_start_date': date.today(),
    },
    # Government deductions
    {
        'name': 'SSS Contribution',
        'code': 'SSS',
        'category': 'GOVERNMENT',
        'is_government': True,
        'is_tax_applicable': False,
        'display_order': 10,
        'effective_start_date': date.today(),
    },
    {
        'name': 'PhilHealth Contribution',
        'code': 'PHILHEALTH',
        'category': 'GOVERNMENT',
        'is_government': True,
        'is_tax_applicable': False,
        'display_order': 11,
        'effective_start_date': date.today(),
    },
    {
        'name': 'Pag-IBIG Contribution',
        'code': 'PAGIBIG',
        'category': 'GOVERNMENT',
        'is_government': True,
        'is_tax_applicable': False,
        'display_order': 12,
        'effective_start_date': date.today(),
    },
    # Loan/Cash Advance
    {
        'name': 'Cash Advance',
        'code': 'CA',
        'category': 'LOAN',
        'is_government': False,
        'display_order': 20,
        'effective_start_date': date.today(),
    },
    {
        'name': 'Salary Loan',
        'code': 'LOAN',
        'category': 'LOAN',
        'is_government': False,
        'display_order': 21,
        'effective_start_date': date.today(),
    },
    # Other deductions
    {
        'name': 'Overpayment Recovery',
        'code': 'OVERPAYMENT',
        'category': 'OTHER',
        'is_government': False,
        'display_order': 30,
        'effective_start_date': date.today(),
    },
]

for ded in deduction_types:
    DeductionType.objects.create(**ded)
```

### Step 7: Migrate Employee Salaries

Migrate salary data from Staff model to EmployeeSalarySetting:

```python
from human_resource.payroll_computation import migrate_employee_salary_from_staff

# Preview migration
migrated = migrate_employee_salary_from_staff()
print(f"Migrated {len(migrated)} employees")

# Verify migration
from human_resource.payroll_settings_models import EmployeeSalarySetting
print(f"Total salary settings: {EmployeeSalarySetting.objects.count()}")
print(f"Active settings: {EmployeeSalarySetting.objects.filter(is_active=True).count()}")
```

### Step 8: Verify Settings

Run the validation utility:

```python
from human_resource.payroll_computation import validate_payroll_settings

is_valid, warnings, errors = validate_payroll_settings()

if warnings:
    print("Warnings:")
    for w in warnings:
        print(f"  - {w}")

if errors:
    print("Errors:")
    for e in errors:
        print(f"  - {e}")
```

## Configuration Options

### Rate Multipliers

Customize rate multipliers in [`payroll_settings_models.py`](payroll_settings_models.py):

```python
# In PayrollPreview model
ot_rate = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    default=Decimal('1.25'),  # Change to 1.5 for 50% OT premium
    help_text="Overtime rate multiplier"
)

nsd_rate = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    default=Decimal('1.10'),  # Change to 1.15 for 15% NSD premium
    help_text="NSD rate multiplier"
)
```

### Tier Multipliers

Modify tier multipliers based on your compensation structure:

```python
# Example: More aggressive tier progression
tier_multipliers = {
    'TIER1': Decimal('1.0000'),  # Base
    'TIER2': Decimal('1.1000'),  # +10%
    'TIER3': Decimal('1.2000'),  # +20%
    'TIER4': Decimal('1.3500'),  # +35%
    'TIER5': Decimal('1.5000'),  # +50%
}
```

## Rollback Plan

If you need to rollback:

### 1. Database Rollback

```bash
# Rollback the last migration
python manage.py migrate human_resource 0002  # or your previous migration number
```

### 2. Data Preservation

The following data should be preserved before rollback:
- Current EmployeeSalarySetting records (export if needed)
- PayrollPreview records
- PayrollHistory records

### 3. Restore Staff Model Salaries

If needed, restore salary data back to Staff model:

```python
# Save salary back to Staff
from users.models import Staff
from human_resource.payroll_settings_models import EmployeeSalarySetting

for staff in Staff.objects.all():
    latest_salary = EmployeeSalarySetting.objects.filter(
        employee=staff
    ).order_by('-effective_start_date').first()
    
    if latest_salary:
        staff.monthly_salary = latest_salary.base_salary_monthly
        staff.save()
```

## Post-Migration Tasks

### 1. Update Import Statements

Ensure all imports are updated throughout the codebase:

```python
# Old imports
from human_resource.models import Attendance, LeaveRequest
from human_resource.payroll_models import Payout, PayrollRecord

# New imports (add as needed)
from human_resource.payroll_settings_models import (
    EmployeeSalarySetting,
    TierThresholdSetting,
    DeMinimisType,
    DeductionType,
    PayrollPreview,
    PayrollHistory,
)
from human_resource.payroll_computation import (
    get_employee_salary,
    compute_payroll_preview,
    initialize_payroll_preview,
    post_payroll,
)
```

### 2. Update Templates

Modify payroll templates to use new field names and structures. See template examples in:
- `templates/hr/default/payroll/individual_payroll_preview.html`

### 3. Test Payroll Processing

Run through a complete payroll cycle:
1. Create PayrollRecord (batch)
2. Initialize PayrollPreview for employees
3. Validate previews
4. Post payroll
5. Verify PayrollHistory records

### 4. Train HR Staff

Key concepts for HR training:
- Salary changes = New record (no edits to history)
- Tier thresholds affect salary multipliers
- De minimis is separate from salary
- Tax is manually entered
- Payroll history is immutable

## Troubleshooting

### Common Issues

#### 1. "No active salary setting found"

**Cause:** Employee doesn't have an EmployeeSalarySetting record for the cutoff date.

**Solution:**
```python
# Create salary setting for employee
from human_resource.payroll_settings_models import EmployeeSalarySetting
from datetime import date
from decimal import Decimal

EmployeeSalarySetting.objects.create(
    employee=employee,
    base_salary_monthly=Decimal('50000.00'),
    effective_start_date=date.today(),
    is_active=True,
    notes="Initial salary setting"
)
```

#### 2. "Validation error: Net pay cannot be negative"

**Cause:** Deductions exceed earnings.

**Solutions:**
- Check for excessive manual deductions
- Verify attendance deductions are correct
- Ensure tax amount doesn't exceed taxable earnings

#### 3. "Tier threshold not found for employee"

**Cause:** Employee salary setting doesn't have a tier assigned.

**Solution:**
```python
from human_resource.payroll_settings_models import TierThresholdSetting

# Get default tier
default_tier = TierThresholdSetting.objects.filter(
    tier_name='TIER1',
    is_active=True
).first()

# Assign to employee
salary_setting.tier = default_tier
salary_setting.save()
```

## Future Enhancements

The system is designed to support:
- **KPI Module Integration:** Automatic tier assignment based on performance scores
- **Tax Calculator:** Integration with BIR tax tables
- **Government Deductions:** Automatic calculation based on salary brackets
- **Payslip Generation:** PDF generation for employees
- **Bank Integration:** Direct deposit file export

## Support

For issues or questions:
1. Review the model docstrings in [`payroll_settings_models.py`](payroll_settings_models.py)
2. Check computation logic in [`payroll_computation.py`](payroll_computation.py)
3. Review validation rules in [`PayrollPreview.clean()`](payroll_settings_models.py)
4. Check audit logs in Django Admin
