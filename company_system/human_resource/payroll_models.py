# human_resource/payroll_models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone

# Import existing Staff model (adjust import path)
from users.models import Staff

# Bank types (small table)
class BankType(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
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

    def __str__(self):
        return f"Payroll {self.month}/{self.year} cutoff {self.cutoff} - {self.created_at:%Y-%m-%d}"
