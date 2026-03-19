"""
Views for Payroll Settings Management
Handles: TierThresholdSetting, DeMinimisType, DeductionType, EmployeeSalarySetting
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import date as date_type
from django.db import connection
from django.core.exceptions import ValidationError

from App.authentication.decorators import login_required

from .models import (
    TierThresholdSetting, 
    DeMinimisType, 
    DeductionType,
    EmployeeSalarySetting,
    EmployeeDeductionAccount,
)
from App.users.models import Staff
from .forms_payroll_settings import (
    TierThresholdSettingForm,
    DeMinimisTypeForm,
    DeductionTypeForm,
    EmployeeSalarySettingForm
)


def _deactivate_record_raw(model_class, pk):
    """
    Deactivate a record using raw SQL to bypass clean() validation.
    Sets is_active=False, effective_end_date=now(), and modifies unique field to avoid constraint violations.
    Returns the old unique field value before modification.
    """
    from django.db import transaction
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            # Get current values
            cursor.execute(f"SELECT tier_name FROM {model_class._meta.db_table} WHERE id = %s", [pk])
            row = cursor.fetchone()
            if not row:
                return None
            
            old_unique_value = row[0]
            new_unique_value = f"{old_unique_value}_OLD_{pk}"
            
            # Update record directly (bypasses clean())
            cursor.execute(f"""
                UPDATE {model_class._meta.db_table}
                SET tier_name = %s, is_active = FALSE, effective_end_date = %s, updated_at = %s
                WHERE id = %s
            """, [new_unique_value, timezone.now().date(), timezone.now(), pk])
            
            return old_unique_value


def _deactivate_deminimis_raw(pk):
    """
    Deactivate a DeMinimisType record using raw SQL to bypass clean() validation.
    """
    from django.db import transaction
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT code FROM human_resource_deminimistype WHERE id = %s", [pk])
            row = cursor.fetchone()
            if not row:
                return None
            
            old_code = row[0]
            new_code = f"{old_code}_OLD_{pk}"
            
            cursor.execute("""
                UPDATE human_resource_deminimistype
                SET code = %s, is_active = FALSE, effective_end_date = %s, updated_at = %s
                WHERE id = %s
            """, [new_code, timezone.now().date(), timezone.now(), pk])
            
            return old_code


def _deactivate_deduction_raw(pk):
    """
    Deactivate a DeductionType record using raw SQL to bypass clean() validation.
    """
    from django.db import transaction
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT code FROM human_resource_deductiontype WHERE id = %s", [pk])
            row = cursor.fetchone()
            if not row:
                return None
            
            old_code = row[0]
            new_code = f"{old_code}_OLD_{pk}"
            
            cursor.execute("""
                UPDATE human_resource_deductiontype
                SET code = %s, is_active = FALSE, effective_end_date = %s, updated_at = %s
                WHERE id = %s
            """, [new_code, timezone.now().date(), timezone.now(), pk])
            
            return old_code


# ==================== TIER THRESHOLD SETTINGS ====================

@login_required
def tier_list(request):
    """List all tier threshold settings with filtering"""
    from django.db.models import Q
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    tier_filter = request.GET.get('tier', '')
    
    # Base queryset
    tiers = TierThresholdSetting.objects.all()
    
    # Filter by status
    if status_filter == 'active':
        tiers = tiers.filter(is_active=True)
    elif status_filter == 'inactive':
        tiers = tiers.filter(is_active=False)
    
    # Filter by tier name
    if tier_filter:
        tiers = tiers.filter(tier_name=tier_filter)
    
    # Order by tier_name and start date
    tiers = tiers.order_by('tier_name', '-effective_start_date')
    
    return render(request, 'hr/default/payroll_settings/tier_list.html', {
        'tiers': tiers,
        'status_filter': status_filter,
        'tier_filter': tier_filter
    })


@login_required
def tier_add(request):
    """Add new tier threshold setting"""
    if request.method == 'POST':
        form = TierThresholdSettingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tier threshold added successfully.')
            return redirect('human_resource:tier_list')
    else:
        form = TierThresholdSettingForm()
    
    return render(request, 'hr/default/payroll_settings/tier_form.html', {'form': form})


@login_required
def tier_edit(request, pk):
    """Edit tier threshold setting - creates new record for history"""
    tier = get_object_or_404(TierThresholdSetting, pk=pk)
    
    if request.method == 'POST':
        form = TierThresholdSettingForm(request.POST, instance=tier)
        if form.is_valid():
            try:
                # Deactivate old record first - skip validation
                tier._deactivating_only = True
                tier.is_active = False
                tier.effective_end_date = timezone.now().date()
                tier.save(update_fields=['is_active', 'effective_end_date', 'updated_at'])
                tier._deactivating_only = False
                
                # Create new record with form data
                new_tier = form.save(commit=False)
                new_tier.pk = None
                new_tier.is_active = True
                new_tier.effective_end_date = None
                new_tier._skip_clean = True
                new_tier.save()
                
                messages.success(request, 'Tier threshold updated. History preserved.')
                return redirect('human_resource:tier_list')
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    form.add_error(field, errors)
    else:
        form = TierThresholdSettingForm(instance=tier)
    
    return render(request, 'hr/default/payroll_settings/tier_form.html', {'form': form})


# ==================== DE MINIMIS TYPES ====================

@login_required
def deminimis_list(request):
    """List all de minimis types with filtering"""
    from django.db.models import Q
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    types = DeMinimisType.objects.all()
    
    # Filter by status
    if status_filter == 'active':
        types = types.filter(is_active=True)
    elif status_filter == 'inactive':
        types = types.filter(is_active=False)
    
    # Filter by search (name or code)
    if search_query:
        types = types.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        )
    
    # Order by display_order and name
    types = types.order_by('display_order', 'name')
    
    return render(request, 'hr/default/payroll_settings/deminimis_list.html', {
        'types': types,
        'status_filter': status_filter,
        'search_query': search_query
    })


@login_required
def deminimis_add(request):
    """Add new de minimis type"""
    if request.method == 'POST':
        form = DeMinimisTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'De minimis type added successfully.')
            return redirect('human_resource:demiminimis_list')
    else:
        form = DeMinimisTypeForm()
    
    return render(request, 'hr/default/payroll_settings/deminimis_form.html', {'form': form})


@login_required
def deminimis_form(request, pk=None):
    """Add or edit de minimis type - creates new record for history when editing"""
    from django.utils import timezone
    from django.core.exceptions import ValidationError
    
    # Check for pk in POST data (from modal form)
    post_pk = request.POST.get('pk')
    if post_pk:
        try:
            dem = DeMinimisType.objects.get(pk=post_pk)
        except DeMinimisType.DoesNotExist:
            dem = None
    elif pk:
        dem = get_object_or_404(DeMinimisType, pk=pk)
    else:
        dem = None
    
    if request.method == 'POST':
        # Pre-process: update old record first to free up the code
        if dem:
            # Edit mode: deactivate old record first
            dem._deactivating_only = True
            dem.is_active = False
            dem.effective_end_date = timezone.now().date()
            
            # Append _OLD_X suffix to code for audit trail
            old_code = dem.code
            if not old_code.endswith('_OLD_'):
                # Count existing OLD records for this code
                old_count = DeMinimisType.objects.filter(
                    code__startswith=old_code + '_OLD_'
                ).count()
                new_old_code = f'{old_code}_OLD_{old_count + 1}'
                dem.code = new_old_code
                
                # Also append to name for display
                dem.name = f'{dem.name} (OLD)'
            
            # Save old record WITHOUT going through full clean
            # Use raw SQL update to bypass validation
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE human_resource_deminimistype SET 
                    code = %s, name = %s, is_active = %s, 
                    effective_end_date = %s, updated_at = %s WHERE id = %s""",
                    [dem.code, dem.name, False, dem.effective_end_date, timezone.now(), dem.pk]
                )
            
            # Now create form with the updated dem instance
            form = DeMinimisTypeForm(request.POST, instance=dem)
            if form.is_valid():
                # Create new record with form data
                new_dem = form.save(commit=False)
                new_dem.pk = None
                new_dem.is_active = True
                new_dem.effective_end_date = None
                new_dem._skip_clean = True
                new_dem.save()
                
                messages.success(request, 'De minimis type updated. Old record marked as (OLD).')
                return redirect('human_resource:demiminimis_list')
        else:
            # Add mode
            form = DeMinimisTypeForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'De minimis type added successfully.')
                return redirect('human_resource:demiminimis_list')
    else:
        form = DeMinimisTypeForm(instance=dem)
    
    return render(request, 'hr/default/payroll_settings/deminimis_form.html', {
        'form': form, 
        'dem': dem
    })


