from django import forms
from .models import EmployeeShiftRule, LeaveCredit,LeaveRequest
from App.users.models import Staff
from django.forms.widgets import DateInput
from datetime import date   # <-- add this
from django.core.exceptions import ValidationError
from decimal import Decimal

class EmployeeShiftRuleForm(forms.ModelForm):
    class Meta:
        model = EmployeeShiftRule
        fields = ['shift', 'rank', 'clock_in_start', 'clock_out', 'lunch_start', 'lunch_end']

        widgets = {
            'shift': forms.Select(choices=Staff.SHIFT_CHOICES, attrs={'class': 'form-control'}),
            'rank': forms.Select(choices=Staff.RANK_CHOICES, attrs={'class': 'form-control'}),
            'clock_in_start': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'clock_out': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'lunch_start': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'lunch_end': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

class LeaveCreditForm(forms.ModelForm):
    # Read-only field just for display (Rank comes from Staff model)
    employee_rank = forms.CharField(
        label="Rank",
        required=False,
        disabled=True
    )

    class Meta:
        model = LeaveCredit
        fields = ['employee', 'employee_rank', 'leave_type', 'total', 'used', 'year', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional notes / adjustments'
            }),
            'year': forms.NumberInput(attrs={
                'min': 2000,
                'max': 2100
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # if editing → show rank
        if self.instance and self.instance.pk:
            self.fields['employee_rank'].initial = getattr(self.instance.employee, "rank", "")
        else:
            # new record → default year
            self.fields['year'].initial = date.today().year



class LeaveRequestForm(forms.ModelForm):
    position = forms.CharField(label="Position", required=True, widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500'}))
    position_other = forms.CharField(label="Other Position", required=False, widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500'}))
    department = forms.CharField(label="Department", required=True, widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500'}))
    department_other = forms.CharField(label="Other Department", required=False, widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500'}))
    rank = forms.CharField(label="Rank", required=True, widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500'}))
    rank_other = forms.CharField(label="Other Rank", required=False, widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-md px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500'}))
    total_days = forms.DecimalField(
    label="Total Days",
    required=False,
    widget=forms.NumberInput(attrs={'readonly': 'readonly'})
)
    half_day = forms.BooleanField(label="Half Day", required=False)  # New

    date_filed = forms.DateField(widget=DateInput(attrs={'type':'date'}), required=False)

    class Meta:
        model = LeaveRequest
        fields = [
            'employee', 'date_filed', 'leave_type', 'start_date', 'end_date',
            'half_day', 'total_days', 'position', 'department', 'rank', 'purpose',
            'is_paid', 'status', 'disapproval_reason'
        ]
        widgets = {
            'employee': forms.HiddenInput(),
            'start_date': DateInput(attrs={'type':'date'}),
            'end_date': DateInput(attrs={'type':'date'}),
            'purpose': forms.Textarea(attrs={'rows': 4}),
            'disapproval_reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_filed'].initial = self.instance.date_filed or date.today()
        self.fields['total_days'].initial = self.instance.total_days or 0
        
        # For CharField, just set the initial values directly from the instance
        if self.instance.pk:
            # Set initial values from the saved leave request
            if self.instance.position:
                self.fields['position'].initial = self.instance.position
            if self.instance.department:
                self.fields['department'].initial = self.instance.department
            if self.instance.rank:
                self.fields['rank'].initial = self.instance.rank

    def clean(self):
        cleaned_data = super().clean()
        pos = cleaned_data.get('position')
        pos_other = cleaned_data.get('position_other')
        dept = cleaned_data.get('department')
        dept_other = cleaned_data.get('department_other')
        rank = cleaned_data.get('rank')
        rank_other = cleaned_data.get('rank_other')
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')
        total_days = cleaned_data.get('total_days') or Decimal('0.0')

        if pos == 'other' and not pos_other:
            self.add_error('position_other', 'Please specify a position.')
        if dept == 'other' and not dept_other:
            self.add_error('department_other', 'Please specify a department.')
        if rank == 'other' and not rank_other:
            self.add_error('rank_other', 'Please specify a rank.')

        if pos == 'other':
            cleaned_data['position'] = pos_other
        if dept == 'other':
            cleaned_data['department'] = dept_other
        if rank == 'other':
            cleaned_data['rank'] = rank_other

        if start and end and end < start:
            raise ValidationError("End date cannot be earlier than start date.")

        # ---- Leave Credit Check ----
        if employee and leave_type:
            try:
                # Get current year's leave credit
                current_year = date.today().year
                credit = LeaveCredit.objects.filter(
                    employee=employee, 
                    leave_type=leave_type,
                    year=current_year
                ).first()
                
                if credit and total_days > (credit.total - credit.used):
                    raise ValidationError(
                        f"Requested {total_days} days exceed remaining credits ({credit.total - credit.used})."
                    )
            except LeaveCredit.DoesNotExist:
                pass  # No credits for current year is OK - may be using previous year credits

        return cleaned_data



        # REMOVE employee_rank prefill because LeaveRequestForm has no such field
        # if self.instance and self.instance.pk:
        #     self.fields['employee_rank'].initial = self.instance.employee.rank




