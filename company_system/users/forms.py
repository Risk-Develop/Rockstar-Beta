from django import forms
from .models import Staff
from .models import Role, Department,Position
from django.core.exceptions import ValidationError

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = [
            'first_name', 'middle_name', 'last_name',
            'status', 'positionlink', 'type', 'departmentlink', 'shift',

            # Newly added fields:
            'sss_number', 'pagibig_number', 'philhealth_number',
            'email_address', 'phone_number',
            'emergency_contact_name', 'emergency_contact_number',
            'start_date', 'tenure_active',
            'employee_number', 'birthdate', 'age', 'sex','rank',
        ]
        def clean(self):
            if Staff.objects.exclude(id=self.id).filter(employee_number=self.employee_number).exists():
                raise ValidationError({"employee_number": "Employee Number must be unique."})

        def save(self, *args, **kwargs):
            self.full_clean()  # calls clean() to enforce validation
            super().save(*args, **kwargs)
        labels = {
            'shift': 'Shift Set-Up',
            'departmentlink': 'Employee Department',
            'positionlink': 'Job Title',
            'type': 'Employment Type',
            'status': 'Current Status',
            'sss_number': 'SSS Number',
            'pagibig_number': 'PAG-IBIG Number',
            'philhealth_number': 'PhilHealth Number',
            'email_address': 'Email Address',
            'phone_number': 'Phone Number',
            'emergency_contact_name': 'Emergency Contact Name',
            'emergency_contact_number': 'Emergency Contact Number',
            'start_date': 'Start Date',
            'tenure_active': 'Tenure',
            'employee_number': 'Employee Number',
            'birthdate': 'Birthdate',
            'age': 'Age',
            'sex': 'Sex',
            'rank': 'Rank',
        }

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full', 'placeholder': 'Enter first name'}),
            'middle_name': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full', 'placeholder': 'Enter middle name'}),
            'last_name': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full', 'placeholder': 'Enter last name'}),

            'status': forms.Select(attrs={'class': 'input border rounded px-2 py-1 w-full select'}),
            'positionlink': forms.Select(attrs={'class': 'input border rounded px-2 py-1 w-full select'}),
            'type': forms.Select(attrs={'class': 'input border rounded px-2 py-1 w-full select'}),
            'departmentlink': forms.Select(attrs={'class': 'input border rounded px-2 py-1 w-full select'}),
            'shift': forms.Select(attrs={'class': 'input border rounded px-2 py-1 w-full select'}),
            'rank': forms.Select(attrs={'class': 'input border rounded px-2 py-1 w-full select'}),

            # New fields widgets
            'sss_number': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full'}),
            'pagibig_number': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full'}),
            'philhealth_number': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full'}),

            'email_address': forms.EmailInput(attrs={'class': 'input border rounded px-2 py-1 w-full'}),
            'phone_number': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full'}),
            'emergency_contact_number': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full'}),

            'start_date': forms.DateInput(attrs={'class': 'input border rounded px-2 py-1 w-full', 'type': 'date', 'id': 'id_start_date'}),
            'tenure_active': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full','readonly': 'readonly','id': 'id_tenure_active'}),

            'employee_number': forms.TextInput(attrs={'class': 'input border rounded px-2 py-1 w-full', 'readonly': 'readonly', 'id': 'id_employee_number'}),
            'birthdate': forms.DateInput(attrs={'class': 'input border rounded px-2 py-1 w-full', 'type': 'date', 'id': 'id_birthdate'}),
            'age': forms.NumberInput(attrs={'class': 'input border rounded px-2 py-1 w-full', 'readonly': 'readonly', 'id': 'id_age'}),
            'sex': forms.Select(attrs={'class': 'input border rounded px-2 py-1 w-full select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamic queryset for departmentlink (only active)
        self.fields['departmentlink'].queryset = Department.objects.filter(is_active=True)

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['role_name', 'description', 'is_active']
        widgets = {
            'role_name': forms.TextInput(attrs={'class': 'input border rounded p-2 w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea border rounded p-2 w-full', 'rows':3}),
            'is_active': forms.CheckboxInput(attrs={'class':'checkbox'}),
        }


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['department_name', 'description', 'is_active']
        widgets = {
            'department_name': forms.TextInput(attrs={'class': 'input border rounded p-2 w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea border rounded p-2 w-full', 'rows':3}),
            'is_active': forms.CheckboxInput(attrs={'class':'checkbox'}),
        }


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['position_name', 'description', 'is_active']
        widgets = {
            'position_name': forms.TextInput(attrs={'class': 'input border rounded p-2 w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea border rounded p-2 w-full', 'rows':3}),
            'is_active': forms.CheckboxInput(attrs={'class':'checkbox'}),
        }