@login_required
def deminimis_delete(request, pk):
    """Delete a de minimis type"""
    if request.method == 'POST':
        dem = get_object_or_404(DeMinimisType, pk=pk)
        dem.delete()
        messages.success(request, f'De minimis type "{dem.name}" deleted successfully.')
    return redirect('human_resource:demiminimis_list')


# ==================== DEDUCTION TYPES ====================

@login_required
def deduction_type_list(request):
    """List all deduction types with filtering"""
    from django.db.models import Q
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    types = DeductionType.objects.all()
    
    # Filter by status
    if status_filter == 'active':
        types = types.filter(is_active=True)
    elif status_filter == 'inactive':
        types = types.filter(is_active=False)
    
    # Filter by category
    if category_filter:
        types = types.filter(category=category_filter)
    
    # Filter by search (name or code)
    if search_query:
        types = types.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        )
    
    # Order by category, display_order, and name
    types = types.order_by('category', 'display_order', 'name')
    
    # Get counts for stats cards
    active_count = DeductionType.objects.filter(is_active=True).count()
    government_count = DeductionType.objects.filter(is_government=True).count()
    category_count = DeductionType.objects.values('category').distinct().count()
    
    return render(request, 'hr/default/payroll_settings/deduction_list.html', {
        'types': types,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'active_count': active_count,
        'government_count': government_count,
        'category_count': category_count
    })


