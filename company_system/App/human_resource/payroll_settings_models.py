# human_resource/payroll_settings_models.py
"""
Dynamic Payroll Settings Models

These models support auditable, date-effective payroll configuration:
- EmployeeSalarySetting: Tracks employee salary history with effective dates
- TierThresholdSetting: Configurable tier thresholds for KPI integration
- DeMinimisType: Configurable de minimis allowance types
- DeductionType: Configurable deduction types with categories
- PayrollPreview: Temporary working table for payroll preview
- PayrollHistory: Immutable snapshot of posted payroll records
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError

# Import existing Staff model
from App.users.models import Staff


# =============================================================================
# TIER THRESHOLD SETTING
# =============================================================================
class TierThresholdSetting(models.Model):
    """
    Configurable tier thresholds for salary grading and KPI scoring.
    
    Supports date-effective changes and preserves history.
    Future-ready for KPI module integration.
    """
    TIER_CHOICES = [
        ('NESTING', 'Nesting'),
        ('TIER1', 'Tier 1'),
        ('TIER2', 'Tier 2'),
        ('TIER3', 'Tier 3'),
        ('TIER4', 'Tier 4'),
        ('TIER5', 'Tier 5'),
    ]
    
    tier_name = models.CharField(
        max_length=50,
        choices=TIER_CHOICES,
        help_text="Tier classification for salary grading"
    )
    tier_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Human-readable label (e.g., 'Entry Level', 'Senior')"
    )
    threshold_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Performance threshold percentage (e.g., 85.00, 92.00)"
    )
    multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('1.0000'),
        help_text="Salary multiplier for this tier (e.g., 1.0000, 1.0500)"
    )
    effective_start_date = models.DateField(
        help_text="First date this tier is effective"
    )
    effective_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this tier is effective (null for indefinite)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable this tier setting"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'human_resource_tierthresholdsetting'
        ordering = ['threshold_percentage']
        verbose_name = 'Tier Threshold Setting'
        verbose_name_plural = 'Tier Threshold Settings'
        constraints = [
            models.UniqueConstraint(
                fields=['tier_name', 'effective_start_date'],
                name='unique_tier_per_start_date'
            )
        ]
    
    def clean(self):
        """Validate tier settings with user-friendly error messages"""
        # Skip ALL validation if this is just updating is_active/effective_end_date for deactivation
        if getattr(self, '_deactivating_only', False):
            return
            
        # Skip overlap check if this is a new record being created during edit
        if getattr(self, '_skip_clean', False):
            return
            
        # Check end date is after start date
        if self.effective_end_date and self.effective_end_date < self.effective_start_date:
            raise ValidationError({
                'effective_end_date': f'Invalid date range: End date ({self.effective_end_date}) must be after start date ({self.effective_start_date}). Please select a valid end date.'
            })
        
        # Check for overlapping active records, EXCLUDING the record being edited
        overlap = TierThresholdSetting.objects.filter(
            tier_name=self.tier_name,
            is_active=True
        ).exclude(pk=self.pk)
        
        # Also exclude records that have the same effective_start_date
        overlap = overlap.exclude(effective_start_date=self.effective_start_date)
        
        if self.effective_end_date:
            overlap = overlap.filter(
                effective_start_date__lte=self.effective_end_date,
                effective_end_date__gte=self.effective_start_date
            )
        else:
            # If no end date, only check against records that are truly indefinite
            overlap = overlap.filter(
                effective_start_date__lte=self.effective_start_date,
                effective_end_date__isnull=True
            )
        
        if overlap.exists():
            existing = overlap.first()
            raise ValidationError(
                f'Cannot save: An active tier setting "{self.tier_name}" already exists from {existing.effective_start_date} to {existing.effective_end_date or "present"}.\n'
                f'Please either: (1) Set an end date before {existing.effective_start_date}, or (2) Deactivate the existing record first.'
            )
    
    def save(self, *args, **kwargs):
        """Override save to ensure data integrity"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.tier_name} ({self.threshold_percentage}%) - {self.effective_start_date}"
    
    @classmethod
    def get_active_tier(cls, payroll_date):
        """
        Get the applicable tier setting for a given date.
        Returns the tier with highest threshold <= given percentage.
        """
        today = payroll_date or timezone.now().date()
        return cls.objects.filter(
            effective_start_date__lte=today,
            is_active=True
        ).filter(
            models.Q(effective_end_date__isnull=True) |
            models.Q(effective_end_date__gte=today)
        ).order_by('-threshold_percentage').first()
    
    @classmethod
    def get_tier_for_percentage(cls, percentage, payroll_date):
        """Get tier for a specific performance percentage"""
        today = payroll_date or timezone.now().date()
        return cls.objects.filter(
            threshold_percentage__lte=percentage,
            effective_start_date__lte=today,
            is_active=True
        ).filter(
            models.Q(effective_end_date__isnull=True) |
            models.Q(effective_end_date__gte=today)
        ).order_by('-threshold_percentage').first()


