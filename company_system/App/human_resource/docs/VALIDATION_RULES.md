# Payroll System - Validation Rules Reference

This document provides comprehensive validation rules for the enhanced payroll system.

## Table of Contents

1. [Salary Setting Validation](#salary-setting-validation)
2. [Tier Threshold Validation](#tier-threshold-validation)
3. [De Minimis Type Validation](#de-minimis-type-validation)
4. [Deduction Type Validation](#deduction-type-validation)
5. [Payroll Preview Validation](#payroll-preview-validation)
6. [Payroll Posting Validation](#payroll-posting-validation)
7. [Error Handling](#error-handling)

---

## Salary Setting Validation

### Rule 1: Date Range Validation
```
Effective end date must be after effective start date.
```
- **Field:** `effective_end_date`
- **Condition:** Must be >= `effective_start_date`
- **Error Code:** `SALARY_001`
- **Error Message:** "End date must be after start date"

### Rule 2: Single Active Salary Per Date
```
Only ONE active salary record per employee per date.
```
- **Field:** `employee`, `effective_start_date`, `is_active`
- **Condition:** No overlapping active records
- **Error Code:** `SALARY_002`
- **Error Message:** "Active salary setting already exists for this employee on this date"

### Rule 3: Salary Per Cutoff Computation
```
Salary per cutoff = monthly salary / 2
```
- **Field:** `salary_per_cutoff` (computed)
- **Condition:** Auto-computed from `base_salary_monthly`
- **Rounding:** 2 decimal places

### Rule 4: No Salary Overwrite
```
Salary changes MUST create a new record.
```
- **Implementation:** No update allowed on existing records
- **Workflow:** Create new record, deactivate old
- **Error Code:** `SALARY_003`
- **Error Message:** "Salary changes must create a new record"

### Rule 5: Positive Salary
```
Base salary must be positive.
```
- **Field:** `base_salary_monthly`
- **Condition:** Must be >= 0
- **Error Code:** `SALARY_004`
- **Error Message:** "Base salary must be a positive value"

---

## Tier Threshold Validation

### Rule 1: Percentage Range
```
Threshold percentage must be between 0 and 100.
```
- **Field:** `threshold_percentage`
- **Condition:** 0 <= value <= 100
- **Error Code:** `TIER_001`
- **Error Message:** "Threshold percentage must be between 0 and 100"

### Rule 2: Date Range Validation
```
Tier effective dates must be valid.
```
- **Condition:** `effective_end_date` >= `effective_start_date`
- **Error Code:** `TIER_002`
- **Error Message:** "End date must be after start date"

### Rule 3: No Overlapping Active Tiers
```
Cannot have two active tier settings with the same name on overlapping dates.
```
- **Fields:** `tier_name`, `effective_start_date`, `effective_end_date`
- **Condition:** No overlapping active records
- **Error Code:** `TIER_003`
- **Error Message:** "Active tier setting already exists for this tier on this date"

### Rule 4: Multiplier Range
```
Tier multiplier should be positive.
```
- **Field:** `multiplier`
- **Condition:** Must be > 0
- **Error Code:** `TIER_004`
- **Error Message:** "Tier multiplier must be a positive value"

---

## De Minimis Type Validation

### Rule 1: Unique Code
```
Each de minimis type must have a unique code.
```
- **Field:** `code`
- **Condition:** Unique across all de minimis types
- **Error Code:** `DEM_001`
- **Error Message:** "De minimis type with this code already exists"

### Rule 2: Date Range
```
De minimis effective dates must be valid.
```
- **Condition:** `effective_end_date` >= `effective_start_date`
- **Error Code:** `DEM_002`
- **Error Message:** "End date must be after start date"

### Rule 3: Taxable Flag
```
Taxable flag is a boolean (true/false).
```
- **Field:** `is_taxable`
- **Condition:** Boolean value
- **Note:** Taxable de minimis affects taxable income calculation

### Rule 4: Display Order
```
Display order must be a non-negative integer.
```
- **Field:** `display_order`
- **Condition:** >= 0
- **Error Code:** `DEM_003`
- **Error Message:** "Display order must be a non-negative integer"

---

## Deduction Type Validation

### Rule 1: Unique Code
```
Each deduction type must have a unique code.
```
- **Field:** `code`
- **Condition:** Unique across all deduction types
- **Error Code:** `DED_001`
- **Error Message:** "Deduction type with this code already exists"

### Rule 2: Valid Category
```
Category must be one of: ATTENDANCE, GOVERNMENT, LOAN, OTHER
```
- **Field:** `category`
- **Condition:** Must be in CATEGORY_CHOICES
- **Error Code:** `DED_002`
- **Error Message:** "Invalid category"

### Rule 3: Date Range
```
Deduction type effective dates must be valid.
```
- **Condition:** `effective_end_date` >= `effective_start_date`
- **Error Code:** `DED_003`
- **Error Message:** "End date must be after start date"

### Rule 4: Government Flag
```
Government deductions have specific processing rules.
```
- **Field:** `is_government`
- **Note:** Government deductions are processed separately
- **Affected Categories:** GOVERNMENT only

---

## Payroll Preview Validation

### Rule 1: Net Pay Cannot Be Negative
```
Net pay must be >= 0.
```
- **Field:** `net_pay`
- **Condition:** >= 0
- **Severity:** ERROR (blocks posting)
- **Error Code:** `PREVIEW_001`
- **Error Message:** "Net pay cannot be negative: {net_pay}"

### Rule 2: Tax Cannot Exceed Taxable Earnings
```
Tax amount must not exceed taxable earnings.
```
- **Fields:** `tax_amount`, `taxable_earnings`
- **Condition:** `tax_amount` <= `taxable_earnings`
- **Severity:** ERROR (blocks posting)
- **Error Code:** `PREVIEW_002`
- **Error Message:** "Tax cannot exceed taxable earnings"

### Rule 3: Salary Setting Required
```
Each payroll preview must have a valid salary setting.
```
- **Field:** `employee_salary_setting`
- **Condition:** Must not be null
- **Severity:** ERROR (blocks posting)
- **Error Code:** `PREVIEW_003`
- **Error Message:** "No salary setting found for this employee"

### Rule 4: Valid Cutoff Dates
```
Cutoff end date must be after cutoff start date.
```
- **Fields:** `cutoff_start_date`, `cutoff_end_date`
- **Condition:** `cutoff_end_date` >= `cutoff_start_date`
- **Severity:** ERROR
- **Error Code:** `PREVIEW_004`
- **Error Message:** "Invalid cutoff dates"

### Rule 5: No Negative Hours/Amounts
```
All hour and amount fields must be non-negative.
```
- **Fields:** `overtime_hours`, `nsd_hours`, `holiday_hours`, `leave_days`
- **Condition:** >= 0
- **Severity:** WARNING
- **Error Code:** `PREVIEW_005`
- **Error Message:** "{field_name} cannot be negative"

### Rule 6: Tax Amount Non-Negative
```
Tax amount must be non-negative.
```
- **Field:** `tax_amount`
- **Condition:** >= 0
- **Severity:** ERROR (if negative)
- **Error Code:** `PREVIEW_006`
- **Error Message:** "Tax amount cannot be negative"

---

## Payroll Posting Validation

### Rule 1: Preview Must Be Validated
```
Only validated previews can be posted.
```
- **Field:** `status`
- **Condition:** Must be 'VALIDATED'
- **Severity:** ERROR (blocks posting)
- **Error Code:** `POST_001`
- **Error Message:** "Preview must be validated before posting"

### Rule 2: No Negative Net Pay
```
Cannot post payroll with negative net pay.
```
- **Field:** `net_pay`
- **Condition:** >= 0
- **Severity:** ERROR (blocks posting)
- **Error Code:** `POST_002`
- **Error Message:** "Cannot post payroll with negative net pay"

### Rule 3: Salary Setting Required
```
Cannot post without salary setting.
```
- **Field:** `employee_salary_setting`
- **Condition:** Must exist
- **Severity:** ERROR (blocks posting)
- **Error Code:** `POST_003`
- **Error Message:** "Cannot post: No salary setting"

### Rule 4: No Validation Errors
```
Preview must have no validation errors.
```
- **Field:** `validation_errors`
- **Condition:** Must be null or empty
- **Severity:** ERROR (blocks posting)
- **Error Code:** `POST_004`
- **Error Message:** "Cannot post: {validation_errors}"

---

## Error Handling

### Error Response Format

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "field": "field_name",
        "severity": "ERROR|WARNING",
        "data": {}
    }
}
```

### Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| ERROR | Fatal error | Blocks operation |
| WARNING | Potential issue | Allows operation, flags for review |
| INFO | Informational | No action required |

### Error Recovery

#### 1. Negative Net Pay
```
Scenario: Deductions exceed earnings
Recovery: 
1. Review deduction entries
2. Check attendance data
3. Verify manual deductions
4. Adjust amounts or approve as-is
```

#### 2. Tax Exceeds Earnings
```
Scenario: Tax amount is too high
Recovery:
1. Verify taxable earnings calculation
2. Check de minimis taxable flags
3. Adjust tax amount
```

#### 3. Missing Salary Setting
```
Scenario: Employee has no salary for the date
Recovery:
1. Create EmployeeSalarySetting for the date
2. Or adjust cutoff dates
3. Or backdate salary setting
```

---

## Validation in Forms

### Model Form Validation

```python
# Example: EmployeeSalarySettingForm
class EmployeeSalarySettingForm(forms.ModelForm):
    class Meta:
        model = EmployeeSalarySetting
        fields = ['employee', 'base_salary_monthly', 'tier', 
                  'effective_start_date', 'effective_end_date', 'notes']
    
    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        start_date = cleaned_data.get('effective_start_date')
        end_date = cleaned_data.get('effective_end_date')
        
        # Check for overlapping records
        if employee and start_date:
            overlap = EmployeeSalarySetting.objects.filter(
                employee=employee,
                is_active=True
            ).exclude(pk=self.instance.pk)
            
            # ... validation logic ...
        
        return cleaned_data
```

### View-Level Validation

```python
@transaction.atomic
def post_payroll(request, preview_id):
    preview = get_object_or_404(PayrollPreview, pk=preview_id)
    
    # Validate
    is_valid, errors = validate_payroll_preview(preview)
    if not is_valid:
        messages.error(request, f"Cannot post: {'; '.join(errors)}")
        return redirect('payroll:preview_detail', pk=preview_id)
    
    # Additional checks
    if preview.status != 'VALIDATED':
        messages.error(request, "Preview must be validated first")
        return redirect('payroll:preview_detail', pk=preview_id)
    
    # Proceed with posting
    # ...
```

---

## API Validation Endpoints

### Validate Settings
```
GET /api/payroll/settings/validate/
```
Returns validation status of all payroll settings.

### Check Employee Salary
```
GET /api/payroll/salary/check/?employee_id=X&date=Y
```
Returns salary setting status for an employee on a specific date.

### Validate Preview
```
POST /api/payroll/preview/validate/
{
    "preview_id": X
}
```
Returns validation errors for a payroll preview.

---

## Summary Table

| Rule ID | Category | Rule | Severity | Blocks Posting |
|---------|----------|------|----------|----------------|
| SALARY_001 | Salary | Date range valid | ERROR | No |
| SALARY_002 | Salary | No overlapping records | ERROR | No |
| SALARY_003 | Salary | No overwrites | ERROR | No |
| SALARY_004 | Salary | Positive salary | ERROR | No |
| TIER_001 | Tier | Percentage 0-100 | ERROR | No |
| TIER_002 | Tier | Date range valid | ERROR | No |
| TIER_003 | Tier | No overlapping tiers | ERROR | No |
| DEM_001 | De Minimis | Unique code | ERROR | No |
| DEM_002 | De Minimis | Date range valid | ERROR | No |
| DED_001 | Deduction | Unique code | ERROR | No |
| DED_002 | Deduction | Valid category | ERROR | No |
| PREVIEW_001 | Preview | Net pay >= 0 | ERROR | Yes |
| PREVIEW_002 | Preview | Tax <= taxable | ERROR | Yes |
| PREVIEW_003 | Preview | Salary required | ERROR | Yes |
| PREVIEW_004 | Preview | Valid dates | ERROR | No |
| POST_001 | Posting | Must be validated | ERROR | Yes |
| POST_002 | Posting | No negative net | ERROR | Yes |
| POST_003 | Posting | Salary required | ERROR | Yes |
