from django.db import models
from django.conf import settings
from datetime import date

class Role(models.Model):
    role_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.role_name


class Department(models.Model):
    department_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.department_name
    
class Position(models.Model):
    position_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.position_name


class Staff(models.Model):

    def save(self, *args, **kwargs):
        if self.start_date:
            today = date.today()
            # Calculate tenure in years, months, and days format
            start = self.start_date
            years = today.year - start.year
            months = today.month - start.month
            days = today.day - start.day
            
            # Adjust for negative days
            if days < 0:
                months -= 1
                # Get days in previous month
                from datetime import timedelta
                first_day_this_month = today.replace(day=1)
                prev_month_end = first_day_this_month - timedelta(days=1)
                days += prev_month_end.day
            
            # Adjust for negative months
            if months < 0:
                years -= 1
                months += 12
            
            # Ensure non-negative values
            if years < 0: years = 0
            if months < 0: months = 0
            if days < 0: days = 0
            
            self.tenure_active = f"{years} years, {months} months, {days} days"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_number})"

    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]

    TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('probationary', 'Probationary'),
        ('contractual', 'Contractual'),
        ('consultant', 'Consultant'),
        ('part_time', 'Part time'),
        ('freelance', 'Freelance'),
        ('defined', 'Defined'),
    ]

    DEPARTMENT_CHOICES = [
        ('top_management', 'Top Management'),
        ('compliance', 'Compliance'),
        ('sales_and_marketing', 'Sales and Marketing'),
        ('sales_operation_processes', 'Sales Operations Processes'),
        ('finance', 'Finance'),
        ('human_resource', 'Human Resource'),
        ('marketing', 'Marketing'),
        ('sales_production', 'Sales Production'),
        ('client_success_management', 'Client Success Management'),
        ('administrative', 'Administrative'),
        ('design_and_technical', 'Design and Technical'),
    ]

    RANK_CHOICES = [
        ('rank_and_file', 'Rank and File'),
        ('supervisory', 'Supervisory'),
        ('managerial', 'Managerial'),
        ('director', 'Director'),
        ('top-management', 'Top Management'),
    ]

    # You asked Job Title dropdown — put example titles; you can extend later
    JOB_TITLE_CHOICES = [
        ('ceo', 'CEO'),
        ('cto', 'CTO'),
        ('hr_manager', 'HR Manager'),
        ('auditor', 'Auditor'),
        ('sales_rep', 'Sales Rep'),
        ('designer', 'Designer'),
    ]


    SHIFT_CHOICES = [
        ('morning', 'Morning Shift'),
        ('afternoon', 'Afternoon Shift'),
        ('night', 'Night Shift'),
        ('flexible', 'Flexible / Others'),
    ]
    SEX_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
    ('prefer_not_to_say', 'Prefer not to say'),]

# Personal Information
    first_name = models.CharField(max_length=100, blank=False, null=False)
    middle_name = models.CharField(max_length=100, blank=False, null=False)
    last_name = models.CharField(max_length=100)
    birthdate = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    sex = models.CharField(max_length=17, choices=SEX_CHOICES, null=True, blank=True)

    # Employment Details
    start_date = models.DateField(null=True, blank=True)
    tenure_active = models.CharField(max_length=50, null=True, blank=True)  # months or years?
    employee_number = models.CharField(max_length=50, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    job_title = models.CharField(max_length=50, choices=JOB_TITLE_CHOICES)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES)

    rank = models.CharField(max_length=20, choices=RANK_CHOICES, null=True, blank=True)
    
    # Join relationship
    #role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True)  # link to role
    #Join Relationship ---> Department
    departmentlink = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)  # link
    #Join Relationship ---> Position
    positionlink = models.ForeignKey(Position, on_delete=models.PROTECT, null=True, blank=True)  # link



    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES)
    

    email_address = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=255, null=True, blank=True)
    emergency_contact_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Address Information
    street_address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Master_Employee'   # optional: set the table name you'd like


# Staff History Tracking
class StaffHistory(models.Model):
    """
    Model to track changes to Staff records.
    Automatically created when Staff is updated via signal.
    """
    
    # Field choices - tracks the fields that can be changed
    FIELD_CHOICES = [
        ('job_title', 'Job Title'),
        ('type', 'Employment Type'),
        ('department', 'Department'),
        ('departmentlink', 'Department Link'),
        ('rank', 'Rank'),
        ('shift', 'Shift'),
        ('positionlink', 'Position'),
        ('role', 'Role'),
        ('status', 'Status'),
        ('first_name', 'First Name'),
        ('middle_name', 'Middle Name'),
        ('last_name', 'Last Name'),
        ('birthdate', 'Birthdate'),
        ('age', 'Age'),
        ('sex', 'Sex'),
        ('start_date', 'Start Date'),
        ('tenure_active', 'Tenure'),
        ('employee_number', 'Employee Number'),
        ('email_address', 'Email Address'),
        ('phone_number', 'Phone Number'),
        ('emergency_contact_name', 'Emergency Contact Name'),
        ('emergency_contact_number', 'Emergency Contact Number'),
        ('street_address', 'Street Address'),
        ('city', 'City'),
        ('province', 'Province'),
        ('postal_code', 'Postal Code'),
        ('country', 'Country'),
    ]

    staff = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='history_records'
    )
    field_name = models.CharField(max_length=50, choices=FIELD_CHOICES)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        'Staff',  # Use Staff model since this project uses session-based auth
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='staff_changes_made'
    )
    change_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Staff History'
        verbose_name_plural = 'Staff History Records'

    def __str__(self):
        return f"{self.staff} - {self.field_name} changed on {self.changed_at}"

    def get_field_display_name(self):
        """Get human-readable field name"""
        for choice in self.FIELD_CHOICES:
            if choice[0] == self.field_name:
                return choice[1]
        return self.field_name


