"""
Handbook Offense Classification & Compliance Models
=====================================================

This module contains models for:
1. Offense Groups (Rule 1, Rule 2, etc.)
2. Offense Sections (1.1, 1.2, etc.)
3. Offense Classifications (Infraction/Violation descriptions)
4. Remedial Action Matrix (Progressive disciplinary actions)
5. Violation Categories (CAR, Violation, Client Case, Pending, NTE)
6. Violation Types (Client-Related, Discipline-Related, Performance-Related, Pending)
7. Employee Violations (Track violations per employee)
"""

from django.db import models
from django.conf import settings


# =============================================================================
# OFFENSE GROUP - Rule 1, Rule 2, etc.
# =============================================================================

class OffenseGroup(models.Model):
    """
    Group like Rule 1 - violation against conduct and decorum.
    Example: Rule 1 - Violation against conduct and decorum
    """
    group_number = models.CharField(max_length=20, unique=True)  # "Rule 1"
    group_name = models.CharField(max_length=200)  # "Violation against conduct and decorum"
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group_number']
    
    def __str__(self):
        return f"{self.group_number}: {self.group_name}"


# =============================================================================
# OFFENSE SECTION - Section 1.1, 1.2, etc.
# =============================================================================

class OffenseSection(models.Model):
    """
    Section like 1.1 under a specific group.
    Example: 1.1 - General Conduct
    """
    section_number = models.CharField(max_length=20)  # "1.1"
    section_title = models.CharField(max_length=200)
    offense_group = models.ForeignKey(
        OffenseGroup, 
        on_delete=models.CASCADE, 
        related_name='sections'
    )
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['offense_group', 'section_number']
        unique_together = ['offense_group', 'section_number']
    
    def __str__(self):
        return f"{self.section_number}: {self.section_title}"


# =============================================================================
# OFFENSE CLASSIFICATION - Infraction/Violation descriptions
# =============================================================================

class OffenseClassification(models.Model):
    """
    Infraction/Violation - rich text description.
    Example: Tardiness (arriving late to work)
    """
    RANGE_CHOICES = [
        ('A', 'Range A'),
        ('B', 'Range B'),
        ('C', 'Range C'),
        ('D', 'Range D'),
    ]
    
    offense_section = models.ForeignKey(
        OffenseSection, 
        on_delete=models.CASCADE, 
        related_name='classifications'
    )
    offense_description = models.TextField()  # Rich text field for the violation
    default_range = models.CharField(max_length=1, choices=RANGE_CHOICES, default='A')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['offense_section', 'id']
    
    def __str__(self):
        return self.offense_description[:50] + '...' if len(self.offense_description) > 50 else self.offense_description


# =============================================================================
# REMEDIAL ACTION - Progressive disciplinary actions matrix
# =============================================================================

class RemedialAction(models.Model):
    """
    Remedial actions based on Range and Offense Count.
    
    Matrix:
    Range A: 1st=Verbal, 2nd=Written, 3rd=Suspension 1-3 days, 4th=Suspension 4-6 days, 5th=Dismissal
    Range B: 1st=Written, 2nd=Suspension 1-3 days, 3rd=Suspension 4-6 days, 4th=Dismissal
    Range C: 1st=Suspension 1-3 days, 2nd=Suspension 4-6 days, 3rd=Dismissal
    Range D: 1st=Dismissal
    """
    RANGE_CHOICES = [
        ('A', 'Range A'),
        ('B', 'Range B'),
        ('C', 'Range C'),
        ('D', 'Range D'),
    ]
    
    range_code = models.CharField(max_length=1, choices=RANGE_CHOICES)
    offense_count = models.PositiveIntegerField()  # 1, 2, 3, 4, 5
    action = models.CharField(max_length=100)  # "Verbal Warning", "Suspension 1-3 days"
    action_details = models.TextField(blank=True, default='')  # Rich text details
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('range_code', 'offense_count')
        ordering = ['range_code', 'offense_count']
    
    def __str__(self):
        return f"Range {self.range_code} - Offense #{self.offense_count}: {self.action}"


# =============================================================================
# VIOLATION CATEGORY - Category dropdown settings
# =============================================================================

class ViolationCategory(models.Model):
    """
    Category dropdown: CAR, Violation, Client Case, Pending, NTE
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


# =============================================================================
# VIOLATION TYPE - Type dropdown settings
# =============================================================================

class ViolationType(models.Model):
    """
    Type dropdown: Client-Related, Discipline-Related, Performance-Related, Pending
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


