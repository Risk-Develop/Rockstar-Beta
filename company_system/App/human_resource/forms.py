from django import forms
from .models import EmployeeShiftRule, LeaveCredit, LeaveRequest, ExitInterview
from App.users.models import Staff
from django.forms.widgets import DateInput
from datetime import date
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
        if self.instance and self.instance.pk:
            self.fields['employee_rank'].initial = getattr(self.instance.employee, "rank", "")
        else:
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
    half_day = forms.BooleanField(label="Half Day", required=False)

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

        if self.instance.pk:
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
                pass

        return cleaned_data


class ExitInterviewForm(forms.ModelForm):
    """Form for creating and editing Exit Interview records."""

    employee_name = forms.CharField(
        label="Employee Name",
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400', 'readonly': 'readonly'})
    )
    employee_id = forms.CharField(
        label="Employee ID",
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400', 'readonly': 'readonly'})
    )

    primary_driver = forms.CharField(
        label="Primary Reason for Resignation",
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )
    improvement_areas = forms.CharField(
        label="Areas for Company Improvement",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )
    categorization = forms.CharField(
        label="Reason Category",
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )
    additional_feedback = forms.CharField(
        label="Additional Feedback",
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )

    class Meta:
        model = ExitInterview
        fields = [
            'employee',
            'resignation_status',
            'date_filed',
            'resignation_letter',
            'resignation_letter_text',
            'desired_last_day',
            'approved_last_day',
            'rendering_30day_status',
            'exit_interview_status',
            'knowledge_transfer_status',
            'asset_return_status',
            'clearance_status',
            'quitclaim_status',
            'final_pay_status',
            'nda_signed',
            'nca_signed',
            'other_attachments',
            'qualitative_data',
            'interview_notes',
        ]
        widgets = {
            'employee': forms.HiddenInput(),
            'date_filed': DateInput(attrs={'type': 'date', 'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'desired_last_day': DateInput(attrs={'type': 'date', 'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'approved_last_day': DateInput(attrs={'type': 'date', 'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'resignation_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'rendering_30day_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'exit_interview_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'knowledge_transfer_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'asset_return_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'clearance_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'quitclaim_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'final_pay_status': forms.Select(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'resignation_letter': forms.FileInput(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'other_attachments': forms.FileInput(attrs={'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'nda_signed': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 dark:border-gray-600 text-blue-600 shadow-sm focus:ring-blue-500'}),
            'nca_signed': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 dark:border-gray-600 text-blue-600 shadow-sm focus:ring-blue-500'}),
            'interview_notes': forms.Textarea(attrs={'rows': 4, 'class': 'w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['resignation_status'].choices = ExitInterview.RESIGNATION_STATUS_CHOICES
        self.fields['rendering_30day_status'].choices = ExitInterview.RENDERING_30DAY_STATUS_CHOICES
        self.fields['exit_interview_status'].choices = ExitInterview.EXIT_INTERVIEW_STATUS_CHOICES
        self.fields['knowledge_transfer_status'].choices = ExitInterview.KNOWLEDGE_TRANSFER_STATUS_CHOICES
        self.fields['asset_return_status'].choices = ExitInterview.ASSET_RETURN_STATUS_CHOICES
        self.fields['clearance_status'].choices = ExitInterview.CLEARANCE_STATUS_CHOICES
        self.fields['quitclaim_status'].choices = ExitInterview.QUITCLAIM_STATUS_CHOICES
        self.fields['final_pay_status'].choices = ExitInterview.FINAL_PAY_STATUS_CHOICES

        if self.instance and self.instance.pk:
            self.fields['employee_name'].initial = self.instance.get_full_name()
            self.fields['employee_id'].initial = self.instance.get_employee_number()
            self.fields['primary_driver'].initial = self.instance.get_qualitative_insight('primary_driver')
            self.fields['improvement_areas'].initial = self.instance.get_qualitative_insight('improvement_areas')
            self.fields['categorization'].initial = self.instance.get_qualitative_insight('categorization')
            self.fields['additional_feedback'].initial = self.instance.get_qualitative_insight('additional_feedback')
        else:
            self.fields['date_filed'].initial = date.today()

    def clean(self):
        cleaned_data = super().clean()
        desired = cleaned_data.get('desired_last_day')
        approved = cleaned_data.get('approved_last_day')

        if desired and approved and approved < desired:
            raise ValidationError({
                'approved_last_day': "Approved last day cannot be earlier than desired last day."
            })

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.qualitative_data = {
            'primary_driver': self.cleaned_data.get('primary_driver', ''),
            'improvement_areas': self.cleaned_data.get('improvement_areas', ''),
            'categorization': self.cleaned_data.get('categorization', ''),
            'additional_feedback': self.cleaned_data.get('additional_feedback', ''),
        }

        if commit:
            instance.save()
        return instance