# =============================================================================
# EMPLOYEE SALARY SETTING
# =============================================================================
class EmployeeSalarySetting(models.Model):
    """
    Employee salary configuration with full audit trail.
    
    Rules:
    - Salary changes MUST create a new record (no overwrites)
    - Only ONE active salary record per employee per date
    - Payroll preview pulls salary based on payroll date
    - Preserves complete salary history for audit
    """
    WORK_SCHEDULE_CHOICES = [
        ('8H', '8 Hours'),
        ('9.5H', '9.5 Hours'),
        ('FLEX', 'Flextime'),
    ]
   
    employee = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='salary_settings',
        help_text="Employee for salary setting"
    )
    base_salary_monthly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monthly base salary before any adjustments"
    )
    tier = models.ForeignKey(
        TierThresholdSetting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_salary_settings',
        help_text="Assigned tier for this salary period"
    )

    work_schedule = models.CharField(
        max_length=10,
        choices=WORK_SCHEDULE_CHOICES,
        default='9.5H',
        help_text="Working hour arrangement: 8H, 9.5H, or Flextime (salary-based, no hourly computation)"
    )


    salary_per_cutoff = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Computed salary per cutoff (monthly / 2)",
        editable=False
    )
    effective_start_date = models.DateField(
        help_text="First date this salary is effective"
    )
    effective_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this salary is effective (null for current/indefinite)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this salary setting is currently active"
    )



    

    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for salary change or notes"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'human_resource_employeesalarysetting'
        ordering = ['-effective_start_date', '-created_at']
        verbose_name = 'Employee Salary Setting'
        verbose_name_plural = 'Employee Salary Settings'
        indexes = [
            models.Index(fields=['employee', 'effective_start_date']),
            models.Index(fields=['employee', 'is_active']),
        ]
    
    def clean(self):
        """Validate salary setting with user-friendly error messages"""
        # Skip ALL validation if this is just updating is_active/effective_end_date for deactivation
        # This happens when _deactivating_only flag is set (during edit workflow)
        if getattr(self, '_deactivating_only', False):
            return
        
        # Skip overlap check if this is a new record being created during edit
        # (indicated by _skip_clean flag set by the view)
        if getattr(self, '_skip_clean', False):
            return
            
        # Handle empty or None end dates - allow None (no end date)
        if self.effective_end_date and self.effective_end_date < self.effective_start_date:
            raise ValidationError({
                'effective_end_date': f'Invalid date range: End date ({self.effective_end_date}) must be after start date ({self.effective_start_date}). Please select a valid end date or leave it blank.'
            })
        
        # Auto-compute salary per cutoff
        self.salary_per_cutoff = (self.base_salary_monthly / Decimal('2')).quantize(Decimal('0.01'))
        
        # Check for overlapping active salary records for the same employee
        # EXCLUDING the record being edited
        overlap = EmployeeSalarySetting.objects.filter(
            employee=self.employee,
            is_active=True
        ).exclude(pk=self.pk)
        
        # Also exclude records that have the same effective_start_date
        overlap = overlap.exclude(effective_start_date=self.effective_start_date)
        
        # Check overlap conditions
        if self.effective_end_date:
            overlap = overlap.filter(
                effective_start_date__lte=self.effective_end_date,
                effective_end_date__gte=self.effective_start_date
            )
        else:
            # If no end date, check against records that overlap the start date
            from django.utils import timezone
            today = timezone.now().date()
            overlap = overlap.filter(
                effective_start_date__lte=self.effective_start_date,
                effective_end_date__gte=self.effective_start_date
            ).filter(
                models.Q(effective_end_date__isnull=True) | models.Q(effective_end_date__gte=today)
            )
        
        if overlap.exists():
            existing = overlap.first()
            employee_name = self.employee.get_full_name() if hasattr(self.employee, 'get_full_name') else str(self.employee)
            raise ValidationError(
                f'Cannot save: {employee_name} already has an active salary setting effective from {existing.effective_start_date} to {existing.effective_end_date or "present"}.\n'
                f'Note: Only ONE active salary record is allowed per employee per date. To create a new salary record, please either:\n'
                f'• Set the end date of the existing record to a date before the new start date, or\n'
                f'• Deactivate the existing record first.'
            )
    
    def save(self, *args, **kwargs):
        """Override save to compute salary per cutoff and ensure validation"""
        self.full_clean()
        # Auto-compute salary per cutoff
        if self.base_salary_monthly:
            self.salary_per_cutoff = (self.base_salary_monthly / Decimal('2')).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        end = self.effective_end_date or "Present"
        return f"{self.employee} - {self.base_salary_monthly:,.2f}/mo ({self.effective_start_date} to {end}) - {status}"
    
    @classmethod
    def get_active_salary(cls, employee, payroll_date):
        """
        Get the applicable salary setting for an employee on a specific date.
        
        Args:
            employee: Staff instance
            payroll_date: date to check salary effectiveness
            
        Returns:
            EmployeeSalarySetting or None
        """
        today = payroll_date or timezone.now().date()
        return cls.objects.filter(
            employee=employee,
            effective_start_date__lte=today,
            is_active=True
        ).filter(
            models.Q(effective_end_date__isnull=True) |
            models.Q(effective_end_date__gte=today)
        ).order_by('-effective_start_date').first()
    
    @classmethod
    def get_salary_history(cls, employee):
        """Get complete salary history for an employee"""
        return cls.objects.filter(
            employee=employee
        ).order_by('-effective_start_date')
    
    @property
    def is_current(self):
        """Check if this salary setting is currently active"""
        today = timezone.now().date()
        return (
            self.is_active and
            self.effective_start_date <= today and
            (self.effective_end_date is None or self.effective_end_date >= today)
        )