@login_required
def deduction_type_form(request, pk=None):
    """Add or edit deduction type - creates new record for history when editing"""
    from django.utils import timezone
    from django.core.exceptions import ValidationError
    from django.db import connection
    
    # Check for pk in POST data (from modal form)
    post_pk = request.POST.get('pk')
    if post_pk:
        try:
            deduction = DeductionType.objects.get(pk=post_pk)
        except DeductionType.DoesNotExist:
            deduction = None
    elif pk:
        deduction = get_object_or_404(DeductionType, pk=pk)
    else:
        deduction = None
    
    if request.method == 'POST':
        # Pre-process: update old record first to free up the code
        if deduction:
            # Edit mode: deactivate old record first
            deduction._deactivating_only = True
            deduction.is_active = False
            deduction.effective_end_date = timezone.now().date()
            
            # Append _OLD_X suffix to code for audit trail
            old_code = deduction.code
            if not old_code.endswith('_OLD_'):
                # Count existing OLD records for this code
                old_count = DeductionType.objects.filter(
                    code__startswith=old_code + '_OLD_'
                ).count()
                new_old_code = f'{old_code}_OLD_{old_count + 1}'
                deduction.code = new_old_code
                
                # Also append to name for display
                deduction.name = f'{deduction.name} (OLD)'
            
            # Save old record WITHOUT going through full clean
            # Use raw SQL update to bypass validation
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE human_resource_deductiontype SET 
                    code = %s, name = %s, is_active = %s, 
                    effective_end_date = %s, updated_at = %s WHERE id = %s""",
                    [deduction.code, deduction.name, False, deduction.effective_end_date, timezone.now(), deduction.pk]
                )
            
            # Now create form with the updated deduction instance
            form = DeductionTypeForm(request.POST, instance=deduction)
            if form.is_valid():
                # Create new record with form data
                new_deduction = form.save(commit=False)
                new_deduction.pk = None
                new_deduction.is_active = True
                new_deduction.effective_end_date = None
                new_deduction._skip_clean = True
                new_deduction.save()
                
                messages.success(request, 'Deduction type updated. Old record marked as (OLD).')
                return redirect('human_resource:deduction_type_list')
        else:
            # Add mode
            form = DeductionTypeForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Deduction type added successfully.')
                return redirect('human_resource:deduction_type_list')
    else:
        form = DeductionTypeForm(instance=deduction)
    
    return render(request, 'hr/default/payroll_settings/deduction_form.html', {
        'form': form, 
        'deduction': deduction
    })


@login_required
def deduction_type_delete(request, pk):
    """Delete a deduction type"""
    if request.method == 'POST':
        deduction = get_object_or_404(DeductionType, pk=pk)
        deduction.delete()
        messages.success(request, f'Deduction type "{deduction.name}" deleted successfully.')
    return redirect('human_resource:deduction_type_list')


# ==================== EMPLOYEE SALARY SETTINGS ====================

@login_required
def salary_setting_list(request):
    """List all employee salary settings with filtering"""
    from django.db.models import Q
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    settings = EmployeeSalarySetting.objects.select_related('employee', 'tier').all()
    
    # Filter by status
    if status_filter == 'active':
        settings = settings.filter(is_active=True)
    elif status_filter == 'inactive':
        settings = settings.filter(is_active=False)
    
    # Filter by search (employee name)
    if search_query:
        settings = settings.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__employee_number__icontains=search_query)
        )
    
    # Order by employee name and start date
    settings = settings.order_by('employee__last_name', '-effective_start_date')
    
    return render(request, 'hr/default/payroll_settings/salary_setting_list.html', {
        'settings': settings,
        'status_filter': status_filter,
        'search_query': search_query
    })


@login_required
def salary_setting_add(request):
    """Add new employee salary setting"""
    if request.method == 'POST':
        form = EmployeeSalarySettingForm(request.POST)
        if form.is_valid():
            salary_setting = form.save(commit=False)
            # Compute salary per cutoff (monthly / 2)
            salary_setting.salary_per_cutoff = salary_setting.base_salary_monthly / 2
            salary_setting.save()
            messages.success(request, 'Salary setting added successfully.')
            return redirect('human_resource:salary_setting_list')
    else:
        form = EmployeeSalarySettingForm()
    
    return render(request, 'hr/default/payroll_settings/salary_form.html', {'form': form})


@login_required
def salary_setting_edit(request, pk):
    """
    Edit employee salary setting - creates new record for history.
    Employee field is read-only during edit (can't change employee).
    """
    salary_setting = get_object_or_404(EmployeeSalarySetting, pk=pk)
    is_edit = True
    
    if request.method == 'POST':
        form = EmployeeSalarySettingForm(request.POST, instance=salary_setting)
        if form.is_valid():
            try:
                # Store the original employee before deactivation
                original_employee = salary_setting.employee
                original_start_date = salary_setting.effective_start_date
                
                # Deactivate old record FIRST - skip validation for this update
                # We only want to update is_active and effective_end_date
                salary_setting._deactivating_only = True
                salary_setting.is_active = False
                salary_setting.effective_end_date = timezone.now().date()
                salary_setting.save(update_fields=['is_active', 'effective_end_date', 'updated_at'])
                salary_setting._deactivating_only = False  # Reset flag
                
                # Create new record with form data
                new_setting = form.save(commit=False)
                new_setting.pk = None
                new_setting.is_active = True
                new_setting.effective_end_date = None  # Ensure no end date for new record
                
                # Compute salary per cutoff (monthly / 2)
                new_setting.salary_per_cutoff = new_setting.base_salary_monthly / 2
                
                # Skip model clean() since old record is already deactivated
                # The clean() method checks for overlaps, but since the old record
                # was just deactivated, there should be no conflicts
                new_setting._skip_clean = True
                new_setting.save()
                
                messages.success(request, 'Salary setting updated. History preserved.')
                return redirect('human_resource:salary_setting_list')
            except ValidationError as e:
                # Add validation errors to form
                for field, errors in e.message_dict.items():
                    form.add_error(field, errors)
    else:
        form = EmployeeSalarySettingForm(instance=salary_setting)
        # Make employee field readonly for edit
        form.fields['employee'].widget.attrs['readonly'] = True
        form.fields['employee'].widget.attrs['disabled'] = True
    
    return render(request, 'hr/default/payroll_settings/salary_form.html', {
        'form': form, 
        'is_edit': is_edit,
        'original_employee': salary_setting.employee
    })


# ==================== UTILITY FUNCTIONS ====================

def get_active_settings_for_date(date):
    """
    Get all active settings for a specific date.
    Used by payroll preview to load appropriate settings.
    """
    from datetime import date as date_type
    
    # Convert if needed
    if isinstance(date, str):
        date = date_type.fromisoformat(date)
    
    tier = TierThresholdSetting.objects.filter(
        is_active=True,
        effective_start_date__lte=date
    ).filter(
        Q(effective_end_date__isnull=True) | Q(effective_end_date__gte=date)
    ).first()
    
    deminimis_types = DeMinimisType.objects.filter(
        is_active=True,
        effective_start_date__lte=date
    ).filter(
        Q(effective_end_date__isnull=True) | Q(effective_end_date__gte=date)
    ).order_by('display_order')
    
    deduction_types = DeductionType.objects.filter(
        is_active=True,
        effective_start_date__lte=date
    ).filter(
        Q(effective_end_date__isnull=True) | Q(effective_end_date__gte=date)
    ).order_by('display_order')
    
    return {
        'tier': tier,
        'demimimis_types': deminimis_types,
        'deduction_types': deduction_types
    }


def get_employee_salary_for_date(employee, date):
    """
    Get the active salary setting for an employee for a specific date.
    Returns None if no salary setting exists.
    """
    from datetime import date as date_type
    from django.db.models import Q
    
    if isinstance(date, str):
        date = date_type.fromisoformat(date)
    
    salary_setting = EmployeeSalarySetting.objects.filter(
        employee=employee,
        is_active=True,
        effective_start_date__lte=date
    ).filter(
        Q(effective_end_date__isnull=True) | Q(effective_end_date__gte=date)
    ).select_related('tier').first()
    
    return salary_setting


# ==================== EMPLOYEE DEDUCTION ACCOUNTS ====================

@login_required
def employee_deduction_account_list(request):
    """
    List all employee deduction accounts with filtering.
    This page manages government, attendance, and insurance account numbers for employees.
    """
    from django.db.models import Q
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('search', '')
    employee_filter = request.GET.get('employee', '')
    
    # Base queryset
    accounts = EmployeeDeductionAccount.objects.select_related('employee', 'deduction_type').all()
    
    # Filter by status
    if status_filter == 'active':
        accounts = accounts.filter(is_active=True)
    elif status_filter == 'inactive':
        accounts = accounts.filter(is_active=False)
    
    # Filter by category (deduction type category)
    if category_filter:
        accounts = accounts.filter(deduction_type__category=category_filter)
    
    # Filter by search (employee name or account number)
    if search_query:
        accounts = accounts.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__employee_number__icontains=search_query) |
            Q(account_number__icontains=search_query) |
            Q(insurance_policy_number__icontains=search_query)
        )
    
    # Filter by specific employee
    if employee_filter:
        accounts = accounts.filter(employee_id=employee_filter)
    
    # Order by employee name and deduction type
    accounts = accounts.order_by('employee__last_name', 'employee__first_name', 'deduction_type__category')
    
    # Get counts for stats cards
    active_count = EmployeeDeductionAccount.objects.filter(is_active=True).count()
    government_count = EmployeeDeductionAccount.objects.filter(
        deduction_type__category='GOVERNMENT',
        is_active=True
    ).count()
    insurance_count = EmployeeDeductionAccount.objects.filter(
        has_insurance=True,
        is_active=True
    ).count()
    attendance_count = EmployeeDeductionAccount.objects.filter(
        deduction_type__category='ATTENDANCE',
        is_active=True
    ).count()
    
    # Get deduction types for the category filter dropdown
    deduction_types = DeductionType.objects.filter(is_active=True).order_by('category', 'name')
    
    # Get employees for the employee filter dropdown
    employees = Staff.objects.filter(status='active').order_by('last_name', 'first_name')
    
    return render(request, 'hr/default/payroll_settings/employee_deduction_account_list.html', {
        'accounts': accounts,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'employee_filter': employee_filter,
        'active_count': active_count,
        'government_count': government_count,
        'insurance_count': insurance_count,
        'attendance_count': attendance_count,
        'deduction_types': deduction_types,
        'employees': employees
    })


@login_required
def employee_deduction_account_form(request, pk=None):
    """
    Add or edit employee deduction account.
    Creates new record for history when editing.
    """
    from django.utils import timezone
    from django.core.exceptions import ValidationError
    from django.db import connection
    
    # Check for pk in POST data (from modal form)
    post_pk = request.POST.get('pk')
    if post_pk:
        try:
            account = EmployeeDeductionAccount.objects.get(pk=post_pk)
        except EmployeeDeductionAccount.DoesNotExist:
            account = None
    elif pk:
        account = get_object_or_404(EmployeeDeductionAccount, pk=pk)
    else:
        account = None
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        deduction_type_id = request.POST.get('deduction_type')
        account_number = request.POST.get('account_number', '').strip()
        employer_account_number = request.POST.get('employer_account_number', '').strip()
        has_insurance = request.POST.get('has_insurance') == 'on'
        insurance_policy_number = request.POST.get('insurance_policy_number', '').strip() if has_insurance else ''
        is_active = request.POST.get('is_active') == 'on'
        effective_start_date = request.POST.get('effective_start_date')
        effective_end_date = request.POST.get('effective_end_date') or None
        notes = request.POST.get('notes', '')
        
        # Validate required fields
        if not employee_id or not deduction_type_id:
            messages.error(request, 'Employee and Deduction Type are required.')
            return redirect('human_resource:employee_deduction_account_list')
        
        try:
            employee = Staff.objects.get(pk=employee_id)
            deduction_type = DeductionType.objects.get(pk=deduction_type_id)
        except (Staff.DoesNotExist, DeductionType.DoesNotExist) as e:
            messages.error(request, 'Invalid employee or deduction type.')
            return redirect('human_resource:employee_deduction_account_list')
        
        # Pre-process: update old record first to free up the unique constraint
        if account:
            # Edit mode: deactivate old record first
            account._deactivating_only = True
            account.is_active = False
            account.effective_end_date = timezone.now().date()
            
            # Save old record using raw SQL to bypass validation
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE human_resource_employeendeductionaccount SET 
                    is_active = %s, effective_end_date = %s, updated_at = %s WHERE id = %s""",
                    [False, account.effective_end_date, timezone.now(), account.pk]
                )
            
            # Create new record with form data
            new_account = EmployeeDeductionAccount(
                employee=employee,
                deduction_type=deduction_type,
                account_number=account_number or None,
                employer_account_number=employer_account_number or None,
                has_insurance=has_insurance,
                insurance_policy_number=insurance_policy_number or None,
                is_active=is_active,
                effective_start_date=effective_start_date or timezone.now().date(),
                effective_end_date=effective_end_date,
                notes=notes
            )
            new_account._skip_clean = True
            new_account.save()
            messages.success(request, f'Employee deduction account updated for {employee}. Old record deactivated.')
        else:
            # Add mode: check if there's already an active account for this employee and deduction type
            existing = EmployeeDeductionAccount.objects.filter(
                employee=employee,
                deduction_type=deduction_type,
                is_active=True
            ).first()
            
            if existing:
                # Deactivate existing and create new
                existing._deactivating_only = True
                existing.is_active = False
                existing.effective_end_date = timezone.now().date()
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE human_resource_employeendeductionaccount SET 
                        is_active = %s, effective_end_date = %s, updated_at = %s WHERE id = %s""",
                        [False, existing.effective_end_date, timezone.now(), existing.pk]
                    )
            
            # Create new record
            new_account = EmployeeDeductionAccount(
                employee=employee,
                deduction_type=deduction_type,
                account_number=account_number or None,
                employer_account_number=employer_account_number or None,
                has_insurance=has_insurance,
                insurance_policy_number=insurance_policy_number or None,
                is_active=is_active,
                effective_start_date=effective_start_date or timezone.now().date(),
                effective_end_date=effective_end_date,
                notes=notes
            )
            new_account._skip_clean = True
            new_account.save()
            messages.success(request, f'Employee deduction account created for {employee}.')
        
        return redirect('human_resource:employee_deduction_account_list')
    
    # GET request - show form
    deduction_types = DeductionType.objects.filter(is_active=True).order_by('category', 'name')
    employees = Staff.objects.filter(status='active').order_by('last_name', 'first_name')
    
    return render(request, 'hr/default/payroll_settings/employee_deduction_account_form.html', {
        'account': account,
        'deduction_types': deduction_types,
        'employees': employees
    })


@login_required
def employee_deduction_account_delete(request, pk):
    """Delete an employee deduction account"""
    if request.method == 'POST':
        account = get_object_or_404(EmployeeDeductionAccount, pk=pk)
        employee_name = str(account.employee)
        deduction_name = account.deduction_type.name
        account.delete()
        messages.success(request, f'Deduction account for {employee_name} ({deduction_name}) deleted successfully.')
    return redirect('human_resource:employee_deduction_account_list')


@login_required
def employee_deduction_accounts_by_employee(request, employee_id):
    """
    Get all deduction accounts for a specific employee.
    Used for AJAX calls to display employee deduction info.
    """
    employee = get_object_or_404(Staff, pk=employee_id)
    accounts = EmployeeDeductionAccount.objects.filter(
        employee=employee,
        is_active=True
    ).select_related('deduction_type').order_by('deduction_type__category', 'deduction_type__name')
    
    return render(request, 'hr/default/payroll_settings/employee_deduction_accounts_partial.html', {
        'employee': employee,
        'accounts': accounts
    })

