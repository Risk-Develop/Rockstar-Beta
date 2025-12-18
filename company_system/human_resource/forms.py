from django import forms
from .models import EmployeeShiftRule, LeaveCredit,LeaveRequest
from users.models import Staff
from django.forms.widgets import DateInput
from datetime import date   # <-- add this
from django.core.exceptions import ValidationError
from decimal import Decimal

class EmployeeShiftRuleForm(forms.ModelForm):
    class Meta:
        model = EmployeeShiftRule
        fields = ['shift', 'rank', 'clock_in_start', 'clock_in_end', 'clock_out']

        widgets = {
            'shift': forms.Select(choices=Staff.SHIFT_CHOICES, attrs={'class': 'form-control'}),
            'rank': forms.Select(choices=Staff.RANK_CHOICES, attrs={'class': 'form-control'}),
            'clock_in_start': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'clock_in_end': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'clock_out': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
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
    position = forms.ChoiceField(label="Position", required=True)
    position_other = forms.CharField(label="Other Position", required=False)
    department = forms.ChoiceField(label="Department", required=True)
    department_other = forms.CharField(label="Other Department", required=False)
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
            'half_day', 'total_days', 'position', 'department', 'purpose',
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

        positions = list(Staff.objects.order_by('positionlink__position_name').values_list('positionlink__id','positionlink__position_name').distinct())
        depts = list(Staff.objects.order_by('departmentlink__department_name').values_list('departmentlink__id','departmentlink__department_name').distinct())
        self.fields['position'].choices = [('', 'Select Position')] + positions + [('other', 'Other')]
        self.fields['department'].choices = [('', 'Select Department')] + depts + [('other', 'Other')]

        if self.instance.pk:
            self.fields['position'].initial = self.instance.position if self.instance.position in dict(positions) else 'other'
            self.fields['position_other'].initial = '' if self.instance.position in dict(positions) else self.instance.position
            self.fields['department'].initial = self.instance.department if self.instance.department in dict(depts) else 'other'
            self.fields['department_other'].initial = '' if self.instance.department in dict(depts) else self.instance.department

    def clean(self):
        cleaned_data = super().clean()
        pos = cleaned_data.get('position')
        pos_other = cleaned_data.get('position_other')
        dept = cleaned_data.get('department')
        dept_other = cleaned_data.get('department_other')
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')
        total_days = cleaned_data.get('total_days') or Decimal('0.0')

        if pos == 'other' and not pos_other:
            self.add_error('position_other', 'Please specify a position.')
        if dept == 'other' and not dept_other:
            self.add_error('department_other', 'Please specify a department.')

        if pos == 'other':
            cleaned_data['position'] = pos_other
        if dept == 'other':
            cleaned_data['department'] = dept_other

        if start and end and end < start:
            raise ValidationError("End date cannot be earlier than start date.")

        # ---- Leave Credit Check ----
        if employee and leave_type:
            try:
                credit = LeaveCredit.objects.get(employee=employee, leave_type=leave_type)
                if total_days > (credit.total - credit.used):
                    raise ValidationError(
                        f"Requested {total_days} days exceed remaining credits ({credit.total - credit.used})."
                    )
            except LeaveCredit.DoesNotExist:
                raise ValidationError("No leave credits available for this leave type.")

        return cleaned_data



        # REMOVE employee_rank prefill because LeaveRequestForm has no such field
        # if self.instance and self.instance.pk:
        #     self.fields['employee_rank'].initial = self.instance.employee.rank