# =============================================================================
# DE MINIMIS TYPE SETTING
# =============================================================================
class DeMinimisType(models.Model):
    """
    Configurable de minimis allowance types.
    
    Controls which allowance fields appear in payroll preview.
    HR inputs only the AMOUNT - the type is controlled here.
    Settings changes must not affect past payroll history.
    """
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Rice Allowance', 'Food Allowance')"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for identification (e.g., 'RICE', 'FOOD', 'GAS')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of this de minimis allowance"
    )
    is_taxable = models.BooleanField(
        default=False,
        help_text="Whether this de minimis is included in taxable income"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable this de minimis type"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which this appears in payroll forms"
    )
    effective_start_date = models.DateField(
        help_text="First date this de minimis type is effective"
    )
    effective_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this de minimis type is effective"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'human_resource_deminimistype'
        ordering = ['display_order', 'name']
        verbose_name = 'De Minimis Type'
        verbose_name_plural = 'De Minimis Types'
    
    def clean(self):
        """Validate de minimis type with user-friendly error messages"""
        # Skip ALL validation if this is just updating is_active/effective_end_date for deactivation
        if getattr(self, '_deactivating_only', False):
            return
            
        # Skip overlap check if this is a new record being created during edit
        if getattr(self, '_skip_clean', False):
            return
            
        # Check end date is after start date
        if self.effective_end_date and self.effective_end_date < self.effective_start_date:
            raise ValidationError({
                'effective_end_date': f'Invalid date range: End date ({self.effective_end_date}) must be after start date ({self.effective_start_date}). Please select a valid end date or leave it blank.'
            })
        
        # Check for unique code, excluding current instance
        if self.pk:
            # Editing existing record - exclude self from check
            existing = DeMinimisType.objects.filter(code__iexact=self.code).exclude(pk=self.pk).first()
        else:
            # New record
            existing = DeMinimisType.objects.filter(code__iexact=self.code).first()
        
        if existing:
            raise ValidationError({
                'code': f'Code "{self.code}" is already used by "{existing.name}". Please use a different code.'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({self.code}) - {status}"
    
    @classmethod
    def get_active_types(cls, payroll_date=None):
        """Get all active de minimis types for a given date"""
        today = payroll_date or timezone.now().date()
        return cls.objects.filter(
            is_active=True,
            effective_start_date__lte=today
        ).filter(
            models.Q(effective_end_date__isnull=True) |
            models.Q(effective_end_date__gte=today)
        ).order_by('display_order')


# =============================================================================
# DEDUCTION TYPE SETTING
# =============================================================================
class DeductionType(models.Model):
    """
    Configurable deduction types for payroll deductions.
    
    Categories:
    - ATTENDANCE: Late, absent, etc.
    - GOVERNMENT: SSS, PhilHealth, Pag-IBIG
    - LOAN: Cash advances, loans
    - OTHER: Other miscellaneous deductions
    """
    CATEGORY_CHOICES = [
        ('ATTENDANCE', 'Attendance'),
        ('GOVERNMENT', 'Government'),
        ('LOAN', 'Loan/Cash Advance'),
        ('INSURANCE', 'Insurance'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Late Deduction', 'Cash Advance')"
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique code (e.g., 'LATE', 'ABSENT', 'CA')"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text="Category for this deduction"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of this deduction type"
    )
    is_government = models.BooleanField(
        default=False,
        help_text="Whether this is a government deduction (SSS, PhilHealth, etc.)"
    )
    is_tax_applicable = models.BooleanField(
        default=False,
        help_text="Whether this deduction reduces taxable income"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable this deduction type"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which this appears in payroll forms"
    )
    effective_start_date = models.DateField(
        help_text="First date this deduction type is effective"
    )
    effective_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this deduction type is effective"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'human_resource_deductiontype'
        ordering = ['category', 'display_order', 'name']
        verbose_name = 'Deduction Type'
        verbose_name_plural = 'Deduction Types'
    
    def clean(self):
        """Validate deduction type with user-friendly error messages"""
        # Skip ALL validation if this is just updating is_active/effective_end_date for deactivation
        if getattr(self, '_deactivating_only', False):
            return
            
        # Skip overlap check if this is a new record being created during edit
        if getattr(self, '_skip_clean', False):
            return
            
        # Check end date is after start date
        if self.effective_end_date and self.effective_end_date < self.effective_start_date:
            raise ValidationError({
                'effective_end_date': f'Invalid date range: End date ({self.effective_end_date}) must be after start date ({self.effective_start_date}). Please select a valid end date or leave it blank.'
            })
        
        # Check for unique code, excluding current instance
        if self.pk:
            # Editing existing record - exclude self from check
            existing = DeductionType.objects.filter(code__iexact=self.code).exclude(pk=self.pk).first()
        else:
            # New record
            existing = DeductionType.objects.filter(code__iexact=self.code).first()
        
        if existing:
            raise ValidationError({
                'code': f'Code "{self.code}" is already used by "{existing.name}" ({existing.category}). Please use a different code.'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({self.category}) - {status}"
    
    @classmethod
    def get_active_types(cls, payroll_date=None, category=None):
        """Get active deduction types for a given date, optionally filtered by category"""
        today = payroll_date or timezone.now().date()
        queryset = cls.objects.filter(
            is_active=True,
            effective_start_date__lte=today
        ).filter(
            models.Q(effective_end_date__isnull=True) |
            models.Q(effective_end_date__gte=today)
        )
        
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('display_order')
    
    @classmethod
    def get_attendance_deductions(cls, payroll_date=None):
        """Get attendance-related deduction types"""
        return cls.get_active_types(payroll_date, category='ATTENDANCE')
    
    @classmethod
    def get_government_deductions(cls, payroll_date=None):
        """Get government deduction types"""
        return cls.get_active_types(payroll_date, category='GOVERNMENT')


# =============================================================================
# EMPLOYEE DEDUCTION ACCOUNT (Per employee deduction account numbers)
# =============================================================================
class EmployeeDeductionAccount(models.Model):
    """
    Individual employee deduction accounts with government-provided account numbers.
    
    This model stores:
    - Government deduction account numbers (SSS, PhilHealth, Pag-IBIG)
    - Attendance deduction settings
    - Insurance deduction account numbers (if employee has insurance)
    
    Each employee can have multiple deduction accounts based on deduction type.
    """
    employee = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='deduction_accounts',
        help_text="Employee for this deduction account"
    )
    deduction_type = models.ForeignKey(
        DeductionType,
        on_delete=models.CASCADE,
        related_name='employee_accounts',
        help_text="Type of deduction (government, attendance, insurance)"
    )
    account_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Government-provided account number (e.g., SSS number, PhilHealth ID)"
    )
    employer_account_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Employer's account number for this deduction type"
    )
    has_insurance = models.BooleanField(
        default=False,
        help_text="Whether the employee has insurance coverage for this deduction type"
    )
    insurance_policy_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Insurance policy number if employee has insurance"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this deduction account is currently active"
    )
    effective_start_date = models.DateField(
        default=timezone.now,
        help_text="First date this deduction account is effective"
    )
    effective_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this deduction account is effective"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about this deduction account"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'human_resource_employeendeductionaccount'
        ordering = ['employee', 'deduction_type']
        verbose_name = 'Employee Deduction Account'
        verbose_name_plural = 'Employee Deduction Accounts'
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'deduction_type', 'effective_start_date'],
                name='unique_deduction_account_per_employee_type_date'
            )
        ]
        indexes = [
            models.Index(fields=['employee', 'is_active']),
            models.Index(fields=['deduction_type', 'is_active']),
        ]
    
    def clean(self):
        """Validate deduction account"""
        # Skip validation for deactivation
        if getattr(self, '_deactivating_only', False):
            return
            
        if getattr(self, '_skip_clean', False):
            return
        
        # Check end date is after start date
        if self.effective_end_date and self.effective_end_date < self.effective_start_date:
            raise ValidationError({
                'effective_end_date': f'Invalid date range: End date must be after start date.'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee} - {self.deduction_type.name}: {self.account_number or 'No Account'}"
    
    @classmethod
    def get_active_account(cls, employee, deduction_type, payroll_date=None):
        """Get the active deduction account for an employee and deduction type"""
        today = payroll_date or timezone.now().date()
        return cls.objects.filter(
            employee=employee,
            deduction_type=deduction_type,
            is_active=True,
            effective_start_date__lte=today
        ).filter(
            models.Q(effective_end_date__isnull=True) |
            models.Q(effective_end_date__gte=today)
        ).first()
    
    @classmethod
    def get_employee_accounts(cls, employee, payroll_date=None, category=None):
        """Get all active deduction accounts for an employee, optionally filtered by category"""
        today = payroll_date or timezone.now().date()
        queryset = cls.objects.filter(
            employee=employee,
            is_active=True,
            effective_start_date__lte=today
        ).filter(
            models.Q(effective_end_date__isnull=True) |
            models.Q(effective_end_date__gte=today)
        )
        
        if category:
            queryset = queryset.filter(deduction_type__category=category)
        
        return queryset.select_related('deduction_type')


# =============================================================================
# DE MINIMIS ENTRY (Per payroll instance)
# =============================================================================
class DeMinimisEntry(models.Model):
    """
    Individual de minimis entry for a payroll preview/posting.
    Stores the amount entered by HR for each de minimis type.
    """
    payroll_preview = models.ForeignKey(
        'PayrollPreview',
        on_delete=models.CASCADE,
        related_name='demiminis_entries',
        null=True,
        blank=True
    )
    payroll_history = models.ForeignKey(
        'PayrollHistory',
        on_delete=models.CASCADE,
        related_name='demiminis_entries',
        null=True,
        blank=True
    )
    payout = models.ForeignKey(
        'Payout',
        on_delete=models.CASCADE,
        related_name='demiminis_entries',
        null=True,
        blank=True,
        help_text="Payout reference for individual payroll"
    )
    de_minimis_type = models.ForeignKey(
        DeMinimisType,
        on_delete=models.PROTECT,
        help_text="Type of de minimis allowance"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount for this de minimis"
    )
    
    class Meta:
        db_table = 'human_resource_deminimisentry'
        verbose_name = 'De Minimis Entry'
        verbose_name_plural = 'De Minimis Entries'
    
    def __str__(self):
        source = self.payroll_preview or self.payroll_history
        return f"{self.de_minimis_type.name}: {self.amount:,.2f}"


# =============================================================================
# DEDUCTION ENTRY (Per payroll instance)
# =============================================================================
class DeductionEntry(models.Model):
    """
    Individual deduction entry for a payroll preview/posting.
    Stores the amount for each deduction type.
    """
    payroll_preview = models.ForeignKey(
        'PayrollPreview',
        on_delete=models.CASCADE,
        related_name='deduction_entries',
        null=True,
        blank=True
    )
    payroll_history = models.ForeignKey(
        'PayrollHistory',
        on_delete=models.CASCADE,
        related_name='deduction_entries',
        null=True,
        blank=True
    )
    payout = models.ForeignKey(
        'Payout',
        on_delete=models.CASCADE,
        related_name='deduction_entries',
        null=True,
        blank=True,
        help_text="Payout reference for individual payroll"
    )
    deduction_type = models.ForeignKey(
        DeductionType,
        on_delete=models.PROTECT,
        help_text="Type of deduction"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount for this deduction"
    )
    # For government deductions, store the rate used
    rate_used = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Rate percentage used for calculation"
    )
    # Notes for this deduction entry
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for this deduction"
    )
    
    class Meta:
        db_table = 'human_resource_deductionentry'
        verbose_name = 'Deduction Entry'
        verbose_name_plural = 'Deduction Entries'
    
    def __str__(self):
        source = self.payroll_preview or self.payroll_history
        return f"{self.deduction_type.name}: {self.amount:,.2f}"