# =============================================================================
# EMPLOYEE VIOLATION - Main violation tracking model
# =============================================================================

class EmployeeViolation(models.Model):
    """
    Employee Violation - Parent: Employee Name → Sub-items: Violation Entries
    
    Each violation has:
    - Auto-incrementing incident number (1st, 2nd, 3rd...)
    - Auto-calculated range based on offense count
    - Auto-calculated remedial action based on range + count
    """
    STATUS_CHOICES = [
        ('done', 'Done'),
        ('working', 'Working on it'),
        ('stuck', 'Stuck'),
    ]
    
    DA_STATUS_CHOICES = [
        ('done', 'Done'),
        ('working', 'Working'),
        ('stuck', 'Stuck'),
    ]
    
    DECISION_CHOICES = [
        ('disciplinary_action', 'Disciplinary Action'),
        ('mitigated_offense', 'Mitigated Offense'),
    ]
    
    RANGE_CHOICES = [
        ('A', 'Range A'),
        ('B', 'Range B'),
        ('C', 'Range C'),
        ('D', 'Range D'),
    ]
    
    # Employee relationship (parent item)
    employee = models.ForeignKey(
        'users.Staff', 
        on_delete=models.CASCADE, 
        related_name='violations'
    )
    
    # Incident number (1st, 2nd, 3rd - auto-incremented)
    incident_number = models.PositiveIntegerField(default=1)
    
    # Dropdown fields
    category = models.ForeignKey(
        ViolationCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    violation_type = models.ForeignKey(
        ViolationType, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='working')
    
    # Date fields
    last_updated = models.DateTimeField(auto_now=True)
    date_submitted = models.DateField()
    submitted_by = models.ForeignKey(
        'users.Staff', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='submitted_violations'
    )
    
    # Rich text fields
    type_of_incident = models.TextField()
    hr_note = models.TextField(blank=True, default='')
    
    # Classification from Handbook (dynamic - linked to handbook)
    offense_classification = models.ForeignKey(
        OffenseClassification, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Auto-calculated fields
    offense_count = models.PositiveIntegerField(default=1)
    remedial_action_range = models.CharField(max_length=1, choices=RANGE_CHOICES, default='A')
    remedial_action = models.ForeignKey(
        RemedialAction, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # DA/Classification Status
    da_status = models.CharField(max_length=20, choices=DA_STATUS_CHOICES, default='working')
    
    # Decision
    fully_signed = models.BooleanField(default=False)
    decision = models.CharField(max_length=50, choices=DECISION_CHOICES, blank=True, default='')
    
    # Attachment (future feature - add coming soon handler)
    attachment = models.FileField(
        upload_to='violations/attachments/', 
        null=True, 
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - Violation #{self.incident_number}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate incident number
        if not self.pk:
            # New violation - calculate incident number
            existing_count = EmployeeViolation.objects.filter(
                employee=self.employee
            ).count()
            self.incident_number = existing_count + 1
        
        # Calculate offense_count as total violations for this employee (cumulative across all ranges)
        if not self.pk:
            # New violation: count all existing violations for this employee
            existing_count = EmployeeViolation.objects.filter(
                employee=self.employee
            ).count()
            self.offense_count = existing_count + 1
        elif not self.offense_count or self.offense_count == 0:
            self.offense_count = self.incident_number
        
        # Calculate range based on offense count
        # If offense_classification is set, use its default_range to determine range
        # But offense_count remains as the total cumulative count
        if self.offense_classification and self.offense_classification.default_range:
            self.remedial_action_range = self.offense_classification.default_range
        else:
            if self.offense_count >= 4:
                self.remedial_action_range = 'D'
            elif self.offense_count == 3:
                self.remedial_action_range = 'C'
            elif self.offense_count == 2:
                self.remedial_action_range = 'B'
            else:
                self.remedial_action_range = 'A'
        
        # Get the appropriate remedial action
        self.remedial_action = RemedialAction.objects.filter(
            range_code=self.remedial_action_range,
            offense_count=self.offense_count,
            is_active=True
        ).first()
        
        super().save(*args, **kwargs)
    
    @property
    def incident_label(self):
        """Return ordinal label: 1st, 2nd, 3rd, etc."""
        if self.incident_number == 1:
            return "1st"
        elif self.incident_number == 2:
            return "2nd"
        elif self.incident_number == 3:
            return "3rd"
        else:
            return f"{self.incident_number}th"


# =============================================================================
# SIGNAL TO CREATE DEFAULT DATA
# =============================================================================

def create_default_remedial_actions(sender, **kwargs):
    """
    Signal to create default remedial actions on database migration.
    """
    default_actions = [
        # Range A
        {'range_code': 'A', 'offense_count': 1, 'action': 'Verbal Warning', 'action_details': 'Oral counseling and warning'},
        {'range_code': 'A', 'offense_count': 2, 'action': 'Written Warning', 'action_details': 'Formal written warning in file'},
        {'range_code': 'A', 'offense_count': 3, 'action': 'Suspension 1-3 Days', 'action_details': 'Suspension without pay for 1-3 working days'},
        {'range_code': 'A', 'offense_count': 4, 'action': 'Suspension 4-6 Days', 'action_details': 'Suspension without pay for 4-6 working days'},
        {'range_code': 'A', 'offense_count': 5, 'action': 'Dismissal', 'action_details': 'Termination of employment'},
        
        # Range B
        {'range_code': 'B', 'offense_count': 1, 'action': 'Written Warning', 'action_details': 'Formal written warning in file'},
        {'range_code': 'B', 'offense_count': 2, 'action': 'Suspension 1-3 Days', 'action_details': 'Suspension without pay for 1-3 working days'},
        {'range_code': 'B', 'offense_count': 3, 'action': 'Suspension 4-6 Days', 'action_details': 'Suspension without pay for 4-6 working days'},
        {'range_code': 'B', 'offense_count': 4, 'action': 'Dismissal', 'action_details': 'Termination of employment'},
        
        # Range C
        {'range_code': 'C', 'offense_count': 1, 'action': 'Suspension 1-3 Days', 'action_details': 'Suspension without pay for 1-3 working days'},
        {'range_code': 'C', 'offense_count': 2, 'action': 'Suspension 4-6 Days', 'action_details': 'Suspension without pay for 4-6 working days'},
        {'range_code': 'C', 'offense_count': 3, 'action': 'Dismissal', 'action_details': 'Termination of employment'},
        
        # Range D
        {'range_code': 'D', 'offense_count': 1, 'action': 'Dismissal', 'action_details': 'Immediate termination of employment'},
    ]
    
    for action_data in default_actions:
        RemedialAction.objects.get_or_create(
            range_code=action_data['range_code'],
            offense_count=action_data['offense_count'],
            defaults={
                'action': action_data['action'],
                'action_details': action_data['action_details'],
                'is_active': True
            }
        )


def create_default_violation_categories(sender, **kwargs):
    """
    Signal to create default violation categories.
    """
    default_categories = [
        {'name': 'CAR', 'description': 'Corrective Action Request', 'display_order': 1},
        {'name': 'Violation', 'description': 'General Violation', 'display_order': 2},
        {'name': 'Client Case', 'description': 'Client-related incident', 'display_order': 3},
        {'name': 'Pending', 'description': 'Pending case', 'display_order': 4},
        {'name': 'NTE', 'description': 'Notice to Explain', 'display_order': 5},
    ]
    
    for cat_data in default_categories:
        ViolationCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'display_order': cat_data['display_order'],
                'is_active': True
            }
        )


def create_default_violation_types(sender, **kwargs):
    """
    Signal to create default violation types.
    """
    default_types = [
        {'name': 'Client - Related', 'description': 'Incidents related to clients', 'display_order': 1},
        {'name': 'Discipline - Related', 'description': 'Disciplinary issues', 'display_order': 2},
        {'name': 'Performance - Related', 'description': 'Performance-related issues', 'display_order': 3},
        {'name': 'Pending', 'description': 'Pending classification', 'display_order': 4},
    ]
    
    for type_data in default_types:
        ViolationType.objects.get_or_create(
            name=type_data['name'],
            defaults={
                'description': type_data['description'],
                'display_order': type_data['display_order'],
                'is_active': True
            }
        )


# Connect signals to run after migrations
from django.db.models.signals import post_migrate
post_migrate.connect(create_default_remedial_actions, sender=RemedialAction)
post_migrate.connect(create_default_violation_categories, sender=ViolationCategory)
post_migrate.connect(create_default_violation_types, sender=ViolationType)