# Django Signals for automatic history tracking
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


@receiver(pre_save, sender=Staff)
def capture_staff_old_values(sender, instance, **kwargs):
    """
    Signal to capture old values BEFORE Staff is saved.
    Stores old values as a temporary attribute on the instance.
    """
    if instance.pk is None:
        # This is a new instance, no old values to track
        instance._is_new = True
        instance._old_values = {}
        return
    
    instance._is_new = False
    
    # Get the existing instance from database
    try:
        old_instance = Staff.objects.get(pk=instance.pk)
    except Staff.DoesNotExist:
        instance._old_values = {}
        return
    
    # Capture all tracked field values
    tracked_fields = [
        'job_title', 'type', 'department', 'departmentlink', 'rank', 'shift', 
        'positionlink', 'role', 'status', 'first_name', 'middle_name',
        'last_name', 'birthdate', 'age', 'sex', 'start_date', 'tenure_active',
        'employee_number',
        'email_address', 'phone_number', 'emergency_contact_name', 
        'emergency_contact_number', 'street_address', 'city', 'province', 
        'postal_code', 'country'
    ]
    
    old_values = {}
    for field_name in tracked_fields:
        old_value = getattr(old_instance, field_name, None)
        # Handle foreign key fields
        if field_name in ['positionlink', 'role', 'departmentlink']:
            old_value = str(old_value) if old_value else None
        old_values[field_name] = old_value
    
    instance._old_values = old_values


@receiver(post_save, sender=Staff)
def track_staff_changes(sender, instance, created, **kwargs):
    """
    Signal to automatically create StaffHistory records when Staff is saved.
    Uses the old values captured in pre_save to compare with new values.
    """
    # Get old values captured in pre_save
    old_values = getattr(instance, '_old_values', {})
    
    # Get the user who made the change (set by the view)
    changed_by = getattr(instance, '_changed_by', None)
    
    if created or not old_values:
        # For new creations, track all fields as new values
        if created:
            tracked_fields = [
                'job_title', 'type', 'department', 'departmentlink', 'rank', 'shift', 
                'positionlink', 'role', 'status', 'first_name', 'middle_name',
                'last_name', 'birthdate', 'age', 'sex', 'start_date', 'tenure_active',
                'employee_number',
                'email_address', 'phone_number', 'emergency_contact_name', 
                'emergency_contact_number', 'street_address', 'city', 'province', 
                'postal_code', 'country'
            ]
            
            for field_name in tracked_fields:
                new_value = getattr(instance, field_name, None)
                # Handle foreign key fields
                if field_name in ['positionlink', 'role', 'departmentlink']:
                    new_value = str(new_value) if new_value else None
                
                new_value_str = str(new_value) if new_value else ''
                
                if new_value_str:  # Only track if there's a value
                    StaffHistory.objects.create(
                        staff=instance,
                        field_name=field_name,
                        old_value=None,
                        new_value=new_value_str,
                        changed_by=changed_by
                    )
        return
    
    # Fields to track
    tracked_fields = [
        'job_title', 'type', 'department', 'departmentlink', 'rank', 'shift', 
        'positionlink', 'role', 'status', 'first_name', 'middle_name',
        'last_name', 'birthdate', 'age', 'sex', 'start_date', 'tenure_active',
        'employee_number',
        'email_address', 'phone_number', 'emergency_contact_name', 
        'emergency_contact_number', 'street_address', 'city', 'province', 
        'postal_code', 'country'
    ]
    
    for field_name in tracked_fields:
        old_value = old_values.get(field_name)
        new_value = getattr(instance, field_name, None)
        
        # Handle foreign key fields
        if field_name in ['positionlink', 'role', 'departmentlink']:
            new_value = str(new_value) if new_value else None
        
        # Compare values
        if str(old_value) != str(new_value):
            # Convert values to string for storage
            old_value_str = str(old_value) if old_value else ''
            new_value_str = str(new_value) if new_value else ''
            
            StaffHistory.objects.create(
                staff=instance,
                field_name=field_name,
                old_value=old_value_str,
                new_value=new_value_str,
                changed_by=changed_by
            )