# =============================================================================
# PAYROLL PREVIEW (Working table)
# =============================================================================
class PayrollPreview(models.Model):
    """
    Temporary working table for payroll preview before posting.
    
    Contains both auto-computed and HR-input values.
    All values are recomputed until payroll is posted.
    """
    CUTOFF_CHOICES = [('1', '1st Cutoff'), ('2', '2nd Cutoff')]
    
    # Core identifiers
    employee = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='payroll_previews',
        help_text="Employee for this payroll preview"
    )
    payroll_record = models.ForeignKey(
        'PayrollRecord',
        on_delete=models.CASCADE,
        related_name='previews',
        null=True,
        blank=True,
        help_text="Associated payroll record"
    )
    cutoff = models.CharField(
        max_length=1,
        choices=CUTOFF_CHOICES,
        help_text="Payroll cutoff period"
    )
    cutoff_start_date = models.DateField(
        help_text="Start date of this cutoff period"
    )
    cutoff_end_date = models.DateField(
        help_text="End date of this cutoff period"
    )
    
    # Salary snapshot (from EmployeeSalarySetting at time of preview)
    employee_salary_setting = models.ForeignKey(
        EmployeeSalarySetting,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payroll_previews',
        help_text="Salary setting used for this preview"
    )
    base_salary_monthly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Snapshot of base monthly salary"
    )
    salary_per_cutoff = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Snapshot of salary per cutoff"
    )
    
    # Tier snapshot (from TierThresholdSetting)
    tier = models.ForeignKey(
        TierThresholdSetting,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payroll_previews',
        help_text="Tier threshold used for this preview"
    )
    tier_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Snapshot of tier name"
    )
    tier_threshold_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Snapshot of tier threshold percentage"
    )
    
    # Auto-computed earnings (READ-ONLY in UI)
    gross_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total earnings (salary + additions, excluding de minimis)"
    )
    
    # HR-input additions (from settings)
    overtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Overtime hours worked"
    )
    overtime_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.25'),
        help_text="Overtime rate multiplier"
    )
    overtime_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Computed overtime pay (read-only)"
    )
    
    nsd_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Night Shift Differential hours"
    )
    nsd_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.10'),
        help_text="NSD rate multiplier"
    )
    nsd_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Computed NSD amount (read-only)"
    )
    
    holiday_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Holiday hours worked"
    )
    holiday_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.30'),
        help_text="Holiday rate multiplier"
    )
    holiday_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Computed holiday pay (read-only)"
    )
    
    regular_holiday_hours = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Regular holiday hours worked (double pay)"
    )
    regular_holiday_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('2.00'),
        help_text="Regular holiday rate (2.00 = double pay)"
    )
    regular_holiday_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Computed regular holiday pay"
    )



    incentives = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Additional incentives/bonus"
    )
    
    # Additional HR-input additions (Tips and Lodging)
    tips_others = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tips or other additional earnings"
    )
    lodging_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Lodging allowance"
    )
    
    # Leave deductions
    leave_days = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Unpaid leave days"
    )
    leave_deduction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Computed leave deduction (read-only)"
    )
    
    # Total additions (auto-computed)
    total_additions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total additions (OT + NSD + Holiday + Incentives)"
    )
    
    # De minimis total
    total_de_minimis = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total de minimis allowances"
    )
    
    # Total taxable earnings
    taxable_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total taxable earnings (for tax calculation)"
    )
    
    # HR-input tax (manual entry)
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Manual tax amount entered by HR"
    )
    
    # Other deductions
    other_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Other manual deductions"
    )
    
    # Total deductions (auto-computed)
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total deductions (tax + leave + other)"
    )
    
    # Net pay (auto-computed)
    net_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Net pay after all deductions"
    )
    
    # Status tracking
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('VALIDATED', 'Validated'),
        ('ERROR', 'Error'),
        ('POSTED', 'Posted'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Current status of this payroll preview"
    )
    validation_errors = models.TextField(
        blank=True,
        null=True,
        help_text="Comma-separated validation error messages"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payroll_previews_created'
    )
    
    class Meta:
        db_table = 'human_resource_payrollpreview'
        ordering = ['-cutoff_start_date', 'employee']
        verbose_name = 'Payroll Preview'
        verbose_name_plural = 'Payroll Previews'
        unique_together = [
            ['employee', 'cutoff_start_date', 'cutoff_end_date']
        ]
    
    def clean(self):
        """Validate payroll preview"""
        errors = []
        
        # Check net pay
        if self.net_pay < Decimal('0.00'):
            errors.append("Net pay cannot be negative")
        
        # Check tax doesn't exceed taxable earnings
        if self.tax_amount > self.taxable_earnings:
            errors.append(f"Tax ({self.tax_amount}) cannot exceed taxable earnings ({self.taxable_earnings})")
        
        # Validate salary setting exists
        if not self.employee_salary_setting:
            # Try to find one
            salary = EmployeeSalarySetting.get_active_salary(
                self.employee, 
                self.cutoff_start_date
            )
            if salary:
                self.employee_salary_setting = salary
                self.base_salary_monthly = salary.base_salary_monthly
                self.salary_per_cutoff = salary.salary_per_cutoff
            else:
                errors.append(f"No salary setting found for {self.employee} on {self.cutoff_start_date}")
        
        if errors:
            self.validation_errors = "; ".join(errors)
            self.status = 'ERROR'
        else:
            self.validation_errors = None
            self.status = 'VALIDATED' if self.status == 'DRAFT' else self.status
    
    def save(self, *args, **kwargs):
        """Override save to compute all auto-calculated fields"""
        # Compute salary per cutoff from salary setting if not set
        if self.employee_salary_setting and not self.salary_per_cutoff:
            self.salary_per_cutoff = self.employee_salary_setting.salary_per_cutoff
            self.base_salary_monthly = self.employee_salary_setting.base_salary_monthly
        
        # Copy tier info from salary setting
        if self.employee_salary_setting and self.employee_salary_setting.tier:
            tier = self.employee_salary_setting.tier
            self.tier = tier
            self.tier_name = tier.tier_name
            self.tier_threshold_percentage = tier.threshold_percentage
        
        # Compute overtime amount
        self.overtime_amount = (
            self.overtime_hours * 
            (self.salary_per_cutoff / Decimal('11') / Decimal('8')) * 
            self.overtime_rate
        ).quantize(Decimal('0.01'))
        
        # Compute NSD amount
        self.nsd_amount = (
            self.nsd_hours * 
            (self.salary_per_cutoff / Decimal('11') / Decimal('8')) * 
            self.nsd_rate
        ).quantize(Decimal('0.01'))
        
        # Compute holiday amount
        self.holiday_amount = (
            self.holiday_hours * 
            (self.salary_per_cutoff / Decimal('11') / Decimal('8')) * 
            self.holiday_rate
        ).quantize(Decimal('0.01'))
        
        # Compute leave deduction
        daily_rate = (self.salary_per_cutoff / Decimal('11')).quantize(Decimal('0.01'))
        self.leave_deduction = (self.leave_days * daily_rate).quantize(Decimal('0.01'))
        
        # Compute totals
        self.total_additions = (
            self.overtime_amount + 
            self.nsd_amount + 
            self.holiday_amount + 
            self.incentives +
            self.tips_others +
            self.lodging_allowance
        ).quantize(Decimal('0.01'))
        
        # Gross earnings = salary + additions (excludes de minimis)
        self.gross_earnings = (self.salary_per_cutoff + self.total_additions).quantize(Decimal('0.01'))
        
        # Taxable earnings = gross earnings (excluding de minimis)
        self.taxable_earnings = self.gross_earnings
        
        # Total deductions = tax + leave deduction + other deductions
        self.total_deductions = (
            self.tax_amount + 
            self.leave_deduction + 
            self.other_deductions
        ).quantize(Decimal('0.01'))
        
        # Net pay
        self.net_pay = (
            self.salary_per_cutoff + 
            self.total_additions + 
            self.total_de_minimis - 
            self.total_deductions
        ).quantize(Decimal('0.01'))
        
        # Run validation
        self.full_clean()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Preview: {self.employee} - {self.cutoff_start_date} to {self.cutoff_end_date} ({self.cutoff})"
    
    def get_all_deductions(self):
        """Get all deduction entries plus inline deductions"""
        entries = list(self.deduction_entries.all())
        entries.extend([
            ('tax', self.tax_amount),
            ('leave_deduction', self.leave_deduction),
            ('other_deductions', self.other_deductions),
        ])
        return entries
    
    def get_all_demiminis(self):
        """Get all de minimis entries"""
        return list(self.demiminis_entries.all())
    
    def can_post(self):
        """Check if payroll can be posted"""
        return (
            self.status == 'VALIDATED' and
            self.net_pay >= Decimal('0.00') and
            self.employee_salary_setting is not None
        )


