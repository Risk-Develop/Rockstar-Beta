
from django.db import models
from users.models import Staff  # import your existing Master_Employee
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, time, timedelta
from .payroll_models import *    

#=========================================
#
# SHIFT 
#
#=========================================
    
#class Shift(models.Model):
#    name = models.CharField(max_length=50)  # e.g., Night, Morning, Afternoon
#    start_time = models.TimeField()
#    end_time = models.TimeField()
#    grace_period = models.IntegerField(default=10)  # minutes allowed late
#   is_overnight = models.BooleanField(default=False)

#    def __str__(self):
#        return self.name
    
#=========================================
#
# EmployeeProfileSettings
#
#=========================================

# Employee Profile Settings
class EmployeeProfileSettings(models.Model):
    employee = models.OneToOneField(Staff, on_delete=models.CASCADE)
    rank = models.CharField(max_length=20, choices=Staff.RANK_CHOICES, null=True, blank=True)
    shift = models.CharField(max_length=20, choices=Staff.SHIFT_CHOICES, null=True, blank=True)

    initial_vl = models.IntegerField(default=6)
    initial_sl = models.IntegerField(default=6)
    current_vl = models.IntegerField(default=6)
    current_sl = models.IntegerField(default=6)

    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} Profile"
    

#=========================================
#
# Attendance
#
#=========================================


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ]

    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='absent')

    # --- Suggested Additional Fields ---
    hours_worked = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        help_text="Computed hours worked per shift"
    )
    late_minutes = models.PositiveIntegerField(default=0, help_text="Minutes late beyond grace period")
    ot_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        help_text="Overtime hours"
    )
    nsd_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        help_text="Night Shift Differential hours"
    )

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date}"
    
#=========================================
#
# Shift Rule
#
#=========================================
class EmployeeShiftRule(models.Model):
    SHIFT_CHOICES = Staff.SHIFT_CHOICES
    RANK_CHOICES = Staff.RANK_CHOICES

    shift = models.CharField(max_length=50, choices=SHIFT_CHOICES)
    rank = models.CharField(max_length=50, choices=RANK_CHOICES)
    clock_in_start = models.TimeField(null=True, blank=True)
    clock_in_end = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)

 # --- Suggested Additional Fields ---
    total_hours = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('8.00'),
        help_text="Expected total hours per shift"
    )
    nsd_applicable = models.BooleanField(default=False, help_text="Night Shift Differential applicable?")
    late_grace_period = models.PositiveIntegerField(default=0, help_text="Grace period in minutes")
    flexible = models.BooleanField(default=False, help_text="Flexible schedule?")




    class Meta:
        db_table = 'human_resource_employeeshiftrule'
        unique_together = ('shift', 'rank')
        ordering = ['shift', 'rank']

    def __str__(self):
        return f"{self.get_shift_display()} - {self.get_rank_display()}"
    

#=========================================
#
# Leave Credit
#
#=========================================


LEAVE_TYPE_CHOICES = [
    ('vl', 'Vacation Leave'),
    ('sl', 'Sick Leave'),
]

class LeaveCredit(models.Model):
    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=2, choices=LEAVE_TYPE_CHOICES)
    total = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    year = models.PositiveIntegerField(default=date.today().year)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'leave_type', 'year')

    @property
    def remaining(self):
        return self.total - self.used

    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()} ({self.year})"

#=========================================
#
# Leave Request
#
#=========================================


LEAVE_TYPE_CHOICES = [
    ('vl', 'Vacation Leave'),
    ('sl', 'Sick Leave'),
]

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('disapproved', 'Disapproved'),
    ]

    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date_filed = models.DateField(null=True, blank=True)
    position = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)
    leave_type = models.CharField(max_length=2, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    half_day = models.BooleanField(default=False)  # New: checkbox support
    purpose = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    is_paid = models.BooleanField(default=False)
    disapproval_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days + 1
            self.total_days = delta
            if self.half_day:
                self.total_days -= 0.5

        if self.employee:
            if not self.position:
                self.position = getattr(self.employee, 'job_title', '') or ''
            if not self.department:
                self.department = getattr(self.employee, 'department', '') or ''

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"
