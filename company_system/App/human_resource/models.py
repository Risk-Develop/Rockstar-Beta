from django.db import models
from App.users.models import Staff
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, time, timedelta
from .payroll_models import *
from .payroll_settings_models import *


# ─────────────────────────────────────────────────────────────────────────────
# EmployeeProfileSettings
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeProfileSettings(models.Model):
    employee   = models.OneToOneField(Staff, on_delete=models.CASCADE)
    rank       = models.CharField(max_length=20, choices=Staff.RANK_CHOICES, null=True, blank=True)
    shift      = models.CharField(max_length=20, choices=Staff.SHIFT_CHOICES, null=True, blank=True)

    initial_vl = models.IntegerField(default=6)
    initial_sl = models.IntegerField(default=6)
    current_vl = models.IntegerField(default=6)
    current_sl = models.IntegerField(default=6)

    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} Profile"


# ─────────────────────────────────────────────────────────────────────────────
# Attendance
# ─────────────────────────────────────────────────────────────────────────────

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present',            'Present'),
        ('late',               'Late'),
        ('absent',             'Absent'),
        ('on_leave',           'On Leave'),
        ('early_leave',        'Early Leave'),
        ('failed_to_clock_out','Failed to Clock Out'),
        ('missing_lunch',      'Missing Lunch'),
    ]

    employee = models.ForeignKey(Staff, on_delete=models.CASCADE)

    # ── CHANGED: was auto_now_add=True (ignored passed values).
    #    Now default=date.today so leave rows can be stored for any date.
    date = models.DateField(default=date.today)

    clock_in  = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)

    # Multi-select status field (comma-separated values)
    statuses = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text=(
            "Multiple statuses separated by comma: "
            "present,late,absent,on_leave,early_leave,"
            "failed_to_clock_out,missing_lunch"
        ),
    )

    # Legacy single status field (kept for backward compatibility)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='absent')

    # Lunch fields
    lunch_in  = models.TimeField(null=True, blank=True, help_text="Time employee started lunch break")
    lunch_out = models.TimeField(null=True, blank=True, help_text="Time employee ended lunch break")

    # Calculated fields
    hours_worked = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        help_text="Computed hours worked per shift",
    )
    late_minutes      = models.PositiveIntegerField(default=0, help_text="Minutes late beyond clock in start")
    overlunch_minutes = models.PositiveIntegerField(default=0, help_text="Extra minutes beyond standard 60 min lunch")
    overlunch_validated = models.BooleanField(default=False, help_text="HR validated overlunch (excluded from deduction)")
    deduction_minutes = models.PositiveIntegerField(default=0, help_text="Total deduction: late + overlunch if not validated")
    ot_hours  = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Overtime hours")
    nsd_hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Night Shift Differential hours")

    note = models.TextField(blank=True, default='', help_text="HR remarks/adjustment notes")

    # ── NEW: ForeignKey to LeaveRequest so on_leave rows can be found/removed
    #    precisely when a leave is un-approved.
    #    Requires: python manage.py makemigrations human_resource && migrate
    leave_request = models.ForeignKey(
        'LeaveRequest',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='attendance_records',
        help_text="Set when this row was auto-created from an approved leave request",
    )

    class Meta:
        unique_together = ('employee', 'date')
        ordering        = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date}"

    # ── Multi-select status helper methods ───────────────────────────────────

    def get_statuses_list(self):
        """Return list of statuses from the statuses field."""
        if not self.statuses:
            return []
        return [s.strip() for s in self.statuses.split(',') if s.strip()]

    def set_statuses(self, statuses_list):
        """Set statuses from a list."""
        self.statuses = ','.join(statuses_list)

    def add_status(self, status):
        """Add a status to the list (no duplicates)."""
        current = self.get_statuses_list()
        if status not in current:
            current.append(status)
            self.set_statuses(current)

    def remove_status(self, status):
        """Remove a status from the list."""
        current = self.get_statuses_list()
        if status in current:
            current.remove(status)
            self.set_statuses(current)

    def has_status(self, status):
        """Check if a specific status exists."""
        return status in self.get_statuses_list()

    def get_status_display_list(self):
        """Return list of human-readable status names."""
        status_dict = dict(self.STATUS_CHOICES)
        return [status_dict.get(s, s.title()) for s in self.get_statuses_list()]

    def get_primary_status(self):
        """Return the primary status (first in statuses, or legacy status field)."""
        statuses = self.get_statuses_list()
        if statuses:
            return statuses[0]
        return self.status