# =============================================================================
# PAYROLL HISTORY (Immutable snapshot)
# =============================================================================
class PayrollHistory(models.Model):
    """
    Immutable snapshot of posted payroll.
    
    Once payroll is posted, a snapshot is created here.
    This record NEVER changes - corrections must use Adjustment records.
    """
    CUTOFF_CHOICES = [('1', '1st Cutoff'), ('2', '2nd Cutoff')]
    
    # Core identifiers (from PayrollPreview)
    employee = models.ForeignKey(
        Staff,
        on_delete=models.PROTECT,
        related_name='payroll_history',
        help_text="Employee for this payroll record"
    )
    payroll_record = models.ForeignKey(
        'PayrollRecord',
        on_delete=models.PROTECT,
        related_name='history',
        help_text="Associated payroll batch record"
    )
    cutoff = models.CharField(
        max_length=1,
        choices=CUTOFF_CHOICES,
        help_text="Payroll cutoff period"
    )
    cutoff_start_date = models.DateField()
    cutoff_end_date = models.DateField()
    
    # Salary snapshot (immutable copy)
    employee_salary_setting_id = models.PositiveIntegerField(
        help_text="ID of the salary setting used (for audit)"
    )
    base_salary_monthly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Snapshot of base monthly salary"
    )
    salary_per_cutoff = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Snapshot of salary per cutoff"
    )
    
    # Tier snapshot
    tier_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of tier setting used"
    )
    tier_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Snapshot of tier name"
    )
    tier_threshold_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Snapshot of tier threshold"
    )
    
    # Earnings snapshot
    gross_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total earnings (salary + additions, excl de minimis)"
    )
    overtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    overtime_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    nsd_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    nsd_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    holiday_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    holiday_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )


    regular_holiday_hours = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Regular holiday hours worked (double pay)"
    )
    regular_holiday_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Computed regular holiday pay"
    )



    incentives = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    leave_days = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    leave_deduction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_additions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # De minimis snapshot
    total_de_minimis = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total de minimis allowances"
    )
    
    # Deductions snapshot
    taxable_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Taxable earnings for this period"
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tax deducted"
    )
    other_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Other deductions"
    )
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total deductions"
    )
    
    # Net pay
    net_pay = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Final net pay"
    )
    
    # Metadata
    posted_at = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payroll_history_posted'
    )
    original_preview_id = models.PositiveIntegerField(
        help_text="ID of original PayrollPreview"
    )
    
    # JSON snapshot of complete data (for full audit)
    complete_snapshot = models.JSONField(
        default=dict,
        help_text="Complete snapshot of all values as JSON"
    )
    
    class Meta:
        db_table = 'human_resource_payrollhistory'
        ordering = ['-cutoff_start_date', 'employee']
        verbose_name = 'Payroll History'
        verbose_name_plural = 'Payroll History'
        indexes = [
            models.Index(fields=['employee', 'cutoff_start_date']),
            models.Index(fields=['payroll_record']),
        ]
    
    def __str__(self):
        return f"History: {self.employee} - {self.cutoff_start_date} to {self.cutoff_end_date} - Net: {self.net_pay:,.2f}"
    
    @classmethod
    def create_from_preview(cls, preview, payroll_record, user):
        """
        Create an immutable history record from a PayrollPreview.
        
        Args:
            preview: PayrollPreview instance
            payroll_record: PayrollRecord instance
            user: User who posted the payroll
            
        Returns:
            PayrollHistory instance
        """
        # Get de minimis entries
        demiminis_entries = []
        for entry in preview.demiminis_entries.all():
            demiminis_entries.append({
                'type_id': entry.de_minimis_type_id,
                'type_name': entry.de_minimis_type.name,
                'type_code': entry.de_minimis_type.code,
                'amount': str(entry.amount),
            })
        
        # Get deduction entries
        deduction_entries = []
        for entry in preview.deduction_entries.all():
            deduction_entries.append({
                'type_id': entry.deduction_type_id,
                'type_name': entry.deduction_type.name,
                'type_code': entry.deduction_type.code,
                'category': entry.deduction_type.category,
                'amount': str(entry.amount),
            })
        
        # Create complete snapshot
        complete_snapshot = {
            'preview_id': preview.id,
            'employee_id': preview.employee_id,
            'salary_setting_id': preview.employee_salary_setting_id if preview.employee_salary_setting else None,
            'base_salary_monthly': str(preview.base_salary_monthly),
            'salary_per_cutoff': str(preview.salary_per_cutoff),
            'tier': {
                'id': preview.tier_id,
                'name': preview.tier_name,
                'threshold_percentage': str(preview.tier_threshold_percentage) if preview.tier_threshold_percentage else None,
            },
            'earnings': {
                'gross_earnings': str(preview.gross_earnings),
                'overtime_hours': str(preview.overtime_hours),
                'overtime_amount': str(preview.overtime_amount),
                'nsd_hours': str(preview.nsd_hours),
                'nsd_amount': str(preview.nsd_amount),
                'holiday_hours': str(preview.holiday_hours),
                'holiday_amount': str(preview.holiday_amount),
                'incentives': str(preview.incentives),
                'leave_days': str(preview.leave_days),
                'leave_deduction': str(preview.leave_deduction),
                'total_additions': str(preview.total_additions),
            },
            'de_minimis': {
                'total': str(preview.total_de_minimis),
                'entries': demiminis_entries,
            },
            'deductions': {
                'taxable_earnings': str(preview.taxable_earnings),
                'tax_amount': str(preview.tax_amount),
                'other_deductions': str(preview.other_deductions),
                'leave_deduction': str(preview.leave_deduction),
                'total_deductions': str(preview.total_deductions),
                'entries': deduction_entries,
            },
            'net_pay': str(preview.net_pay),
            'status': preview.status,
        }
        
        return cls.objects.create(
            employee=preview.employee,
            payroll_record=payroll_record,
            cutoff=preview.cutoff,
            cutoff_start_date=preview.cutoff_start_date,
            cutoff_end_date=preview.cutoff_end_date,
            employee_salary_setting_id=preview.employee_salary_setting_id if preview.employee_salary_setting else None,
            base_salary_monthly=preview.base_salary_monthly,
            salary_per_cutoff=preview.salary_per_cutoff,
            tier_id=preview.tier_id,
            tier_name=preview.tier_name,
            tier_threshold_percentage=preview.tier_threshold_percentage,
            gross_earnings=preview.gross_earnings,
            overtime_hours=preview.overtime_hours,
            overtime_amount=preview.overtime_amount,
            nsd_hours=preview.nsd_hours,
            nsd_amount=preview.nsd_amount,
            holiday_hours=preview.holiday_hours,
            holiday_amount=preview.holiday_amount,
            incentives=preview.incentives,
            leave_days=preview.leave_days,
            leave_deduction=preview.leave_deduction,
            total_additions=preview.total_additions,
            total_de_minimis=preview.total_de_minimis,
            taxable_earnings=preview.taxable_earnings,
            tax_amount=preview.tax_amount,
            other_deductions=preview.other_deductions,
            total_deductions=preview.total_deductions,
            net_pay=preview.net_pay,
            posted_by=user,
            original_preview_id=preview.id,
            complete_snapshot=complete_snapshot,
        )


