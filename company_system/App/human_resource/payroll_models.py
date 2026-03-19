# human_resource/payroll_models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone

# Import existing Staff model (adjust import path)
from App.users.models import Staff

# Bank types (small table)
class BankType(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class BankAccount(models.Model):
    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=64)
    bank = models.ForeignKey(BankType, on_delete=models.SET_NULL, null=True, blank=True)
    is_primary = models.BooleanField(default=True)

    class Meta:
        unique_together = ('employee', 'account_number')

    def __str__(self):
        return f"{self.employee} • {self.bank} • {self.account_number}"

# Payout per employee per finalized payout (per cutoff)
class Payout(models.Model):
    CUTOFF_CHOICES = [('1','1st'), ('2','2nd')]
    payroll_record = models.ForeignKey('PayrollRecord', on_delete=models.CASCADE, related_name='payouts')
    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True)
    gross = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_additions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cutoff = models.CharField(max_length=1, choices=CUTOFF_CHOICES)
    month = models.PositiveSmallIntegerField()  # 1-12
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    # optional pay slip file (PDF)
    payslip = models.FileField(upload_to='payslips/%Y/%m/', null=True, blank=True)
    # Added: Release tracking - individual per payout
    released = models.BooleanField(default=False)
    released_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='released_payouts')
    released_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.month}/{self.year} cutoff {self.cutoff}"

# Loan model with attachments
class Loan(models.Model):
    STATUS = [('pending','Pending'), ('approved','Approved'), ('disapproved','Disapproved'), ('closed','Closed')]
    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)
    principal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.00'))  # e.g. 0.05 = 5%
    term_months = models.PositiveIntegerField(default=1)  # in months
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    # store monthly deduction (computed)
    monthly_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    per_cutoff = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    # attachment
    attachment = models.FileField(upload_to='loan_docs/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # recompute totals when saving (if principal and term set)
        total_with_interest = self.principal + (self.principal * self.interest_rate)
        # guard division by zero
        if self.term_months and self.term_months > 0:
            self.monthly_deduction = (total_with_interest / Decimal(self.term_months)).quantize(Decimal('0.01'))
            # per cutoff (2 cutoffs per month)
            self.per_cutoff = (self.monthly_deduction / Decimal(2)).quantize(Decimal('0.01'))
            # initial balance if not set
            if self.balance == Decimal('0.00'):
                self.balance = total_with_interest
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Loan #{self.id} - {self.employee} ({self.principal})"

# BankAllocation (optional internal)
class BankAllocation(models.Model):
    bank = models.ForeignKey(BankType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    cutoff = models.CharField(max_length=1, choices=Payout.CUTOFF_CHOICES)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

# Benefit (shared deductions / benefits)
class Benefit(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2,
                                 help_text="Fixed amount per cutoff or percent if use_percent=True",
                                 default=Decimal('0.00'))
    use_percent = models.BooleanField(default=False)
    percent_value = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))  # 5% = 5.00
    def __str__(self): return self.name

class EmployeeBenefit(models.Model):
    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)
    benefit = models.ForeignKey(Benefit, on_delete=models.CASCADE)
    apply_per_cutoff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

# PayrollRecord = the finalized payroll batch (per cutoff)
class PayrollRecord(models.Model):
    CUTOFF_CHOICES = Payout.CUTOFF_CHOICES
    cutoff = models.CharField(max_length=1, choices=CUTOFF_CHOICES)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finalized = models.BooleanField(default=False)
    finalized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='finalized_payrolls')
    finalized_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payroll {self.month}/{self.year} cutoff {self.cutoff} - {self.created_at:%Y-%m-%d}"


# PayrollOverride - Tracks manual overrides to calculated payroll values
class PayrollOverride(models.Model):
    """Tracks manual overrides to calculated payroll values"""
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name='overrides')
    field_name = models.CharField(max_length=100)
    original_value = models.DecimalField(max_digits=12, decimal_places=2)
    override_value = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    overridden_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    overridden_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-overridden_at']

    def __str__(self):
        return f"Override on {self.payout} - {self.field_name}"


# PayrollAuditLog - Audit trail for all payroll operations
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
    employee = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    payout = models.ForeignKey(Payout, on_delete=models.SET_NULL, null=True, blank=True)
    before_values = models.JSONField(null=True, blank=True)
    after_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Payroll Audit Log'
        verbose_name_plural = 'Payroll Audit Logs'

    def __str__(self):
        return f"{self.action} by {self.user} at {self.timestamp}"


