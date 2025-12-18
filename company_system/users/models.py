from django.db import models
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
            self.tenure_active = (today - self.start_date).days // 30  # months
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
    
    # Government Numbers
    sss_number = models.CharField(max_length=20, null=True, blank=True)
    pagibig_number = models.CharField(max_length=20, null=True, blank=True)
    philhealth_number = models.CharField(max_length=20, null=True, blank=True)

    # Contact Information
    email_address = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=255, null=True, blank=True)
    emergency_contact_number = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Master_Employee'   # optional: set the table name you'd like