# =============================================================================
# ADJUSTMENT (For correcting posted payroll)
# =============================================================================
class PayrollAdjustment(models.Model):
    """
    Adjustment record for correcting posted payroll.
    
    Adjustments add/subtract from employee earnings.
    """
    ADJUSTMENT_TYPE = [
        ('ADDITION', 'Addition'),
        ('DEDUCTION', 'Deduction'),
    ]
    
    employee = models.ForeignKey(
        Staff,
        on_delete=models.PROTECT,
        related_name='payroll_adjustments'
    )
    payroll_history = models.ForeignKey(
        PayrollHistory,
        on_delete=models.PROTECT,
        related_name='adjustments',
        help_text="Original payroll record being adjusted"
    )
    adjustment_type = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_TYPE,
        help_text="Type of adjustment"
    )
    description = models.CharField(
        max_length=200,
        help_text="Reason for adjustment"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Adjustment amount (positive)"
    )
    is_taxable = models.BooleanField(
        default=False,
        help_text="Whether this adjustment affects taxable income"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        db_table = 'human_resource_payrolladjustment'
        ordering = ['-created_at']
        verbose_name = 'Payroll Adjustment'
        verbose_name_plural = 'Payroll Adjustments'
    
    def __str__(self):
        sign = '+' if self.adjustment_type == 'ADDITION' else '-'
        return f"{self.employee} - {sign}{self.amount:,.2f} ({self.description})"
    
    @property
    def signed_amount(self):
        """Return amount with appropriate sign"""
        if self.adjustment_type == 'DEDUCTION':
            return -abs(self.amount)
        return abs(self.amount)