# ─────────────────────────────────────────────────────────────────────────────
# EmployeeShiftRule
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeShiftRule(models.Model):
    SHIFT_CHOICES = Staff.SHIFT_CHOICES
    RANK_CHOICES  = Staff.RANK_CHOICES

    shift = models.CharField(max_length=50, choices=SHIFT_CHOICES)
    rank  = models.CharField(max_length=50, choices=RANK_CHOICES)

    clock_in_start = models.TimeField(null=True, blank=True)
    clock_out      = models.TimeField(null=True, blank=True)

    # Lunch fields
    lunch_start    = models.TimeField(null=True, blank=True, help_text="Standard lunch start time")
    lunch_end      = models.TimeField(null=True, blank=True, help_text="Standard lunch end time (default 60 min from lunch_start)")
    lunch_required = models.BooleanField(default=True, help_text="Whether lunch clock in/out is required for this shift")



    #The default is 60 minutes, but it can be adjusted per shift rule if needed.

    clock_out_grace_period = models.PositiveIntegerField(
        default=60,
        help_text="Grace period in minutes after clock_out time before marking failed_to_clock_out",
    )
    absent_grace_period = models.PositiveIntegerField(
        default=60,
        help_text="Grace period in minutes after shift end before marking absent (if no clock in)",
    )
    total_hours        = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('8.00'), help_text="Expected total hours per shift")
    nsd_applicable     = models.BooleanField(default=False, help_text="Night Shift Differential applicable?")
    late_grace_period  = models.PositiveIntegerField(default=0, help_text="Grace period in minutes")
    flexible           = models.BooleanField(default=False, help_text="Flexible schedule?")

    class Meta:
        db_table       = 'human_resource_employeeshiftrule'
        unique_together = ('shift', 'rank')
        ordering        = ['shift', 'rank']

    def __str__(self):
        return f"{self.get_shift_display()} - {self.get_rank_display()}"


# ─────────────────────────────────────────────────────────────────────────────
# Leave Credit
# ─────────────────────────────────────────────────────────────────────────────

LEAVE_TYPE_CHOICES = [
    ('vl', 'Vacation Leave'),
    ('sl', 'Sick Leave'),
]


class LeaveCredit(models.Model):
    employee   = models.ForeignKey(Staff, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=2, choices=LEAVE_TYPE_CHOICES)
    total      = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used       = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    year       = models.PositiveIntegerField(default=date.today().year)
    notes      = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'leave_type', 'year')

    @property
    def remaining(self):
        return self.total - self.used

    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()} ({self.year})"


