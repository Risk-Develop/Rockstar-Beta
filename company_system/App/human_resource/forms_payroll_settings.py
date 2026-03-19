from django import forms
from django.db import models
from django.utils import timezone
from .models import (
    TierThresholdSetting, 
    DeMinimisType, 
    DeductionType,
    EmployeeSalarySetting
)
from App.users.models import Staff


class TierThresholdSettingForm(forms.ModelForm):
    """Form for Tier Threshold Setting"""
    
    class Meta:
        model = TierThresholdSetting
        fields = [
            'tier_name', 
            'tier_label',
            'threshold_percentage', 
            'effective_start_date',
            'effective_end_date', 
            'is_active'
        ]
        widgets = {
            'tier_name': forms.Select(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500'
            }),
            'tier_label': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., Entry Level, Senior'
            }),
            'threshold_percentage': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., 85, 88, 92',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'effective_start_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'effective_end_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }
    
    def clean_effective_end_date(self):
        """Convert empty end date to None"""
        value = self.cleaned_data.get('effective_end_date')
        if value == '' or value is None:
            return None
        return value
    
    def clean_threshold_percentage(self):
        """Validate threshold percentage"""
        value = self.cleaned_data['threshold_percentage']
        if value < 0 or value > 100:
            raise forms.ValidationError("Threshold percentage must be between 0 and 100")
        return value


class DeMinimisTypeForm(forms.ModelForm):
    """Form for De Minimis Type"""
    
    class Meta:
        model = DeMinimisType
        fields = [
            'name', 
            'code', 
            'is_taxable', 
            'display_order',
            'effective_start_date',
            'effective_end_date', 
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., Rice Allowance'
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., RICE'
            }),
            'is_taxable': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'min': '0'
            }),
            'effective_start_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'effective_end_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original code for unique validation during edit
        self._original_code = None
        if self.instance and self.instance.pk:
            self._original_code = self.instance.code.upper()
    
    def clean_effective_end_date(self):
        """Convert empty end date to None"""
        value = self.cleaned_data.get('effective_end_date')
        if value == '' or value is None:
            return None
        return value
    
    def clean_code(self):
        """Validate code uniqueness, excluding current instance"""
        code = self.cleaned_data.get('code', '').upper()
        if self._original_code and code == self._original_code:
            return code
        if DeMinimisType.objects.filter(code__iexact=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('De Minimis Type with this Code already exists.')
        return code


class DeductionTypeForm(forms.ModelForm):
    """Form for Deduction Type"""
    
    CATEGORY_CHOICES = [
        ('ATTENDANCE', 'Attendance deductions'),
        ('GOVERNMENT', 'Government deductions'),
        ('LOAN', 'Loan/Cash Advance'),
        ('INSURANCE', 'Insurance'),
        ('OTHER', 'Other deductions'),
    ]
    
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, widget=forms.Select(attrs={
        'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500'
    }))
    
    class Meta:
        model = DeductionType
        fields = [
            'name', 
            'code', 
            'category',
            'is_government', 
            'display_order',
            'effective_start_date',
            'effective_end_date', 
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., Late'
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., LATE'
            }),
            'is_government': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'min': '0'
            }),
            'effective_start_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'effective_end_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original code for unique validation during edit
        self._original_code = None
        if self.instance and self.instance.pk:
            self._original_code = self.instance.code.upper()
    
    def clean_effective_end_date(self):
        """Convert empty end date to None"""
        value = self.cleaned_data.get('effective_end_date')
        if value == '' or value is None:
            return None
        return value
    
    def clean_code(self):
        """Validate code uniqueness, excluding current instance"""
        code = self.cleaned_data.get('code', '').upper()
        if self._original_code and code == self._original_code:
            return code
        if DeductionType.objects.filter(code__iexact=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Deduction Type with this Code already exists.')
        return code
    
    def clean_category(self):
        """Ensure category is uppercase"""
        category = self.cleaned_data['category']
        return category.upper()


class EmployeeSalarySettingForm(forms.ModelForm):
    """Form for Employee Salary Setting"""
    
    class Meta:
        model = EmployeeSalarySetting
        fields = [
            'employee',
            'base_salary_monthly',
            'work_schedule',
            'tier',
            'effective_start_date',
            'effective_end_date',
            'is_active',
            'notes'
        ]
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500'
            }),
            'base_salary_monthly': forms.NumberInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., 50000.00',
                'step': '0.01',
                'min': '0'
            }),
            'work_schedule': forms.Select(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500'
            }),
            'tier': forms.Select(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500'
            }),
            'effective_start_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'effective_end_date': forms.DateInput(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'e.g., Initial setup, Salary increase approved by management, Promotion to Senior level...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make salary_per_cutoff readonly (it's computed)
        self.fields['base_salary_monthly'].help_text = 'Monthly salary. Cutoff salary will be computed automatically (monthly / 2).'
        
        # Filter tier dropdown to show only active tiers
        self.fields['tier'].queryset = TierThresholdSetting.objects.filter(
            is_active=True
        ).filter(
            models.Q(effective_end_date__isnull=True) | models.Q(effective_end_date__gte=timezone.now().date())
        ).order_by('tier_name')
        
        # Make tier field optional and add placeholder
        self.fields['tier'].empty_label = "-- Select Active Tier (Optional) --"
    
    def clean_effective_end_date(self):
        """Convert empty end date to None - CRITICAL for model validation"""
        value = self.cleaned_data.get('effective_end_date')
        if value == '' or value is None:
            return None
        return value
    
    def clean_base_salary_monthly(self):
        """Validate base salary"""
        value = self.cleaned_data['base_salary_monthly']
        if value < 0:
            raise forms.ValidationError("Base salary cannot be negative")
        return value