# Government Contribution Rates
class GovernmentContributionRate(models.Model):
    """Stores government contribution rates (SSS, PhilHealth, Pag-IBIG)"""
    CONTRIBUTION_TYPES = [
        ('SSS', 'Social Security System'),
        ('PHILHEALTH', 'PhilHealth'),
        ('PAGIBIG', 'Pag-IBIG'),
    ]
    contribution_type = models.CharField(max_length=20, choices=CONTRIBUTION_TYPES)
    salary_bracket_min = models.DecimalField(max_digits=12, decimal_places=2)
    salary_bracket_max = models.DecimalField(max_digits=12, decimal_places=2)
    employee_share = models.DecimalField(max_digits=12, decimal_places=2)
    employer_share = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['contribution_type', 'salary_bracket_min']

    def __str__(self):
        return f"{self.contribution_type} - {self.salary_bracket_min} to {self.salary_bracket_max}"


# Extended Payout Details for Individual Processing
class PayoutDetail(models.Model):
    """Stores detailed breakdown of payout calculations"""
    payout = models.OneToOneField(Payout, on_delete=models.CASCADE, related_name='details')

    # Earnings breakdown
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    housing_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    transportation_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    meal_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    night_differential = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    nsd_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    # Attendance details (single clean declaration each)
    working_days = models.PositiveIntegerField(default=0, help_text="Total working days in cutoff period")
    days_present = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    days_absent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    # Late tracking (single clean declaration each)
    late_occurrences = models.PositiveIntegerField(default=0, help_text="Number of times late during period")
    late_minutes = models.DecimalField(max_digits=10, decimal_places=0, default=Decimal('0'), help_text="Actual minutes late")
    late_hours_equivalent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), help_text="Hours charged as penalty")
    late_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), help_text="Late deduction amount")

    # Leave days
    leave_days_paid = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), help_text="Paid leave days")
    leave_days_unpaid = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), help_text="Unpaid leave days")

    # Deductions
    absence_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    loan_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Government contributions
    sss_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    philhealth_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pagibig_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Tax
    taxable_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_bracket = models.CharField(max_length=20, blank=True)
    withholding_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Additional earnings
    tips_others = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lodging_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    holiday_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    holiday_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    regular_holiday_pay = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    regular_holiday_hours = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    incentives = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Totals
    total_de_minimis = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_dynamic_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_government_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Note
    note = models.TextField(blank=True, default='')

    # Helper methods
    def get_daily_rate(self):
        if self.working_days and self.working_days > 0:
            return (self.basic_salary / self.working_days).quantize(Decimal('0.01'))
        return Decimal('0.00')

    def get_hourly_rate(self):
        """Get hourly rate — tries to read work_schedule from salary setting via payout employee."""
        daily = self.get_daily_rate()
        if daily == 0:
            return Decimal('0.00')
        try:
            from .payroll_settings_models import EmployeeSalarySetting
            salary_setting = EmployeeSalarySetting.objects.filter(
                employee=self.payout.employee,
                is_active=True,
            ).order_by('-effective_start_date').first()
            if salary_setting and salary_setting.work_schedule == '8H':
                hours = Decimal('8.0')
            elif salary_setting and salary_setting.work_schedule == 'FLEX':
                return Decimal('0.00')
            else:
                hours = Decimal('9.5')
        except Exception:
            hours = Decimal('9.5')
        return (daily / hours).quantize(Decimal('0.01'))

    def get_late_deduction_breakdown(self):
        if not self.late_deduction or self.late_deduction == 0:
            return None
        hourly = self.get_hourly_rate()
        return {
            'minutes': self.late_minutes,
            'hours_equivalent': self.late_hours_equivalent,
            'hourly_rate': hourly,
            'formula': f"{self.late_hours_equivalent} hrs × ₱{hourly} = ₱{self.late_deduction}",
        }

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Details for {self.payout}"


# Import models from payroll_settings_models.py to avoid conflicts
# and ensure all models are available from this module
from .payroll_settings_models import (
    TierThresholdSetting,
    EmployeeSalarySetting,
    DeMinimisType,
    DeductionType,
    PayrollHistory,
    PayrollPreview,
    DeMinimisEntry,
    DeductionEntry,
)