# ─────────────────────────────────────────────────────────────────────────────
# Leave Request
# ─────────────────────────────────────────────────────────────────────────────

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('approved',    'Approved'),
        ('disapproved', 'Disapproved'),
    ]

    employee           = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date_filed         = models.DateField(null=True, blank=True)
    position           = models.CharField(max_length=150, blank=True)
    department         = models.CharField(max_length=150, blank=True)
    rank               = models.CharField(max_length=50, blank=True)
    leave_type         = models.CharField(max_length=2, choices=LEAVE_TYPE_CHOICES)
    start_date         = models.DateField()
    end_date           = models.DateField()
    total_days         = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    half_day           = models.BooleanField(default=False)
    reason             = models.TextField(blank=True, null=True)   # ← ADDED (template uses this)
    purpose            = models.TextField(blank=True, null=True)
    status             = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    is_paid            = models.BooleanField(default=False)
    disapproval_reason = models.TextField(blank=True, null=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days + 1
            self.total_days = delta
            if self.half_day:
                self.total_days -= Decimal('0.5')

        if self.employee:
            if not self.position:
                self.position = getattr(self.employee, 'job_title', '') or ''
            if not self.department:
                self.department = getattr(self.employee, 'department', '') or ''
            if not self.rank:
                self.rank = getattr(self.employee, 'rank', '') or ''

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"


# ═══════════════════════════════════════════════════════════════════════════════
# ENPS (Employee Net Promoter Score) Survey
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib


class ENPSSurvey(models.Model):
    """ENPS Survey Session - Create a new survey to collect employee feedback"""
    
    name = models.CharField(max_length=255, help_text="Survey name (e.g., Q1 2024 Survey)")
    description = models.TextField(blank=True, help_text="Survey description")
    start_date = models.DateField(help_text="Survey start date")
    end_date = models.DateField(null=True, blank=True, help_text="Survey end date (optional)")
    is_active = models.BooleanField(default=True, help_text="Is survey currently active?")
    allow_anonymous = models.BooleanField(default=False, help_text="Allow anonymous submissions?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ENPS Survey'
        verbose_name_plural = 'ENPS Surveys'
    
    def __str__(self):
        return self.name
    
    @property
    def is_open(self):
        """Check if survey is currently open for responses"""
        today = date.today()
        if not self.is_active:
            return False
        if self.end_date:
            return self.start_date <= today <= self.end_date
        return today >= self.start_date
    
    @property
    def response_count(self):
        """Total number of responses"""
        return self.responses.count()
    
    @property
    def enps_score(self):
        """Calculate eNPS score: %Promoters - %Detractors"""
        responses = self.responses.all()
        total = responses.count()
        if total == 0:
            return 0
        
        promoters = responses.filter(score__gte=9).count()
        detractors = responses.filter(score__lte=6).count()
        
        return round(((promoters - detractors) / total) * 100, 1)


class ENPSSurveyQuestion(models.Model):
    """Survey Question - Individual questions within a survey"""
    
    QUESTION_TYPE_CHOICES = [
        ('nps', 'NPS Score (0-10)'),
        ('rating_5', 'Rating (1-5 Stars)'),
        ('rating_3', 'Rating (1-3)'),
        ('text', 'Text Answer'),
        ('yes_no', 'Yes/No'),
    ]
    
    survey = models.ForeignKey(
        ENPSSurvey, 
        on_delete=models.CASCADE, 
        related_name='questions'
    )
    
    question_text = models.TextField(help_text="The question to ask")
    question_type = models.CharField(
        max_length=20, 
        choices=QUESTION_TYPE_CHOICES,
        default='nps',
        help_text="Type of question"
    )
    
    is_required = models.BooleanField(
        default=True,
        help_text="Must this question be answered?"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order of question in survey"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Survey Question'
        verbose_name_plural = 'Survey Questions'
    
    def __str__(self):
        return f"{self.order + 1}. {self.question_text[:50]}..."


class ENPSResponse(models.Model):
    """
    ENPS Response - Stores individual employee feedback
    
    Key Features:
    - Anonymous but traceable (hash-based identification)
    - Employee number and email are hashed for privacy
    - HR can only see department-level analytics
    """
    
    CATEGORY_CHOICES = [
        ('promoter', 'Promoter (9-10)'),
        ('passive', 'Passive (7-8)'),
        ('detractor', 'Detractor (0-6)'),
    ]
    
    EMOJI_CHOICES = [
        ('😍', 'Love it!'),
        ('🙂', 'Good'),
        ('😐', 'Neutral'),
        ('😞', 'Disappointed'),
        ('💢', 'Angry'),
    ]
    
    # Survey Reference
    survey = models.ForeignKey(
        ENPSSurvey, 
        on_delete=models.CASCADE, 
        related_name='responses'
    )
    
    # Core NPS Score (0-10)
    score = models.IntegerField(
        choices=[(i, str(i)) for i in range(11)],
        help_text="NPS Score from 0-10"
    )
    
    # Category (calculated automatically)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Emoji Feedback
    emoji_feedback = models.CharField(max_length=10, choices=EMOJI_CHOICES)
    
    # Text Feedback (Optional)
    feedback_comment = models.TextField(blank=True, help_text="Optional detailed feedback")
    
    # Privacy Fields - Hash-based identification (not plain text)
    # These allow tracking without revealing identity
    employee_number_hash = models.CharField(
        max_length=64, 
        null=True, 
        blank=True,
        help_text="SHA256 hash of employee number for tracking"
    )
    email_hash = models.CharField(
        max_length=64, 
        null=True, 
        blank=True,
        help_text="SHA256 hash of email for tracking"
    )
    
    # Anonymous flag
    is_anonymous = models.BooleanField(
        default=False,
        help_text="If true, response is fully anonymous (no tracking)"
    )
    
    # Employee Info - stored but can be hidden from HR view
    employee = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='enps_responses'
    )
    
    # Denormalized department for easier analytics (protects privacy)
    department = models.CharField(max_length=50, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ENPS Response'
        verbose_name_plural = 'ENPS Responses'
    
    def __str__(self):
        return f"Survey: {self.survey.name} - Score: {self.score}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate category based on score
        if self.score >= 9:
            self.category = 'promoter'
        elif self.score >= 7:
            self.category = 'passive'
        else:
            self.category = 'detractor'
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def hash_value(value):
        """Create SHA256 hash of a value"""
        if not value:
            return None
        return hashlib.sha256(str(value).encode()).hexdigest()
    
    def get_category_display_class(self):
        """Get CSS class for category badge"""
        return {
            'promoter': 'bg-green-100 text-green-800',
            'passive': 'bg-yellow-100 text-yellow-800',
            'detractor': 'bg-red-100 text-red-800',
        }.get(self.category, 'bg-gray-100 text-gray-800')


class ENPSQuestionResponse(models.Model):
    """Individual response to a specific survey question"""
    
    response = models.ForeignKey(
        ENPSResponse,
        on_delete=models.CASCADE,
        related_name='question_responses'
    )
    
    question = models.ForeignKey(
        ENPSSurveyQuestion,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    
    # Answer based on question type
    score_value = models.IntegerField(
        null=True,
        blank=True,
        help_text="Score for NPS (0-10), rating questions"
    )
    
    text_value = models.TextField(
        blank=True,
        help_text="Text answer for text questions"
    )
    
    boolean_value = models.BooleanField(
        null=True,
        blank=True,
        help_text="Yes/No answer"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Question Response'
        verbose_name_plural = 'Question Responses'
    
    def __str__(self):
        return f"Response to: {self.question.question_text[:30]}..."


class ENPSDepartmentAnalytics(models.Model):
    """Cached department-level analytics for faster dashboard loading"""
    
    survey = models.ForeignKey(ENPSSurvey, on_delete=models.CASCADE, related_name='department_analytics')
    department = models.CharField(max_length=50)
    
    # Analytics fields
    total_responses = models.IntegerField(default=0)
    enps_score = models.FloatField(default=0)
    promoters_count = models.IntegerField(default=0)
    passives_count = models.IntegerField(default=0)
    detractors_count = models.IntegerField(default=0)
    average_score = models.FloatField(default=0)
    
    # Emoji distribution (JSON-like storage)
    emoji_distribution = models.JSONField(default=dict)
    
    # Monthly trend data (JSON)
    monthly_trend = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('survey', 'department')
        verbose_name = 'ENPS Department Analytics'
        verbose_name_plural = 'ENPS Department Analytics'
    
    def __str__(self):
        return f"{self.survey.name} - {self.department}"
