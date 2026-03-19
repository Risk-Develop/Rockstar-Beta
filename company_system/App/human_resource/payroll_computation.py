# human_resource/payroll_computation.py
"""
Dynamic Payroll Computation Logic

Core computation functions for the enhanced payroll system:
- Salary retrieval based on effective dates
- Tier-based salary calculations
- Deduction and de minimis processing
- Validation rules for payroll
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from .payroll_settings_models import (
    EmployeeSalarySetting,
    TierThresholdSetting,
    DeMinimisType,
    DeductionType,
    PayrollPreview,
    PayrollHistory,
    DeMinimisEntry,
    DeductionEntry,
)
from .models import Attendance, EmployeeShiftRule, LeaveRequest
from App.users.models import Staff

# Standard rounding
ROUND = Decimal('0.01')


# =============================================================================
# SALARY COMPUTATION FUNCTIONS
# =============================================================================

def get_employee_salary(employee, payroll_date=None):
    """
    Get the applicable salary setting for an employee on a specific date.
    
    Args:
        employee: Staff instance
        payroll_date: date to check (defaults to today)
        
    Returns:
        EmployeeSalarySetting instance or None
        
    Raises:
        ValidationError: If no salary setting found for the date
    """
    today = payroll_date or timezone.now().date()
    
    salary_setting = EmployeeSalarySetting.get_active_salary(employee, today)
    
    if not salary_setting:
        raise ValidationError(
            f"No active salary setting found for {employee} on {today}. "
            "Please create a salary setting before processing payroll."
        )
    
    return salary_setting


def compute_tier_based_salary(base_salary, tier, payroll_date=None):
    """
    Compute salary based on tier threshold.
    
    For future KPI integration - tier multipliers affect salary.
    
    Args:
        base_salary: Decimal, base monthly salary
        tier: TierThresholdSetting instance or None
        payroll_date: date for tier lookup
        
    Returns:
        Decimal: Adjusted salary based on tier
    """
    if not tier:
        return base_salary
    
    # Tier multiplier (e.g., Tier 1 = 1.0000, Tier 2 = 1.0500)
    multiplier = tier.multiplier or Decimal('1.0000')
    
    adjusted_salary = (base_salary * multiplier).quantize(ROUND)
    
    return adjusted_salary


def compute_salary_per_cutoff(monthly_salary):
    """
    Compute salary per cutoff from monthly salary.
    
    Assumes 2 cutoffs per month.
    """
    return (monthly_salary / Decimal('2')).quantize(ROUND)


def compute_daily_rate(salary_per_cutoff, work_days=11):
    """
    Compute daily rate from salary per cutoff.
    
    Args:
        salary_per_cutoff: Decimal salary per cutoff
        work_days: Number of working days per cutoff (default 11)
        
    Returns:
        Decimal: Daily rate
    """
    return (salary_per_cutoff / Decimal(work_days)).quantize(ROUND)


def get_hours_per_day(work_schedule):
    """
    Return hours per day based on work schedule.
    Returns None for FLEX (no hourly computation needed).
    """
    schedule_map = {
        '8H': Decimal('8.0'),
        '9.5H': Decimal('9.5'),
        'FLEX': None,
    }
    return schedule_map.get(work_schedule, Decimal('9.5'))


def compute_hourly_rate(daily_rate, hours_per_day=None):
    """
    Compute hourly rate from daily rate.

    Args:
        daily_rate: Decimal daily rate
        hours_per_day: Decimal hours per day. If None (Flextime), returns None.

    Returns:
        Decimal: Hourly rate, or None for Flextime schedules
    """
    if hours_per_day is None:
        return None
    return (daily_rate / Decimal(str(hours_per_day))).quantize(ROUND)





# =============================================================================
# OVERTIME AND DIFFERENTIAL COMPUTATION
# =============================================================================

def compute_overtime_pay(hours, hourly_rate, rate_multiplier=Decimal('1.25')):
    """
    Compute overtime pay.
    
    Standard rate: 1.25x (25% premium)
    """
    return (hours * hourly_rate * rate_multiplier).quantize(ROUND)


def compute_nsd_pay(hours, hourly_rate, rate_multiplier=Decimal('1.10')):
    """
    Compute Night Shift Differential pay.
    
    Standard rate: 1.10x (10% premium)
    """
    return (hours * hourly_rate * rate_multiplier).quantize(ROUND)


def compute_holiday_pay(hours, hourly_rate, rate_multiplier=Decimal('1.30')):
    """
    Compute Special Holiday pay.
    
    Standard rate: 1.30x (30% premium)
    """
    return (hours * hourly_rate * rate_multiplier).quantize(ROUND)

def compute_regular_holiday_pay(hours, hourly_rate, rate_multiplier=Decimal('2.00')):
    """
    Compute Regular Holiday pay.
    
    Standard rate: 2x (Double pay)
    """
    return (hours * hourly_rate * rate_multiplier).quantize(ROUND)



# =============================================================================
# ATTENDANCE-BASED COMPUTATIONS
# =============================================================================

def get_cutoff_attendance(employee, cutoff_start, cutoff_end):
    """
    Get all attendance records for an employee in a cutoff period.
    """
    return Attendance.objects.filter(
        employee=employee,
        date__range=(cutoff_start, cutoff_end)
    ).order_by('date')


def compute_late_deduction(late_hours_equivalent, hourly_rate):
    """
    Compute deduction for late attendance.
    
    Formula: (hourly_rate / 60) * late_minutes
    """
    return (late_hours_equivalent * hourly_rate).quantize(ROUND)


def compute_absent_deduction(absent_days, daily_rate):
    """
    Compute deduction for absent days.
    """
    return (absent_days * daily_rate).quantize(ROUND)


def get_unpaid_leave_days(employee, cutoff_start, cutoff_end):
    """
    Get total unpaid leave days within a cutoff period.
    """
    leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='approved',
        start_date__lte=cutoff_end,
        end_date__gte=cutoff_start,
        is_paid=False  # Only unpaid leaves
    )
    
    total_days = Decimal('0.00')
    for leave in leaves:
        # Calculate overlap with cutoff
        overlap_start = max(leave.start_date, cutoff_start)
        overlap_end = min(leave.end_date, cutoff_end)
        overlap_days = (overlap_end - overlap_start).days + 1
        total_days += Decimal(overlap_days)
    
    return total_days


# =============================================================================
# DEDUCTION PROCESSING
# =============================================================================

def get_active_deduction_types(payroll_date=None, category=None):
    """
    Get active deduction types for payroll processing.
    """
    return DeductionType.get_active_types(payroll_date, category)


def get_attendance_deductions(payroll_date=None):
    """
    Get attendance-related deduction types (late, absent, etc.)
    """
    return DeductionType.get_attendance_deductions(payroll_date)


def compute_total_deductions(payroll_preview):
    """
    Compute total deductions from all sources.
    
    Includes:
    - Tax (manual input)
    - Attendance deductions (from deduction entries)
    - Leave deductions
    - Other deductions
    """
    total = payroll_preview.tax_amount
    
    # Add deduction entries
    for entry in payroll_preview.deduction_entries.all():
        total += entry.amount
    
    # Add leave deduction
    total += payroll_preview.leave_deduction
    
    # Add other deductions
    total += payroll_preview.other_deductions
    
    return total.quantize(ROUND)


# =============================================================================
# DE MINIMIS PROCESSING
# =============================================================================

def get_active_de_minimis_types(payroll_date=None):
    """
    Get all active de minimis types for a payroll date.
    """
    return DeMinimisType.get_active_types(payroll_date)


def compute_total_de_minimis(payroll_preview):
    """
    Compute total de minimis from all entries.
    """
    return sum(
        entry.amount 
        for entry in payroll_preview.demiminis_entries.all()
    ).quantize(ROUND)


# =============================================================================
# PAYROLL PREVIEW COMPUTATION
# =============================================================================

def compute_payroll_preview(preview):
    """
    Compute all calculated fields for a PayrollPreview.
    
    This function recalculates all computed fields based on:
    - Employee salary setting
    - HR inputs (hours, rates, amounts)
    - Attendance data
    
    Args:
        preview: PayrollPreview instance
        
    Returns:
        PayrollPreview with all computed fields updated
    """
    # Get salary setting
    if not preview.employee_salary_setting:
        salary_setting = get_employee_salary(preview.employee, preview.cutoff_start_date)
        preview.employee_salary_setting = salary_setting
        preview.base_salary_monthly = salary_setting.base_salary_monthly
    else:
        salary_setting = preview.employee_salary_setting
        preview.base_salary_monthly = salary_setting.base_salary_monthly
    
    # Compute salary per cutoff
    preview.salary_per_cutoff = compute_salary_per_cutoff(preview.base_salary_monthly)
    
    # Compute tier-based adjustment if applicable
    if salary_setting.tier:
        preview.tier = salary_setting.tier
        preview.tier_name = salary_setting.tier.tier_name
        preview.tier_threshold_percentage = salary_setting.tier.threshold_percentage
    
    # Compute daily and hourly rates
    daily_rate = compute_daily_rate(preview.salary_per_cutoff)
    
    # Determine work schedule from salary setting
    work_schedule = getattr(salary_setting, 'work_schedule', '9.5H')
    hours_per_day = get_hours_per_day(work_schedule)
    hourly_rate = compute_hourly_rate(daily_rate, hours_per_day)

    is_flextime = (work_schedule == 'FLEX' or hourly_rate is None)

    # OT, NSD, Holiday — zero out for Flextime (no hourly basis)
    if is_flextime:
        preview.overtime_amount = Decimal('0.00')
        preview.nsd_amount = Decimal('0.00')
        preview.holiday_amount = Decimal('0.00')
        preview.regular_holiday_amount = Decimal('0.00')
    else:
        preview.overtime_amount = compute_overtime_pay(
            preview.overtime_hours, hourly_rate, preview.overtime_rate
        )
        preview.nsd_amount = compute_nsd_pay(
            preview.nsd_hours, hourly_rate, preview.nsd_rate
        )
        preview.holiday_amount = compute_holiday_pay(
            preview.holiday_hours, hourly_rate, preview.holiday_rate
        )
        preview.regular_holiday_amount = compute_regular_holiday_pay(
            preview.regular_holiday_hours, hourly_rate, preview.regular_holiday_rate
        )




    # Leave deduction still uses daily rate regardless of schedule
    preview.leave_deduction = (preview.leave_days * daily_rate).quantize(ROUND)
    
    # Compute total additions
    preview.total_additions = (
        preview.overtime_amount +
        preview.nsd_amount +
        preview.holiday_amount +
        preview.regular_holiday_amount +
        preview.incentives +
        preview.tips_others +
        preview.lodging_allowance
    ).quantize(ROUND)
    
    # Compute gross earnings (salary + additions, excl de minimis)
    preview.gross_earnings = (preview.salary_per_cutoff + preview.total_additions).quantize(ROUND)
    
    # Compute total de minimis
    preview.total_de_minimis = compute_total_de_minimis(preview)
    
    # Taxable earnings
    preview.taxable_earnings = preview.gross_earnings
    
    # Compute total deductions
    # Note: late_deduction and absence_deduction should be pre-calculated and set on preview
    preview.total_deductions = (
        preview.tax_amount +
        preview.leave_deduction +
        preview.other_deductions
    ).quantize(ROUND)
    
    # Add late deduction if present
    if hasattr(preview, 'late_deduction') and preview.late_deduction:
        preview.total_deductions += preview.late_deduction
        preview.total_deductions = preview.total_deductions.quantize(ROUND)
    
    # Add absence deduction if present
    if hasattr(preview, 'absence_deduction') and preview.absence_deduction:
        preview.total_deductions += preview.absence_deduction
        preview.total_deductions = preview.total_deductions.quantize(ROUND)
    
    # Add deduction entries to total deductions
    for entry in preview.deduction_entries.all():
        preview.total_deductions += entry.amount
        preview.total_deductions = preview.total_deductions.quantize(ROUND)
    
    # Compute net pay
    preview.net_pay = (
        preview.salary_per_cutoff +
        preview.total_additions +
        preview.total_de_minimis -
        preview.total_deductions
    ).quantize(ROUND)
    
    return preview


def validate_payroll_preview(preview):
    """
    Validate a payroll preview for errors.
    
    Returns:
        tuple: (is_valid, error_list)
    """
    errors = []
    
    # Check net pay
    if preview.net_pay < Decimal('0.00'):
        errors.append(f"ERROR: Net pay is negative ({preview.net_pay:,.2f})")
    
    # Check tax doesn't exceed taxable earnings
    if preview.tax_amount > preview.taxable_earnings:
        errors.append(
            f"ERROR: Tax ({preview.tax_amount:,.2f}) exceeds "
            f"taxable earnings ({preview.taxable_earnings:,.2f})"
        )
    
    # Check salary setting exists
    if not preview.employee_salary_setting:
        errors.append("ERROR: No salary setting found for this employee")
    
    # Check for negative amounts
    fields_to_check = [
        ('overtime_hours', preview.overtime_hours),
        ('nsd_hours', preview.nsd_hours),
        ('holiday_hours', preview.holiday_hours),
        ('regular_holiday_hours', preview.regular_holiday_hours),
        ('leave_days', preview.leave_days),
        ('tax_amount', preview.tax_amount),
        ('other_deductions', preview.other_deductions),
        ('incentives', preview.incentives),
    ]
    
    for field_name, value in fields_to_check:
        if value < Decimal('0.00'):
            errors.append(f"ERROR: {field_name} cannot be negative ({value})")
    
    # Check cutoff dates
    if preview.cutoff_end_date < preview.cutoff_start_date:
        errors.append("ERROR: Cutoff end date is before start date")
    
    return len(errors) == 0, errors


def initialize_payroll_preview(employee, cutoff_start, cutoff_end, cutoff='1'):
    """
    Create and initialize a new PayrollPreview for an employee.
    
    This function:
    1. Creates a new PayrollPreview
    2. Loads the active salary setting
    3. Loads attendance data for the cutoff
    4. Pre-populates computed fields
    
    Args:
        employee: Staff instance
        cutoff_start: Date of cutoff start
        cutoff_end: Date of cutoff end
        cutoff: '1' or '2'
        
    Returns:
        PayrollPreview instance
    """
    # Get salary setting
    salary_setting = get_employee_salary(employee, cutoff_start)
    
    # Create preview
    # Create preview
    preview = PayrollPreview.objects.create(
        employee=employee,
        cutoff=cutoff,
        cutoff_start_date=cutoff_start,
        cutoff_end_date=cutoff_end,
        employee_salary_setting=salary_setting,
        base_salary_monthly=salary_setting.base_salary_monthly,
        salary_per_cutoff=salary_setting.salary_per_cutoff,
        work_schedule=salary_setting.work_schedule,
    )

    # Copy tier info if available
    if salary_setting.tier:
        preview.tier = salary_setting.tier
        preview.tier_name = salary_setting.tier.tier_name
        preview.tier_threshold_percentage = salary_setting.tier.threshold_percentage
        preview.save()

    # Load attendance data
    attendance = get_cutoff_attendance(employee, cutoff_start, cutoff_end)

    total_late_minutes = Decimal('0.00')
    total_ot_hours = Decimal('0.00')
    total_nsd_hours = Decimal('0.00')

    for att in attendance:
        if att.late_minutes:
            total_late_minutes += Decimal(att.late_minutes)
        if att.ot_hours:
            total_ot_hours += Decimal(str(att.ot_hours))
        if att.nsd_hours:
            total_nsd_hours += Decimal(str(att.nsd_hours))

    # Create attendance deduction entry
    attendance_deductions = get_attendance_deductions()
    late_type = attendance_deductions.filter(code='LATE').first()
    absent_type = attendance_deductions.filter(code='ABSENT').first()

    if late_type and total_late_minutes > 0:
        hours_per_day = get_hours_per_day(salary_setting.work_schedule)
        hourly_rate = compute_hourly_rate(
            compute_daily_rate(preview.salary_per_cutoff),
            hours_per_day
        )
        # Skip late deduction for Flextime (no hourly basis)
        if hourly_rate is not None:
            late_amount = compute_late_deduction(total_late_minutes, hourly_rate)
            DeductionEntry.objects.create(
                payroll_preview=preview,
                deduction_type=late_type,
                amount=late_amount,
                notes=f"Late: {total_late_minutes} minutes"
            )

    # Get unpaid leave days
    unpaid_leave_days = get_unpaid_leave_days(employee, cutoff_start, cutoff_end)
    preview.leave_days = unpaid_leave_days
    preview.save()

    # Load active de minimis types (create empty entries)
    de_minimis_types = get_active_de_minimis_types()
    for dm_type in de_minimis_types:
        DeMinimisEntry.objects.create(
            payroll_preview=preview,
            de_minimis_type=dm_type,
            amount=Decimal('0.00')
        )

    # Load deduction types
    deduction_types = get_active_deduction_types()
    for ded_type in deduction_types:
        DeductionEntry.objects.create(
            payroll_preview=preview,
            deduction_type=ded_type,
            amount=Decimal('0.00')
        )

    # Compute all fields
    preview = compute_payroll_preview(preview)
    preview.save()

    return preview


# =============================================================================
# PAYROLL POSTING
# =============================================================================

def post_payroll(preview, payroll_record, user):
    """
    Post a payroll preview to history.
    
    Creates an immutable PayrollHistory record and links it to the payroll batch.
    
    Args:
        preview: PayrollPreview instance to post
        payroll_record: PayrollRecord (batch) instance
        user: User performing the posting
        
    Returns:
        PayrollHistory instance
        
    Raises:
        ValidationError: If preview cannot be posted
    """
    # Validate
    is_valid, errors = validate_payroll_preview(preview)
    if not is_valid:
        raise ValidationError(
            f"Cannot post payroll with errors: {'; '.join(errors)}"
        )
    
    if not preview.can_post():
        raise ValidationError("Preview does not meet posting requirements")
    
    # Create history record
    history = PayrollHistory.create_from_preview(preview, payroll_record, user)
    
    # Update preview status
    preview.status = 'POSTED'
    preview.save()
    
    return history


# =============================================================================
# REPORTING HELPERS
# =============================================================================

def get_payroll_summary_for_period(cutoff_start, cutoff_end):
    """
    Get summary of all payroll history for a period.
    """
    return PayrollHistory.objects.filter(
        cutoff_start_date__gte=cutoff_start,
        cutoff_end_date__lte=cutoff_end
    ).select_related('employee', 'payroll_record')


def get_employee_payroll_history(employee, year=None):
    """
    Get payroll history for an employee, optionally filtered by year.
    """
    queryset = PayrollHistory.objects.filter(
        employee=employee
    ).order_by('-cutoff_start_date')
    
    if year:
        queryset = queryset.filter(cutoff_start_date__year=year)
    
    return queryset


# =============================================================================
# TIER UTILITIES (FOR FUTURE KPI INTEGRATION)
# =============================================================================

def get_tier_for_performance(performance_percentage, payroll_date=None):
    """
    Get the appropriate tier based on performance percentage.
    
    This function will be used by the future KPI module.
    
    Args:
        performance_percentage: Decimal (0-100)
        payroll_date: Date for tier lookup
        
    Returns:
        TierThresholdSetting or None
    """
    return TierThresholdSetting.get_tier_for_percentage(
        performance_percentage, 
        payroll_date
    )


def assign_employee_to_tier(employee, tier, effective_date, notes=None):
    """
    Assign an employee to a tier and create a new salary setting.
    
    This creates a new salary setting with the tier assignment.
    The salary amount may or may not change depending on configuration.
    
    Args:
        employee: Staff instance
        tier: TierThresholdSetting instance
        effective_date: Date for new salary setting
        notes: Optional notes
        
    Returns:
        EmployeeSalarySetting instance
    """
    # Get current salary to preserve amount
    current_salary = EmployeeSalarySetting.get_active_salary(employee)
    
    new_salary = EmployeeSalarySetting.objects.create(
        employee=employee,
        base_salary_monthly=current_salary.base_salary_monthly if current_salary else Decimal('0.00'),
        tier=tier,
        effective_start_date=effective_date,
        is_active=True,
        notes=notes or f"Assigned to {tier.tier_name}"
    )
    
    # Deactivate old salary if exists
    if current_salary:
        current_salary.effective_end_date = effective_date - timedelta(days=1)
        current_salary.is_active = False
        current_salary.save()
    
    return new_salary


# =============================================================================
# DATA MIGRATION HELPERS
# =============================================================================

def migrate_employee_salary_from_staff():
    """
    Migrate salary data from Staff model to EmployeeSalarySetting.
    
    This is a one-time migration function.
    """
    from App.users.models import Staff
    
    migrated = []
    for staff in Staff.objects.filter(monthly_salary__gt=0):
        # Check if salary setting already exists
        exists = EmployeeSalarySetting.objects.filter(
            employee=staff,
            effective_start_date__lte=timezone.now().date(),
            is_active=True
        ).exists()
        
        if not exists:
            setting = EmployeeSalarySetting.objects.create(
                employee=staff,
                base_salary_monthly=staff.monthly_salary,
                effective_start_date=timezone.now().date(),
                is_active=True,
                notes="Migrated from Staff.monthly_salary"
            )
            migrated.append(setting)
    
    return migrated


# =============================================================================
# SETTINGS VALIDATION
# =============================================================================

def validate_payroll_settings():
    """
    Validate all payroll settings are properly configured.
    
    Returns:
        tuple: (is_valid, warnings, errors)
    """
    warnings = []
    errors = []
    
    # Check for active de minimis types
    if not DeMinimisType.objects.filter(is_active=True).exists():
        warnings.append("No active de minimis types found")
    
    # Check for active deduction types
    if not DeductionType.objects.filter(is_active=True).exists():
        warnings.append("No active deduction types found")
    
    # Check for active tiers
    if not TierThresholdSetting.objects.filter(is_active=True).exists():
        warnings.append("No active tier thresholds found")
    
    # Check employees have salary settings
    from App.users.models import Staff
    employees_without_salary = Staff.objects.filter(
        salary_settings__isnull=True
    ).distinct()
    
    if employees_without_salary.exists():
        employees_list = ", ".join(
            [str(e) for e in employees_without_salary[:5]]
        )
        more = f" and {employees_without_salary.count() - 5} more" if employees_without_salary.count() > 5 else ""
        warnings.append(
            f"Employees without salary settings: {employees_list}{more}"
        )
    
    return len(errors) == 0, warnings, errors

