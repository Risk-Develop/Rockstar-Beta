from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat
from django.utils import timezone

from datetime import date, time, datetime, timedelta
from decimal import Decimal

from App.users.models import Staff, Role, Position, Department
from App.users.forms import StaffForm, RoleForm, PositionForm, DepartmentForm
from App.authentication.decorators import login_required

from .models import (
    Attendance,
    EmployeeProfileSettings,
    EmployeeShiftRule,
    LeaveCredit,
    LeaveRequest,
)
from .forms import EmployeeShiftRuleForm, LeaveCreditForm, LeaveRequestForm


# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURATION FLAGS
# ═════════════════════════════════════════════════════════════════════════════

# Set True to skip Saturdays & Sundays when creating attendance rows for leave
SKIP_WEEKENDS = False


# ═════════════════════════════════════════════════════════════════════════════
# LEAVE → ATTENDANCE HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _date_range(start: date, end: date):
    """Yield every date from start to end inclusive, skipping weekends if configured."""
    current = start
    while current <= end:
        if not SKIP_WEEKENDS or current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def create_attendance_from_leave(leave_request):
    """
    For each day in the approved leave's date range, create or update an
    Attendance record with status='on_leave' and statuses='on_leave'.
    """
    employee = leave_request.employee

    for day in _date_range(leave_request.start_date, leave_request.end_date):
        try:
            attendance = Attendance.objects.get(employee=employee, date=day)

            # Don't overwrite a day the employee actually worked
            real_statuses = {'present', 'late'}
            if set(attendance.get_statuses_list()) & real_statuses:
                continue

            attendance.clock_in      = None
            attendance.clock_out     = None
            attendance.lunch_in      = None
            attendance.lunch_out     = None
            attendance.status        = 'on_leave'
            attendance.leave_request = leave_request
            attendance.set_statuses(['on_leave'])
            attendance.save()

        except Attendance.DoesNotExist:
            Attendance.objects.create(
                employee      = employee,
                date          = day,
                status        = 'on_leave',
                statuses      = 'on_leave',
                clock_in      = None,
                clock_out     = None,
                leave_request = leave_request,
            )


def remove_attendance_for_leave(leave_request):
    """
    Delete on_leave attendance rows that were auto-created for this leave request.
    """
    deleted, _ = Attendance.objects.filter(
        employee=leave_request.employee,
        leave_request=leave_request,
        status='on_leave',
    ).delete()

    if not deleted:
        dates = list(_date_range(leave_request.start_date, leave_request.end_date))
        Attendance.objects.filter(
            employee=leave_request.employee,
            date__in=dates,
            status='on_leave',
        ).delete()


# ═════════════════════════════════════════════════════════════════════════════
# HR DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def human_resource_dashboard(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        return render(request, "hr/dashboard/hr_dashboard.html", {"employee": None, "is_owner": True})
    
    emp = Staff.objects.filter(employee_number=emp_num).first()
    if not emp:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    return render(request, "hr/dashboard/hr_dashboard.html", {"employee": emp})


# ═════════════════════════════════════════════════════════════════════════════
# STAFF HISTORY
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def staff_history_hr_list(request):
    from App.users.models import StaffHistory

    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')

    # Owner bypass - allow access without Staff record
    if is_owner:
        staff_history = StaffHistory.objects.all().order_by('-created_at')
        context = {
            'staff_history': staff_history,
            'is_owner': True
        }
        return render(request, "hr/dashboard/staff_history_list.html", context)
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''

    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to view staff history.")
        return redirect('human_resource:hr_dashboard')

    history_records = StaffHistory.objects.select_related('staff', 'changed_by').all()

    staff_id   = request.GET.get('staff')
    field_name = request.GET.get('field')
    start_date = request.GET.get('start_date')
    end_date   = request.GET.get('end_date')

    if staff_id:
        history_records = history_records.filter(staff_id=staff_id)
    if field_name:
        history_records = history_records.filter(field_name=field_name)
    if start_date:
        try:
            history_records = history_records.filter(
                changed_at__date__gte=datetime.strptime(start_date, '%Y-%m-%d').date()
            )
        except ValueError:
            pass
    if end_date:
        try:
            history_records = history_records.filter(
                changed_at__date__lte=datetime.strptime(end_date, '%Y-%m-%d').date()
            )
        except ValueError:
            pass

    history_records = history_records.order_by('-changed_at')
    paginator    = Paginator(history_records, 20)
    history_page = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'hr/dashboard/staff_history_list.html', {
        'employee':        employee,
        'history_records': history_page,
        'staff_list':      Staff.objects.all().order_by('last_name', 'first_name'),
        'field_choices':   StaffHistory.FIELD_CHOICES,
        'staff_id':        staff_id,
        'field_name':      field_name,
        'start_date':      start_date,
        'end_date':        end_date,
    })


# ═════════════════════════════════════════════════════════════════════════════
# ROLE MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

def _get_hr_employee(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return None, redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        return None, None  # None for employee, None for redirect (allow access)
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return None, redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        return employee, None
    return employee, None


@login_required
def role_list(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        roles = Role.objects.all().order_by('role_name')
        return render(request, 'hr/default/roles/role_list.html', {'roles': roles, 'employee': None, 'is_owner': True})
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to view role management.")
        return redirect('human_resource:hr_dashboard')
    roles = Role.objects.all().order_by('role_name')
    return render(request, 'hr/default/roles/role_list.html', {'roles': roles, 'employee': employee})


@login_required
def role_add(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        if request.method == 'POST':
            form = RoleForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Role added successfully.')
                return redirect('human_resource:role_list')
        else:
            form = RoleForm()
        return render(request, 'hr/default/roles/role_form.html', {'form': form, 'action': 'Add', 'employee': None, 'is_owner': True})
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to add roles.")
        return redirect('human_resource:hr_dashboard')
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role added successfully.')
            return redirect('human_resource:role_list')
    else:
        form = RoleForm()
    return render(request, 'hr/default/roles/role_form.html', {'form': form, 'action': 'Add', 'employee': employee})


@login_required
def role_edit(request, pk):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        role = get_object_or_404(Role, pk=pk)
        if request.method == 'POST':
            form = RoleForm(request.POST, instance=role)
            if form.is_valid():
                form.save()
                messages.success(request, 'Role updated successfully.')
                return redirect('human_resource:role_list')
        else:
            form = RoleForm(instance=role)
        return render(request, 'hr/default/roles/role_form.html', {
            'form': form, 'action': 'Edit', 'employee': None, 'role': role, 'is_owner': True
        })
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to edit roles.")
        return redirect('human_resource:hr_dashboard')
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role updated successfully.')
            return redirect('human_resource:role_list')
    else:
        form = RoleForm(instance=role)
    return render(request, 'hr/default/roles/role_form.html', {
        'form': form, 'action': 'Edit', 'employee': employee, 'role': role
    })


@login_required
def role_delete(request, pk):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        role = get_object_or_404(Role, pk=pk)
        if request.method == 'POST':
            role.delete()
            messages.success(request, 'Role deleted successfully.')
            return redirect('human_resource:role_list')
        return render(request, 'hr/default/roles/role_confirm_delete.html', {'role': role, 'employee': None, 'is_owner': True})
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to delete roles.")
        return redirect('human_resource:hr_dashboard')
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        role.delete()
        messages.success(request, 'Role deleted successfully.')
        return redirect('human_resource:role_list')
    return render(request, 'hr/default/roles/role_confirm_delete.html', {'role': role, 'employee': employee})


# ═════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def hr_user_mgnt(request):
    staff_list = Staff.objects.select_related('role').order_by('last_name', 'first_name')
    roles      = Role.objects.filter(is_active=True).order_by('role_name')
    
    # Count staff with roles assigned
    roles_assigned = staff_list.exclude(role__isnull=True).count()
    
    # Count unique departments
    departments_count = staff_list.exclude(department__isnull=True).values('department').distinct().count()
    
    return render(request, 'hr/default/user_mgnt/hr_user_mgnt.html', {
        'staff_list': staff_list,
        'roles':      roles,
        'roles_assigned': roles_assigned,
        'departments_count': departments_count,
    })


@login_required
def update_staff_role(request):
    if request.method == 'POST':
        staff         = get_object_or_404(Staff, id=request.POST.get('staff_id'))
        role_id       = request.POST.get('role')
        staff.role_id = role_id if role_id else None
        staff.save()
    return redirect(reverse('human_resource:hr_user_mgnt'))


@login_required
def hr_user_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        staff.delete()
        return redirect('human_resource:hr_user_mgnt')
    return render(request, 'hr/default/user_mgnt/hr_user_delete.html', {'staff': staff})


@login_required
def dashboard_user_detail(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    return render(request, 'hr/default/user_mgnt/hr_user_details.html', {'staff': staff})


@login_required
def ajax_user_list(request):
    search      = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    page        = request.GET.get('page', 1)

    qs = Staff.objects.select_related('role').all()
    if search:
        qs = qs.filter(last_name__icontains=search) | qs.filter(first_name__icontains=search)
    if role_filter:
        qs = qs.filter(role_id=role_filter)
    qs = qs.order_by('last_name', 'first_name')

    paginator  = Paginator(qs, 5)
    staff_list = paginator.get_page(page)
    roles      = Role.objects.filter(is_active=True)

    html = render_to_string(
        'hr/default/user_mgnt/hr_user_list_rows.html',
        {'staff_list': staff_list, 'roles': roles},
        request=request,
    )
    return JsonResponse({
        'html':         html,
        'page_number':  staff_list.number,
        'num_pages':    paginator.num_pages,
        'has_previous': staff_list.has_previous(),
        'has_next':     staff_list.has_next(),
    })


@login_required
def dashboard_user_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse('human_resource:hr_user_mgnt'))
    else:
        form = StaffForm()
    return render(request, 'hr/default/user_mgnt/hr_user_form.html', {'form': form, 'action': 'Add'})


@login_required
def dashboard_user_edit(request, pk):
    obj = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=obj)
        if form.is_valid():
            staff = form.save(commit=False)
            if not staff.employee_number:
                staff.employee_number = obj.employee_number
            staff.save()
            return redirect(reverse('human_resource:hr_user_mgnt'))
    else:
        form = StaffForm(instance=obj)
    return render(request, 'hr/default/user_mgnt/hr_user_form.html', {'form': form, 'action': 'Edit', 'staff': obj})


@login_required
def check_employee_number(request):
    emp_no   = request.GET.get('emp_no', '').strip()
    staff_id = request.GET.get('staff_id')
    if not emp_no:
        return JsonResponse({'exists': False})
    qs = Staff.objects.filter(employee_number=emp_no)
    if staff_id:
        qs = qs.exclude(id=staff_id)
    return JsonResponse({'exists': qs.exists()})


# ═════════════════════════════════════════════════════════════════════════════
# EMPLOYEE PROFILE SETTINGS
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def employee_list(request):
    employees = Staff.objects.all()
    return render(request, 'hr/default/employees/employeeproset_list.html', {'employees': employees})


@login_required
def employee_profile(request, employee_id):
    employee   = get_object_or_404(Staff, id=employee_id)
    profile, _ = EmployeeProfileSettings.objects.get_or_create(employee=employee)

    if request.method == 'POST':
        profile.rank       = request.POST.get('rank')
        profile.shift      = request.POST.get('shift')
        profile.current_vl = request.POST.get('vl')
        profile.current_sl = request.POST.get('sl')
        profile.save()
        return redirect('human_resource:hr_employee_list')

    return render(request, 'hr/default/employees/employee_profile.html', {
        'employee':     employee,
        'profile':      profile,
        'shifts':       Staff.SHIFT_CHOICES,
        'RANK_CHOICES': Staff.RANK_CHOICES,
    })


# ═════════════════════════════════════════════════════════════════════════════
# ATTENDANCE — HR LIST
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def attendance_list(request):
    qs = Attendance.objects.select_related(
        'employee',
        'employee__departmentlink',
        'employee__positionlink',
        'leave_request',
    ).order_by('-date', 'employee__last_name')

    search     = request.GET.get('search', '').strip()
    date_from  = request.GET.get('date_from', '')
    date_to    = request.GET.get('date_to', '')
    department = request.GET.get('department', '')
    status     = request.GET.getlist('status')

    if search:
        qs = qs.filter(
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search)
        )
    if date_from:
        try:
            qs = qs.filter(date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass
    if department:
        qs = qs.filter(employee__departmentlink__id=department)
    if status:
        sq = Q()
        for s in status:
            sq |= Q(statuses__icontains=s) | Q(status=s)
        qs = qs.filter(sq)

    def _count(s):
        return qs.filter(Q(statuses__icontains=s) | Q(status=s)).count()

    present_count             = _count('present')
    absent_count              = _count('absent')
    late_count                = _count('late')
    on_leave_count            = _count('on_leave')
    failed_to_clock_out_count = _count('failed_to_clock_out')
    overlunch_pending_count   = _count('overlunch_pending')
    missing_lunch_count       = _count('missing_lunch')
    pending_count             = failed_to_clock_out_count + overlunch_pending_count + missing_lunch_count

    paginator   = Paginator(qs, 25)
    attendances = paginator.get_page(request.GET.get('page', 1))
    
    # Get all records for calendar (without pagination)
    all_attendances = qs.all()

    departments = []
    try:
        from App.users.models import Department
        departments = Department.objects.all().order_by('department_name')
    except Exception:
        pass

    return render(request, 'hr/default/attendance/attendance_list.html', {
        'attendances':               attendances,
        'all_attendances':           all_attendances,
        'total_records':             paginator.count,
        'search':                    search,
        'date_from':                 date_from,
        'date_to':                   date_to,
        'department':                department,
        'status':                    status,
        'departments':               departments,
        'present_count':             present_count,
        'absent_count':              absent_count,
        'late_count':                late_count,
        'on_leave_count':            on_leave_count,
        'failed_to_clock_out_count': failed_to_clock_out_count,
        'overlunch_pending_count':   overlunch_pending_count,
        'missing_lunch_count':       missing_lunch_count,
        'pending_count':             pending_count,
    })


# ═════════════════════════════════════════════════════════════════════════════
# ATTENDANCE — EMPLOYEE CLOCK VIEW
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def attendance_clock(request):
    emp_num = request.session.get('employee_number')
    if not emp_num:
        return redirect('login')

    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')

    today     = date.today()
    now_local = timezone.localtime()
    now_time  = now_local.time()

    shift_rule = EmployeeShiftRule.objects.filter(
        shift=employee.shift, rank=employee.rank
    ).first()

    # ── Determine correct shift date ──────────────────────────────────────────
    # Night shifts that cross midnight are identified by clock_out being earlier
    # than clock_in_start (e.g. start=19:00, clock_out=02:00 next day).
    # If it is currently 01:00 on Mar 12 and still before clock_out,
    # the attendance record belongs to Mar 11 (yesterday).
    shift_date = today

    if shift_rule and shift_rule.clock_in_start and shift_rule.clock_out:
        crosses_midnight = shift_rule.clock_out < shift_rule.clock_in_start
        if crosses_midnight and now_time <= shift_rule.clock_out:
            shift_date = today - timedelta(days=1)

    current_year = shift_date.year

    # ── Check whether current time is inside the clock-in window ─────────────
    # Clock-in is allowed from clock_in_start until shift ends.
    clock_in_allowed = True  # default: allow when no shift rule configured
    if shift_rule and shift_rule.clock_in_start and shift_rule.clock_out:
        crosses_midnight = shift_rule.clock_out < shift_rule.clock_in_start
        if crosses_midnight:
            # Valid window spans midnight: clock_in_start → 23:59 → 00:00 → clock_out
            clock_in_allowed = (
                now_time >= shift_rule.clock_in_start or
                now_time <= shift_rule.clock_out
            )
        else:
            clock_in_allowed = shift_rule.clock_in_start <= now_time <= shift_rule.clock_out

    # ── Fetch only — never auto-create on page load ───────────────────────────
    attendance = Attendance.objects.filter(employee=employee, date=shift_date).first()
    
    # ── Fallback: If no attendance found for shift_date, check if user already completed 
    # a shift today (clock_in AND clock_out exist). If not, look for any open attendance ─
    if not attendance:
        # First check: is there any attendance today where user already completed their shift?
        completed_today = Attendance.objects.filter(
            employee=employee,
            clock_in__isnull=False,
            clock_out__isnull=False,
            date=today
        ).first()
        
        if not completed_today:
            # No completed shift today, look for any open attendance (clocked in but not out)
            open_attendance = Attendance.objects.filter(
                employee=employee,
                clock_in__isnull=False,
                clock_out__isnull=True
            ).order_by('-date').first()
            
            if open_attendance:
                attendance = open_attendance
                shift_date = attendance.date

    # ── Shared context variables ──────────────────────────────────────────────
    shift_rule_incomplete = not shift_rule or not (
        shift_rule.clock_in_start and shift_rule.clock_out
    )

    leave_credits      = LeaveCredit.objects.filter(employee=employee)
    vl_credits_current = leave_credits.filter(leave_type='vl', year=current_year)
    sl_credits_current = leave_credits.filter(leave_type='sl', year=current_year)
    vl_credits_old     = leave_credits.filter(leave_type='vl', year__lt=current_year)
    sl_credits_old     = leave_credits.filter(leave_type='sl', year__lt=current_year)

    vl_credit = vl_credits_current.first()
    sl_credit = sl_credits_current.first()

    vl_old_unused_total = sum(c.remaining for c in vl_credits_old)
    sl_old_unused_total = sum(c.remaining for c in sl_credits_old)

    no_vl_credits = vl_credit is None
    no_sl_credits = sl_credit is None

    outdated_vl = vl_credits_old if (vl_credit and vl_credits_old.exists()) else LeaveCredit.objects.none()
    outdated_sl = sl_credits_old if (sl_credit and sl_credits_old.exists()) else LeaveCredit.objects.none()

    vl_low = vl_credit and vl_credit.remaining < 3
    sl_low = sl_credit and sl_credit.remaining < 3

    absent_count = Attendance.objects.filter(employee=employee).filter(
        Q(statuses__contains='absent') | Q(status='absent')
    ).count()

    failed_to_clock_out_records = Attendance.objects.filter(
        employee=employee,
        clock_in__isnull=False,
        clock_out__isnull=True,
    ).filter(
        Q(statuses__contains='failed_to_clock_out') | Q(status='failed_to_clock_out')
    ).order_by('-date')

    def _build_context():
        return {
            'attendance':                  attendance,
            'employee':                    employee,
            'shift_rule':                  shift_rule,
            'history':                     Attendance.objects.filter(employee=employee).order_by('-date'),
            'shift_rule_incomplete':       shift_rule_incomplete,
            'vl_credit':                   vl_credit,
            'sl_credit':                   sl_credit,
            'no_vl_credits':               no_vl_credits,
            'no_sl_credits':               no_sl_credits,
            'outdated_vl':                 outdated_vl,
            'outdated_sl':                 outdated_sl,
            'vl_low':                      vl_low,
            'sl_low':                      sl_low,
            'vl_old_unused_total':         vl_old_unused_total,
            'sl_old_unused_total':         sl_old_unused_total,
            'current_year':                current_year,
            'absent_count':                absent_count,
            'today':                       today,
            'shift_date':                  shift_date,
            'clock_in_allowed':            clock_in_allowed,
            'failed_to_clock_out_records': failed_to_clock_out_records,
            # Added missing context variables for template
            'is_weekend':                  today.weekday() >= 5,  # Saturday=5, Sunday=6
            'no_shift_rule':               shift_rule is None,
        }

    # ── Auto-flag failed_to_clock_out if shift has ended ─────────────────────
    # Only apply to records from PREVIOUS days, not today's active attendance
    if attendance and attendance.clock_in and not attendance.clock_out:
        if shift_rule and shift_rule.clock_out:
            # Only flag as failed_to_clock_out if this is NOT today's attendance
            if attendance.date and attendance.date != today:
                # Calculate deadline using grace period (clock_out + grace_period)
                grace_period = getattr(shift_rule, 'clock_out_grace_period', 60)  # Default 60 minutes
                clock_out_dt = datetime.combine(attendance.date, shift_rule.clock_out)
                deadline_dt = clock_out_dt + timedelta(minutes=grace_period)
                deadline_time = deadline_dt.time()
                
                if now_time > deadline_time:
                    attendance.add_status('failed_to_clock_out')
                    if 'failed_to_clock_out' not in (attendance.status or ''):
                        attendance.status = 'failed_to_clock_out'
                    attendance.save()

    # ── AJAX/HTMX Support ───────────────────────────────────────────────────────
    def _is_ajax():
        return request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    def _is_htmx():
        return request.headers.get('HX-Request') == 'true'

    def _get_attendance_json(att):
        """Convert attendance object to JSON-serializable dict"""
        if not att:
            return None
        return {
            'clock_in': att.clock_in.strftime('%H:%M:%S') if att.clock_in else None,
            'clock_out': att.clock_out.strftime('%H:%M:%S') if att.clock_out else None,
            'lunch_in': att.lunch_in.strftime('%H:%M:%S') if att.lunch_in else None,
            'lunch_out': att.lunch_out.strftime('%H:%M:%S') if att.lunch_out else None,
            'status': att.status,
            'statuses': att.statuses,
            'date': att.date.strftime('%Y-%m-%d') if att.date else None,
            'hours_worked': float(att.hours_worked) if att.hours_worked else 0,
            'late_minutes': att.late_minutes or 0,
            'deduction_minutes': att.deduction_minutes or 0,
        }

    def _render_response(context, is_post=False, action=None, success_msg=None, error_msg=None):
        """Return JSON for AJAX/HTMX requests, HTML for regular requests"""
        # Return JSON for both AJAX and HTMX requests so JavaScript can handle toast messages
        if _is_ajax() or _is_htmx():
            messages_list = []
            storage = messages.get_messages(request)
            for msg in storage:
                messages_list.append({'level': msg.level, 'message': str(msg)})
            
            response_data = {
                'success': error_msg is None,
                'message': success_msg or error_msg,
                'messages': messages_list,
                'attendance': _get_attendance_json(context.get('attendance')),
                'clock_in_allowed': context.get('clock_in_allowed'),
                'redirect': '/human_resource/attendance/clock/' if is_post else None,
            }
            # For initial page load on POST, include action that was performed
            if is_post and action:
                response_data['action'] = action
            return JsonResponse(response_data)
        else:
            return render(request, 'hr/default/attendance/attendance_clock.html', context)

    # ── POST ──────────────────────────────────────────────────────────────────
    if request.method == 'POST':
        # Handle both JSON (from HTMX hx-vals) and form-encoded data
        action = None
        if _is_htmx():
            # Try to parse JSON from request body (hx-vals sends JSON)
            try:
                import json
                data = json.loads(request.body)
                action = data.get('action')
            except (json.JSONDecodeError, TypeError):
                action = request.POST.get('action')
        else:
            action = request.POST.get('action')

        if action == 'clock_in':
            # Allow clock-in at any time (removed restriction for early clock-in)
            # Employees can clock in anytime before or after shift start
            if not attendance:
                attendance = Attendance.objects.create(
                    employee=employee,
                    date=shift_date,
                    status='present',
                    statuses='present',
                )
            attendance.clock_in = now_time

        elif action == 'clock_out':
            if not attendance:
                error_msg = "No attendance record found. Please clock in first."
                return _render_response(_build_context(), is_post=True, action='clock_out', error_msg=error_msg)
            attendance.clock_out = now_time

            # Clear failed_to_clock_out now that they've properly clocked out
            current_statuses = attendance.get_statuses_list()
            if 'failed_to_clock_out' in current_statuses:
                current_statuses.remove('failed_to_clock_out')
                attendance.set_statuses(current_statuses)
                if not current_statuses:
                    attendance.status = 'present'
                elif 'late' in current_statuses:
                    attendance.status = 'late'
                else:
                    attendance.status = current_statuses[0]

            # Calculate hours worked, late/overlunch/deduction minutes
            if shift_rule and attendance.clock_in:
                from datetime import datetime as dt

                ci_dt = dt.combine(attendance.date, attendance.clock_in)
                co_dt = dt.combine(attendance.date, attendance.clock_out)

                # If clock_out time is earlier than clock_in, the shift crossed midnight
                if attendance.clock_out < attendance.clock_in:
                    co_dt += timedelta(days=1)

                if attendance.lunch_in and attendance.lunch_out:
                    lunch_secs = (
                        dt.combine(attendance.date, attendance.lunch_out)
                        - dt.combine(attendance.date, attendance.lunch_in)
                    ).total_seconds()
                    work_hours = (co_dt - ci_dt).total_seconds() / 3600 - lunch_secs / 3600
                    lunch_mins = lunch_secs / 60
                    attendance.overlunch_minutes = max(0, int(lunch_mins - 60))
                else:
                    work_hours = (co_dt - ci_dt).total_seconds() / 3600
                    attendance.overlunch_minutes = 0

                attendance.hours_worked = max(0, round(work_hours, 2))

                if shift_rule.clock_in_start and attendance.clock_in > shift_rule.clock_in_start:
                    late_grace = getattr(shift_rule, 'late_grace_period', 0) or 0
                    late_secs  = (
                        dt.combine(attendance.date, attendance.clock_in)
                        - dt.combine(attendance.date, shift_rule.clock_in_start)
                    ).total_seconds()
                    attendance.late_minutes = max(0, int(late_secs / 60 - late_grace))
                else:
                    attendance.late_minutes = 0

                deduction = attendance.late_minutes
                if not attendance.overlunch_validated:
                    deduction += attendance.overlunch_minutes
                attendance.deduction_minutes = deduction

        elif action == 'lunch_in':
            if attendance:
                attendance.lunch_in = now_time

        elif action == 'lunch_out':
            if attendance:
                attendance.lunch_out = now_time

        # ── Recalculate present/late/absent status after every action ─────────
        if attendance:
            if shift_rule:
                if attendance.clock_in:
                    if shift_rule.clock_in_start and attendance.clock_in > shift_rule.clock_in_start:
                        attendance.status = 'late'
                        attendance.set_statuses(['late'])
                    else:
                        attendance.status = 'present'
                        attendance.set_statuses(['present'])
                else:
                    attendance.status = 'absent'
                    attendance.set_statuses(['absent'])

                # Check for missing lunch (lunch required but no lunch_in)
                if shift_rule.lunch_required and not attendance.lunch_in:
                    attendance.add_status('missing_lunch')
                    if 'missing_lunch' not in (attendance.status or ''):
                        attendance.status += '/missing_lunch'
                
                # Check for overlunch (has lunch_in but no lunch_out)
                if shift_rule.lunch_required and attendance.lunch_in and not attendance.lunch_out:
                    attendance.add_status('overlunch_pending')
                    if 'overlunch_pending' not in (attendance.status or ''):
                        attendance.status += '/overlunch_pending'

                # Check for early_leave by comparing hours worked vs scheduled shift hours
                # Handle night shifts where clock_out is on the next day
                if attendance.clock_out and shift_rule and shift_rule.clock_out and shift_rule.clock_in_start:
                    from datetime import datetime as dt
                    
                    # Check if this is a night shift (clock_out < clock_in_start means crosses midnight)
                    is_night_shift = shift_rule.clock_out < shift_rule.clock_in_start
                    
                    # Calculate scheduled shift hours
                    if is_night_shift:
                        shift_hours = (dt.combine(attendance.date, shift_rule.clock_out) - dt.combine(attendance.date, shift_rule.clock_in_start)).total_seconds() / 3600
                        if shift_hours < 0:
                            shift_hours += 24 * 3600  # Add 24 hours in seconds
                    else:
                        shift_hours = (dt.combine(attendance.date, shift_rule.clock_out) - dt.combine(attendance.date, shift_rule.clock_in_start)).total_seconds() / 3600
                    
                    # Calculate actual hours worked (already computed above as work_hours)
                    # Use the already computed work_hours from line ~880
                    time_worked_hours = work_hours if 'work_hours' in locals() else 0
                    
                    # Early leave if worked less than scheduled hours (allow 1 minute grace)
                    grace_minutes = 1
                    if time_worked_hours > 0 and time_worked_hours < (shift_hours - (grace_minutes / 60)):
                        attendance.add_status('early_leave')
                        if 'early_leave' not in (attendance.status or ''):
                            attendance.status += '/early_leave'
            else:
                attendance.status = 'present' if attendance.clock_in else 'absent'
                attendance.set_statuses([attendance.status])

            attendance.save()

        # Determine success message based on action
        success_messages = {
            'clock_in': 'Clocked in successfully!',
            'clock_out': 'Clocked out successfully!',
            'lunch_in': 'Lunch break started!',
            'lunch_out': 'Lunch break ended!',
        }
        success_msg = success_messages.get(action, 'Action completed successfully!')
        
        return _render_response(_build_context(), is_post=True, action=action, success_msg=success_msg)

    # ── GET ───────────────────────────────────────────────────────────────────
    return _render_response(_build_context())


# ═════════════════════════════════════════════════════════════════════════════
# ATTENDANCE — ADD / EDIT (HR)
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def attendance_add(request):
    if request.method == 'POST':
        employee     = get_object_or_404(Staff, pk=request.POST.get('employee'))
        record_date  = request.POST.get('date')
        status_val   = request.POST.get('status', 'present')
        statuses_val = request.POST.getlist('statuses')
        clock_in     = request.POST.get('clock_in') or None
        clock_out    = request.POST.get('clock_out') or None
        lunch_in     = request.POST.get('lunch_in') or None
        lunch_out    = request.POST.get('lunch_out') or None
        note         = request.POST.get('note', '')
        overlunch_validated = request.POST.get('overlunch_validated') == '1'

        statuses_str = ','.join(statuses_val) if statuses_val else status_val

        Attendance.objects.update_or_create(
            employee=employee,
            date=record_date,
            defaults={
                'status':              status_val,
                'statuses':            statuses_str,
                'clock_in':            clock_in,
                'clock_out':           clock_out,
                'lunch_in':            lunch_in,
                'lunch_out':           lunch_out,
                'note':                note,
                'overlunch_validated': overlunch_validated,
            },
        )
        messages.success(request, 'Attendance record added.')
        return redirect('human_resource:attendance_list')

    return render(request, 'hr/default/attendance/attendance_form.html', {
        'action':             'Add',
        'employees':          Staff.objects.all().order_by('last_name', 'first_name'),
        'today':              date.today(),
        'clock_in_value':     '',
        'clock_out_value':    '',
        'lunch_in_value':     '',
        'lunch_out_value':    '',
        'shift_rule':         None,
        'attendance_history': Attendance.objects.all().order_by('-date')[:10],
    })


@login_required
def attendance_edit(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        status_val   = request.POST.get('status', attendance.status)
        statuses_val = request.POST.getlist('statuses')

        attendance.status   = status_val
        attendance.statuses = ','.join(statuses_val) if statuses_val else status_val
        attendance.clock_in  = request.POST.get('clock_in') or None
        attendance.clock_out = request.POST.get('clock_out') or None
        attendance.lunch_in  = request.POST.get('lunch_in') or None
        attendance.lunch_out = request.POST.get('lunch_out') or None
        attendance.note      = request.POST.get('note', '')
        attendance.overlunch_validated = request.POST.get('overlunch_validated') == '1'
        attendance.save()
        messages.success(request, 'Attendance record updated.')
        return redirect('human_resource:attendance_list')

    return render(request, 'hr/default/attendance/attendance_form.html', {
        'action':             'Edit',
        'attendance':         attendance,
        'employees':          Staff.objects.all().order_by('last_name', 'first_name'),
        'clock_in_value':     attendance.clock_in.strftime('%H:%M') if attendance.clock_in else '',
        'clock_out_value':    attendance.clock_out.strftime('%H:%M') if attendance.clock_out else '',
        'lunch_in_value':     attendance.lunch_in.strftime('%H:%M') if attendance.lunch_in else '',
        'lunch_out_value':    attendance.lunch_out.strftime('%H:%M') if attendance.lunch_out else '',
        'date_value':         str(attendance.date),
        'shift_rule':         EmployeeShiftRule.objects.filter(
                                  shift=attendance.employee.shift,
                                  rank=attendance.employee.rank,
                              ).first() if attendance.employee else None,
        'attendance_history': Attendance.objects.filter(
                                  employee=attendance.employee
                              ).order_by('-date')[:10] if attendance.employee else [],
    })


# ═════════════════════════════════════════════════════════════════════════════
# ATTENDANCE — AJAX ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def attendance_history_ajax(request):
    emp_num = request.session.get('employee_number')
    if not emp_num:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        return JsonResponse({'error': 'Employee not found'}, status=404)

    start_date = request.GET.get('start_date')
    end_date   = request.GET.get('end_date')

    queryset = Attendance.objects.filter(employee=employee).order_by('-date')
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    history_list = []
    for record in queryset:
        statuses_list = record.get_statuses_list() if record.statuses else []
        history_list.append({
            'id':           record.id,
            'date':         str(record.date),
            'clock_in':     record.clock_in.strftime('%H:%M') if record.clock_in else None,
            'clock_out':    record.clock_out.strftime('%H:%M') if record.clock_out else None,
            'status':       record.status,
            'statuses':     statuses_list,
            'late_minutes': record.late_minutes,
            'hours_worked': float(record.hours_worked) if record.hours_worked else 0,
            'lunch_in':     record.lunch_in.strftime('%H:%M') if record.lunch_in else None,
            'lunch_out':    record.lunch_out.strftime('%H:%M') if record.lunch_out else None,
        })

    return JsonResponse({'history': history_list})


@login_required
def get_absent_records_ajax(request):
    emp_num = request.session.get('employee_number')
    if not emp_num:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        return JsonResponse({'error': 'Employee not found'}, status=404)

    absent_records = Attendance.objects.filter(
        employee=employee,
    ).filter(
        Q(statuses__contains='absent') | Q(status='absent')
    ).order_by('-date')

    absent_list = []
    for record in absent_records:
        is_appealed = bool(record.note and 'appeal' in record.note.lower())
        absent_list.append({
            'id':           record.id,
            'date':         str(record.date),
            'date_display': record.date.strftime('%B %d, %Y'),
            'status':       record.status,
            'note':         record.note or '',
            'is_appealed':  is_appealed,
        })

    return JsonResponse({'absent_records': absent_list})


@login_required
def hr_mark_absent(request):
    from datetime import date, datetime
    from django.contrib import messages
    from App.users.models import Staff
    from App.human_resource.models import Attendance
    
    if request.method == 'POST':
        target_date = request.POST.get('date')
        selected_employees = request.POST.getlist('employees')
        bulk_action = request.POST.get('bulk_action')
        
        if not target_date:
            messages.error(request, 'Please select a date.')
            return redirect('human_resource:hr_mark_absent')
        
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('human_resource:hr_mark_absent')
        
        # If bulk action, mark all employees without attendance
        if bulk_action:
            active_employees = Staff.objects.filter(status='active')
            existing_attendance = Attendance.objects.filter(date=target_date)
            existing_employee_ids = set(existing_attendance.values_list('employee_id', flat=True))
            
            absent_count = 0
            for employee in active_employees:
                if employee.id not in existing_employee_ids:
                    Attendance.objects.create(
                        employee=employee,
                        date=target_date,
                        status='absent'
                    )
                    absent_count += 1
            
            messages.success(request, f'Successfully marked {absent_count} employee(s) as absent for {target_date}.')
        elif selected_employees:
            # If specific employees are selected, mark only those
            absent_count = 0
            for emp_id in selected_employees:
                try:
                    employee = Staff.objects.get(id=emp_id)
                    # Check if already has attendance for this date
                    existing = Attendance.objects.filter(employee=employee, date=target_date).first()
                    if not existing:
                        Attendance.objects.create(
                            employee=employee,
                            date=target_date,
                            status='absent'
                        )
                        absent_count += 1
                except Staff.DoesNotExist:
                    continue
            
            messages.success(request, f'Successfully marked {absent_count} employee(s) as absent for {target_date}.')
        else:
            messages.error(request, 'Please select at least one employee or use "Mark ALL Employees Absent".')
        
        # Stay on the mark absent page after submission, preserving the date
        return redirect(f'{reverse("human_resource:hr_mark_absent")}?date={target_date.strftime("%Y-%m-%d")}')
    
    # Get today's employees with their attendance status for initial display
    from calendar import monthrange
    from django.utils import timezone
    
    # Check for date parameter in URL
    date_param = request.GET.get('date')
    if date_param:
        try:
            today = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            today = date.today()
    else:
        today = date.today()
    
    # Get all active employees for the employee list
    all_employees = Staff.objects.filter(status='active').order_by('last_name', 'first_name')
    
    # Get all attendance records for calendar events (no date limit - show all history)
    attendance_records = Attendance.objects.all().select_related('employee')
    attendance_dict = {att.employee_id: att for att in attendance_records}
    
    # Build calendar events for the month
    calendar_events = []
    for att in attendance_records:
        # Determine status and color
        if att.statuses:
            statuses_list = [s.strip() for s in att.statuses.split(',') if s.strip()]
            if statuses_list:
                status = statuses_list[0]
            else:
                status = att.status or 'present'
        else:
            status = att.status or 'present'
        
        # Set colors based on status
        if status == 'absent':
            bg_color = '#ef4444'
            border_color = '#dc2626'
        elif status == 'late':
            bg_color = '#eab308'
            border_color = '#ca8a04'
        elif status == 'on_leave':
            bg_color = '#3b82f6'
            border_color = '#2563eb'
        else:  # present
            bg_color = '#22c55e'
            border_color = '#16a34a'
        
        calendar_events.append({
            'id': att.id,
            'title': f"{att.employee.first_name} {att.employee.last_name}",
            'start': att.date.strftime('%Y-%m-%d'),
            'backgroundColor': bg_color,
            'borderColor': border_color,
            'extendedProps': {
                'employee_id': att.employee.id,
                'status': status,
                'clock_in': str(att.clock_in) if att.clock_in else None,
                'clock_out': str(att.clock_out) if att.clock_out else None,
            }
        })
    
    employees_data = []
    for emp in all_employees:
        attendance = attendance_dict.get(emp.id)
        
        if attendance:
            if attendance.statuses:
                statuses_list = [s.strip() for s in attendance.statuses.split(',') if s.strip()]
                if statuses_list:
                    status = statuses_list[0]
                    status_display = ', '.join([s.title() for s in statuses_list])
                else:
                    status = attendance.status or 'present'
                    status_display = status.title()
            else:
                status = attendance.status or 'present'
                status_display = status.title()
            
            clock_in = attendance.clock_in
        else:
            status = 'none'
            status_display = 'No Record'
            clock_in = None
        
        employees_data.append({
            'employee': emp,
            'status': status,
            'status_display': status_display,
            'clock_in': clock_in,
            'has_attendance': attendance is not None
        })
    
    return render(request, 'hr/default/attendance/mark_absent.html', {
        'today': today.strftime('%Y-%m-%d'),
        'employees': all_employees,
        'employees_data': employees_data,
        'calendar_events': calendar_events,
    })


@login_required
def get_employees_without_attendance_htmx(request):
    """HTMX endpoint to get employees with their attendance status for a specific date"""
    from datetime import datetime
    from App.users.models import Staff
    from App.human_resource.models import Attendance
    
    date_str = request.GET.get('date')
    if not date_str:
        return HttpResponse('')
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponse('')
    
    # Get all active employees
    all_employees = Staff.objects.filter(status='active').order_by('last_name', 'first_name')
    
    # Get attendance records for this specific date
    attendance_records = Attendance.objects.filter(date=target_date).select_related('employee')
    attendance_dict = {att.employee_id: att for att in attendance_records}
    
    employees_data = []
    for emp in all_employees:
        attendance = attendance_dict.get(emp.id)
        
        if attendance:
            # Employee has a record - use its status
            if attendance.statuses:
                # Has multiple statuses
                statuses_list = [s.strip() for s in attendance.statuses.split(',') if s.strip()]
                if statuses_list:
                    status = statuses_list[0]  # Primary status
                    status_display = ', '.join([s.title() for s in statuses_list])
                else:
                    status = attendance.status or 'present'
                    status_display = status.title()
            else:
                status = attendance.status or 'present'
                status_display = status.title()
            
            clock_in = attendance.clock_in
        else:
            # No record for this date
            status = 'none'
            status_display = 'No Record'
            clock_in = None
        
        employees_data.append({
            'employee': emp,
            'status': status,
            'status_display': status_display,
            'clock_in': clock_in,
            'has_attendance': attendance is not None
        })
    
    return render(request, 'hr/default/attendance/partials/employee_status_list.html', {
        'employees_data': employees_data,
    })


@login_required
def acknowledge_attendance(request, pk):
    from django.http import JsonResponse
    
    attendance = get_object_or_404(Attendance, pk=pk)

    if request.method == 'POST':
        note = request.POST.get('note', '').strip()
        if note:
            existing_note   = attendance.note or ''
            attendance.note = (
                existing_note + ('\n' if existing_note else '')
                + f"[Acknowledged - {date.today()}]: {note}"
            )
            statuses = attendance.get_statuses_list()
            if 'failed_to_clock_out' in statuses:
                statuses.remove('failed_to_clock_out')
                attendance.set_statuses(statuses)
            if not attendance.status or attendance.status == 'failed_to_clock_out':
                attendance.status = 'present'
            attendance.save()
            messages.success(request, 'Failed to clock out record acknowledged.')
            success_msg = 'Failed to clock out record acknowledged.'
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': success_msg})
        else:
            messages.error(request, 'Please provide a note for acknowledgement.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Please provide a note for acknowledgement.'})

    return redirect('human_resource:attendance_clock')


@login_required
def appeal_absent(request, pk):
    from django.http import JsonResponse
    
    attendance = get_object_or_404(Attendance, pk=pk)

    if request.method == 'POST':
        appeal_reason = request.POST.get('appeal_reason', '').strip()
        action_type   = request.POST.get('action_type', 'appeal')

        if appeal_reason:
            note_prefix   = (
                f"[HR Review Request - {date.today()}]: "
                if action_type == 'request_hr'
                else f"[Appeal - {date.today()}]: "
            )
            existing_note   = attendance.note or ''
            attendance.note = (
                existing_note + ('\n' if existing_note else '') + note_prefix + appeal_reason
            )
            attendance.save()
            messages.success(request, 'Your request has been submitted successfully.')
            success_msg = 'Your request has been submitted successfully.'
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': success_msg})
        else:
            messages.error(request, 'Please provide a reason for your appeal/request.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Please provide a reason for your appeal/request.'})

    return redirect('human_resource:attendance_clock')


# ═════════════════════════════════════════════════════════════════════════════
# SHIFT RULES
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def hr_shift_rules_list(request):
    for shift, _ in Staff.SHIFT_CHOICES:
        for rank, _ in Staff.RANK_CHOICES:
            EmployeeShiftRule.objects.get_or_create(shift=shift, rank=rank)

    rules = EmployeeShiftRule.objects.all().order_by('shift', 'rank')

    # Calculate shift counts for the stats cards
    morning_count = rules.filter(shift='morning').count()
    afternoon_count = rules.filter(shift='afternoon').count()
    night_count = rules.filter(shift='night').count()

    if request.method == 'POST':
        for rule in rules:
            ci_start = request.POST.get(f'clock_in_start_{rule.id}')
            co       = request.POST.get(f'clock_out_{rule.id}')
            if ci_start and co:
                try:
                    rule.clock_in_start = datetime.strptime(ci_start, '%H:%M').time()
                    rule.clock_out      = datetime.strptime(co,       '%H:%M').time()
                    rule.save()
                except ValueError:
                    messages.error(request, f'Invalid time format for {rule}')
        messages.success(request, 'Shift rules updated successfully!')
        return redirect('human_resource:hr_shift_rules_list')

    return render(request, 'hr/default/shift_rules/shift_rules_list.html', {
        'rules': rules,
        'morning_count': morning_count,
        'afternoon_count': afternoon_count,
        'night_count': night_count,
    })


@login_required
def hr_shift_rule_add(request):        return redirect('human_resource:hr_shift_rules_list')
@login_required
def hr_shift_rule_edit(request, pk):   return redirect('human_resource:hr_shift_rules_list')
@login_required
def hr_shift_rule_delete(request, pk): return redirect('human_resource:hr_shift_rules_list')


# ═════════════════════════════════════════════════════════════════════════════
# LEAVE CREDIT
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def leave_credit_list(request):
    query             = request.GET.get('q', '')
    selected_year     = request.GET.get('year', '')
    leave_type_filter = request.GET.get('leave_type', '')
    status_filter     = request.GET.get('status', '')
    sort              = request.GET.get('sort', 'year')

    all_credits_base = LeaveCredit.objects.select_related('employee')

    available_years = sorted(set(
        LeaveCredit.objects.values_list('year', flat=True).distinct()
    ), reverse=True)
    if not available_years:
        available_years = [date.today().year]

    all_credits = all_credits_base
    if selected_year:
        all_credits = all_credits.filter(year=int(selected_year))
    if leave_type_filter:
        all_credits = all_credits.filter(leave_type=leave_type_filter)

    vl_credits = all_credits.filter(leave_type='vl')
    sl_credits = all_credits.filter(leave_type='sl')
    total_vl_remaining = sum((c.total - c.used) for c in vl_credits)
    total_sl_remaining = sum((c.total - c.used) for c in sl_credits)

    low_credits_list  = [c for c in all_credits if 0 < (c.total - c.used) <= 2]
    low_credits_count = len(low_credits_list)
    zero_credits_list = [c for c in all_credits if (c.total - c.used) <= 0]

    credits = LeaveCredit.objects.select_related('employee')
    if query:
        query_words = query.split()
        q_objects   = Q()
        for word in query_words:
            q_objects &= Q(
                Q(employee__first_name__icontains=word) |
                Q(employee__last_name__icontains=word)
            )
        credits = credits.filter(q_objects)
    if selected_year:
        credits = credits.filter(year=int(selected_year))
    if leave_type_filter:
        credits = credits.filter(leave_type=leave_type_filter)

    if status_filter == 'low':
        credits = [c for c in credits if 0 < (c.total - c.used) <= 2]
    elif status_filter == 'zero':
        credits = [c for c in credits if (c.total - c.used) <= 0]
    elif status_filter == 'healthy':
        credits = [c for c in credits if (c.total - c.used) > 2]

    allowed_sorts = ['year', '-year', 'leave_type', '-leave_type', 'employee', '-employee']

    if isinstance(credits, list):
        sort_map = {
            'year':        lambda x: x.year,
            '-year':       lambda x: x.year,
            'leave_type':  lambda x: x.leave_type,
            '-leave_type': lambda x: x.leave_type,
            'employee':    lambda x: f"{x.employee.first_name} {x.employee.last_name}",
            '-employee':   lambda x: f"{x.employee.first_name} {x.employee.last_name}",
        }
        reverse = sort.startswith('-')
        credits = sorted(credits, key=sort_map.get(sort, lambda x: x.year), reverse=reverse)
    else:
        if sort in ('employee', '-employee'):
            credits = credits.annotate(
                full_name=Concat(
                    F('employee__first_name'), Value(' '), F('employee__last_name'),
                    output_field=CharField(),
                )
            ).order_by('full_name' if sort == 'employee' else '-full_name')
        elif sort in allowed_sorts:
            credits = credits.order_by(sort)
        else:
            credits = credits.order_by('year')

    paginator = Paginator(credits, 10)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'hr/default/leave/leave_credit_list.html', {
        'leave_credits':      page_obj,
        'query':              query,
        'sort':               sort,
        'selected_year':      selected_year,
        'available_years':    available_years,
        'total_vl_remaining': total_vl_remaining,
        'total_sl_remaining': total_sl_remaining,
        'low_credits':        low_credits_list,
        'low_credits_count':  low_credits_count,
        'zero_credits':       zero_credits_list,
    })


@login_required
def leave_credit_add(request):
    if request.method == 'POST':
        form = LeaveCreditForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('human_resource:leave_credit_list')
    else:
        form = LeaveCreditForm()
    return render(request, 'hr/default/leave/leave_credit_form.html', {
        'form': form, 'leave_credit': None,
    })


@login_required
def leave_credit_edit(request, pk):
    credit = get_object_or_404(LeaveCredit, pk=pk)
    if request.method == 'POST':
        form = LeaveCreditForm(request.POST, instance=credit)
        if form.is_valid():
            form.save()
            return redirect('human_resource:leave_credit_list')
    else:
        form = LeaveCreditForm(instance=credit)
    return render(request, 'hr/default/leave/leave_credit_form.html', {
        'form': form, 'leave_credit': credit,
    })


# ═════════════════════════════════════════════════════════════════════════════
# EMPLOYEE INFO — AJAX helpers
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def get_employee_rank(request):
    emp_id = request.GET.get('employee_id')
    if emp_id:
        try:
            emp = Staff.objects.get(id=emp_id)
            return JsonResponse({'rank': emp.get_rank_display()})
        except Staff.DoesNotExist:
            return JsonResponse({'rank': 'Not found'})
    return JsonResponse({'rank': ''})


@login_required
def get_employee_info(request):
    emp_id = request.GET.get('employee_id')
    if not emp_id:
        return JsonResponse({
            'success': False, 'rank': '', 'department': '',
            'vl_remaining': 0, 'sl_remaining': 0,
            'vl_percentage': 0, 'sl_percentage': 0,
        })
    try:
        emp  = Staff.objects.get(pk=emp_id)
        dept = getattr(emp, 'department', '') or ''
        try:
            rank_label = emp.get_rank_display()
        except Exception:
            rank_label = getattr(emp, 'rank', '') or ''

        current_year = date.today().year
        vl_remaining = sl_remaining = vl_total = sl_total = 0

        try:
            vl_credit = LeaveCredit.objects.filter(employee=emp, leave_type='vl', year=current_year).first()
            sl_credit = LeaveCredit.objects.filter(employee=emp, leave_type='sl', year=current_year).first()
            if vl_credit:
                vl_total     = float(vl_credit.total or 0)
                vl_remaining = max(0, vl_total - float(vl_credit.used or 0))
            if sl_credit:
                sl_total     = float(sl_credit.total or 0)
                sl_remaining = max(0, sl_total - float(sl_credit.used or 0))
        except Exception:
            pass

        return JsonResponse({
            'success':       True,
            'rank':          rank_label,
            'department':    dept,
            'vl_remaining':  vl_remaining,
            'sl_remaining':  sl_remaining,
            'vl_percentage': round((vl_remaining / vl_total * 100) if vl_total > 0 else 0, 1),
            'sl_percentage': round((sl_remaining / sl_total * 100) if sl_total > 0 else 0, 1),
        })
    except Staff.DoesNotExist:
        return JsonResponse({
            'success': False, 'rank': '', 'department': '',
            'vl_remaining': 0, 'sl_remaining': 0,
            'vl_percentage': 0, 'sl_percentage': 0,
        })


# ═════════════════════════════════════════════════════════════════════════════
# LEAVE REQUEST — LIST
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def leave_request_list(request):
    search              = request.GET.get('search', '').strip()
    employee_id         = request.GET.get('employee')
    leave_type_filter   = request.GET.get('leave_type')
    status_filter       = request.GET.get('status_filter')
    credits_year_filter = request.GET.get('credits_year', str(date.today().year))
    sort                = request.GET.get('sort', '-date_filed')

    allowed_sorts = [
        'date_filed', '-date_filed', 'created_at', '-created_at',
        'status', '-status', 'leave_type', '-leave_type',
        'employee__first_name', '-employee__first_name',
        'employee__last_name',  '-employee__last_name',
    ]
    if sort not in allowed_sorts:
        sort = '-date_filed'

    qs = LeaveRequest.objects.select_related('employee')
    if search:
        qs = qs.filter(
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search)  |
            Q(leave_type__icontains=search)            |
            Q(status__icontains=search)
        )
    if employee_id:
        qs = qs.filter(employee__id=employee_id)
    if leave_type_filter:
        qs = qs.filter(leave_type=leave_type_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)

    qs = qs.order_by(sort)

    pending_count     = qs.filter(status='pending').count()
    approved_count    = qs.filter(status='approved').count()
    disapproved_count = qs.filter(status='disapproved').count()

    paginator = Paginator(qs, 10)
    page_obj  = paginator.get_page(request.GET.get('page'))

    employee_ids = [req.employee.id for req in page_obj]
    credit_dict  = {}
    for c in LeaveCredit.objects.filter(employee__id__in=employee_ids, year=credits_year_filter):
        credit_dict.setdefault(c.employee_id, {})[c.leave_type] = {
            'used':      float(c.used),
            'total':     float(c.total),
            'remaining': float(c.total) - float(c.used),
        }

    return render(request, 'hr/default/leave/leave_request_list.html', {
        'leave_requests':      page_obj,
        'search':              search,
        'employee_id':         employee_id,
        'leave_type_filter':   leave_type_filter,
        'status_filter':       status_filter,
        'credits_year_filter': credits_year_filter,
        'sort':                sort,
        'leave_credits':       credit_dict,
        'pending_count':       pending_count,
        'approved_count':      approved_count,
        'disapproved_count':   disapproved_count,
    })


@login_required
def leave_request_list_ajax(request):
    search              = request.GET.get('search', '').strip()
    employee_id         = request.GET.get('employee')
    leave_type_filter   = request.GET.get('leave_type')
    status_filter       = request.GET.get('status_filter')
    credits_year_filter = request.GET.get('credits_year', str(date.today().year))
    sort                = request.GET.get('sort', '-date_filed')
    page                = int(request.GET.get('page', 1))

    allowed_sorts = [
        'date_filed', '-date_filed', 'created_at', '-created_at',
        'status', '-status', 'leave_type', '-leave_type',
        'employee__first_name', '-employee__first_name',
        'employee__last_name',  '-employee__last_name',
    ]
    if sort not in allowed_sorts:
        sort = '-date_filed'

    qs = LeaveRequest.objects.select_related('employee')
    if search:
        qs = qs.filter(
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search)  |
            Q(leave_type__icontains=search)            |
            Q(status__icontains=search)
        )
    if employee_id:
        qs = qs.filter(employee__id=employee_id)
    if leave_type_filter:
        qs = qs.filter(leave_type=leave_type_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)

    qs = qs.order_by(sort)

    pending_count     = qs.filter(status='pending').count()
    approved_count    = qs.filter(status='approved').count()
    disapproved_count = qs.filter(status='disapproved').count()

    paginator = Paginator(qs, 10)
    page_obj  = paginator.get_page(page)

    requests_list = []
    for req in page_obj:
        emp = req.employee
        requests_list.append({
            'id': req.id,
            'employee': {
                'id':         emp.id,
                'first_name': emp.first_name,
                'last_name':  emp.last_name,
                'initials':   (emp.first_name[0] if emp.first_name else '') + (emp.last_name[0] if emp.last_name else ''),
                'position':   getattr(getattr(emp, 'positionlink', None), 'position_name', '-') or '-',
                'department': getattr(getattr(emp, 'departmentlink', None), 'department_name', '-') or '-',
            },
            'total_days':         float(req.total_days) if req.total_days else 0,
            'leave_type':         req.leave_type,
            'leave_type_display': req.get_leave_type_display(),
            'status':             req.status,
            'date_filed':         req.date_filed.strftime('%Y-%m-%d') if req.date_filed else '',
            'start_date':         req.start_date.strftime('%Y-%m-%d') if req.start_date else '',
            'end_date':           req.end_date.strftime('%Y-%m-%d') if req.end_date else '',
        })

    return JsonResponse({
        'success':  True,
        'requests': requests_list,
        'pagination': {
            'has_previous': page_obj.has_previous(),
            'has_next':     page_obj.has_next(),
            'number':       page_obj.number,
            'paginator':    {'num_pages': paginator.num_pages},
        },
        'counts': {
            'total':       pending_count + approved_count + disapproved_count,
            'pending':     pending_count,
            'approved':    approved_count,
            'disapproved': disapproved_count,
        },
    })


# ═════════════════════════════════════════════════════════════════════════════
# LEAVE REQUEST — ADD
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def leave_request_add(request):
    employee_id = request.GET.get('employee')
    employees   = Staff.objects.filter(status='active').order_by('last_name', 'first_name')

    if not employees.exists():
        messages.error(request, "No active employees found. Please add employees first.")
        return redirect('human_resource:leave_request_list')

    if not employee_id:
        employee_id = request.POST.get('employee')
        if not employee_id:
            form = LeaveRequestForm()
            return render(request, 'hr/default/leave/leave_request_form.html', {
                'form': form, 'employees': employees,
            })

    employee = get_object_or_404(Staff, pk=employee_id)

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    lr            = form.save(commit=False)
                    lr.position   = form.cleaned_data.get('position', '')
                    lr.department = form.cleaned_data.get('department', '')
                    lr.employee   = employee
                    lr.save()

                    if lr.status == 'approved':
                        credits = LeaveCredit.objects.filter(
                            employee=employee,
                            leave_type=lr.leave_type,
                            year=date.today().year,
                        )
                        credit = credits.first() if credits.exists() else LeaveCredit.objects.create(
                            employee=employee,
                            leave_type=lr.leave_type,
                            year=date.today().year,
                            total=Decimal('0.0'),
                            used=Decimal('0.0'),
                        )
                        credit.used += Decimal(str(lr.total_days or 0))
                        credit.save()
                        create_attendance_from_leave(lr)

                    messages.success(request, 'Leave request saved.')
                    return redirect('human_resource:leave_request_list')
            except Exception as e:
                messages.error(request, f'Error saving leave request: {e}')
        else:
            messages.error(request, 'Please correct the errors below.')

        return render(request, 'hr/default/leave/leave_request_form.html', {
            'form': form, 'employees': employees,
        })

    form = LeaveRequestForm(initial={'employee': employee})
    return render(request, 'hr/default/leave/leave_request_form.html', {
        'form': form, 'employees': employees,
    })


# ═════════════════════════════════════════════════════════════════════════════
# LEAVE REQUEST — EDIT
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def leave_request_edit(request, pk):
    lr         = get_object_or_404(LeaveRequest, pk=pk)
    employee   = lr.employee
    old_status = lr.status
    old_total  = Decimal(str(lr.total_days or 0))

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, instance=lr)
        if form.is_valid():
            try:
                with transaction.atomic():
                    updated            = form.save(commit=False)
                    updated.position   = form.cleaned_data.get('position', '')
                    updated.department = form.cleaned_data.get('department', '')
                    updated.save()

                    credit = LeaveCredit.objects.filter(
                        employee=updated.employee,
                        leave_type=updated.leave_type,
                        year=date.today().year,
                    ).first()
                    if credit is None:
                        credit = LeaveCredit.objects.create(
                            employee=updated.employee,
                            leave_type=updated.leave_type,
                            year=date.today().year,
                            total=Decimal('0.0'),
                            used=Decimal('0.0'),
                        )

                    updated_total = Decimal(str(updated.total_days or 0))

                    if old_status != 'approved' and updated.status == 'approved':
                        credit.used += updated_total
                        create_attendance_from_leave(updated)

                    elif old_status == 'approved' and updated.status != 'approved':
                        credit.used = max(Decimal('0.0'), credit.used - old_total)
                        remove_attendance_for_leave(updated)

                    elif old_status == 'approved' and updated.status == 'approved':
                        remove_attendance_for_leave(updated)
                        create_attendance_from_leave(updated)
                        diff = updated_total - old_total
                        credit.used = max(Decimal('0.0'), credit.used + diff)

                    credit.save()
                    messages.success(request, 'Leave request updated.')
                    return redirect('human_resource:leave_request_list')
            except Exception as e:
                messages.error(request, f'Error updating leave request: {e}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LeaveRequestForm(instance=lr)

    employees    = Staff.objects.filter(status='active').order_by('last_name', 'first_name')
    current_year = date.today().year

    try:
        vl_credit     = LeaveCredit.objects.filter(employee=employee, leave_type='vl', year=current_year).first()
        vl_remaining  = float(vl_credit.total - vl_credit.used) if vl_credit else 0
        vl_percentage = min(100, (vl_remaining / float(vl_credit.total)) * 100) if (vl_credit and vl_credit.total > 0) else 0
    except Exception:
        vl_remaining = vl_percentage = 0

    try:
        sl_credit     = LeaveCredit.objects.filter(employee=employee, leave_type='sl', year=current_year).first()
        sl_remaining  = float(sl_credit.total - sl_credit.used) if sl_credit else 0
        sl_percentage = min(100, (sl_remaining / float(sl_credit.total)) * 100) if (sl_credit and sl_credit.total > 0) else 0
    except Exception:
        sl_remaining = sl_percentage = 0

    return render(request, 'hr/default/leave/leave_request_form.html', {
        'form':          form,
        'employees':     employees,
        'employee':      employee,
        'vl_remaining':  vl_remaining,
        'sl_remaining':  sl_remaining,
        'vl_percentage': vl_percentage,
        'sl_percentage': sl_percentage,
    })


# ═════════════════════════════════════════════════════════════════════════════
# LEAVE REQUEST — QUICK STATUS (AJAX dropdown)
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def leave_request_quick_status(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        leave_request = get_object_or_404(LeaveRequest, pk=pk)
        new_status    = request.POST.get('status')

        if new_status not in ('pending', 'approved', 'disapproved'):
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

        old_status = leave_request.status
        old_total  = Decimal(str(leave_request.total_days or 0))

        with transaction.atomic():
            leave_request.status = new_status
            leave_request.save()

            if new_status == 'approved' and old_status != 'approved':
                credits = LeaveCredit.objects.filter(
                    employee=leave_request.employee,
                    leave_type=leave_request.leave_type,
                    year=date.today().year,
                )
                credit = credits.first() if credits.exists() else LeaveCredit.objects.create(
                    employee=leave_request.employee,
                    leave_type=leave_request.leave_type,
                    year=date.today().year,
                    total=Decimal('0.0'),
                    used=Decimal('0.0'),
                )
                credit.used += old_total
                credit.save()
                create_attendance_from_leave(leave_request)

            elif old_status == 'approved' and new_status != 'approved':
                credit = LeaveCredit.objects.filter(
                    employee=leave_request.employee,
                    leave_type=leave_request.leave_type,
                    year=date.today().year,
                ).first()
                if credit:
                    credit.used = max(Decimal('0.0'), credit.used - old_total)
                    credit.save()
                remove_attendance_for_leave(leave_request)

        return JsonResponse({
            'success':    True,
            'new_status': new_status,
            'message':    f'Status updated to {new_status}',
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ═════════════════════════════════════════════════════════════════════════════
# POSITION & DEPARTMENT — stubs
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def position_list(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        positions = Position.objects.all().order_by('position_name')
        return render(request, 'hr/default/position/position_list.html', {'positions': positions, 'employee': None, 'is_owner': True})
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to view position management.")
        return redirect('human_resource:hr_dashboard')
    positions = Position.objects.all().order_by('position_name')
    return render(request, 'hr/default/position/position_list.html', {'positions': positions, 'employee': employee})


@login_required
def position_add(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        if request.method == 'POST':
            form = PositionForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Position added successfully.')
                return redirect('human_resource:position_list')
        else:
            form = PositionForm()
        return render(request, 'hr/default/position/position_form.html', {'form': form, 'action': 'Add', 'employee': None, 'is_owner': True})
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to add positions.")
        return redirect('human_resource:hr_dashboard')
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Position added successfully.')
            return redirect('human_resource:position_list')
    else:
        form = PositionForm()
    return render(request, 'hr/default/position/position_form.html', {'form': form, 'action': 'Add', 'employee': employee})


@login_required
def position_edit(request, pk):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        position = get_object_or_404(Position, pk=pk)
        if request.method == 'POST':
            form = PositionForm(request.POST, instance=position)
            if form.is_valid():
                form.save()
                messages.success(request, 'Position updated successfully.')
                return redirect('human_resource:position_list')
        else:
            form = PositionForm(instance=position)
        return render(request, 'hr/default/position/position_form.html', {
            'form': form, 'action': 'Edit', 'employee': None, 'position': position, 'is_owner': True
        })
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to edit positions.")
        return redirect('human_resource:hr_dashboard')
    position = get_object_or_404(Position, pk=pk)
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            messages.success(request, 'Position updated successfully.')
            return redirect('human_resource:position_list')
    else:
        form = PositionForm(instance=position)
    return render(request, 'hr/default/position/position_form.html', {
        'form': form, 'action': 'Edit', 'employee': employee, 'position': position
    })


@login_required
def position_delete(request, pk):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        position = get_object_or_404(Position, pk=pk)
        if request.method == 'POST':
            position.delete()
            messages.success(request, 'Position deleted successfully.')
            return redirect('human_resource:position_list')
        return render(request, 'hr/default/position/position_confirm_delete.html', {
            'position': position, 'employee': None, 'is_owner': True
        })
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to delete positions.")
        return redirect('human_resource:hr_dashboard')
    position = get_object_or_404(Position, pk=pk)
    if request.method == 'POST':
        position.delete()
        messages.success(request, 'Position deleted successfully.')
        return redirect('human_resource:position_list')
    return render(request, 'hr/default/position/position_confirm_delete.html', {
        'position': position, 'employee': employee
    })

@login_required
def department_list(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        departments = Department.objects.all().order_by('department_name')
        return render(request, 'hr/default/department/department_list.html', {'departments': departments, 'employee': None, 'is_owner': True})
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to view department management.")
        return redirect('human_resource:hr_dashboard')
    departments = Department.objects.all().order_by('department_name')
    return render(request, 'hr/default/department/department_list.html', {'departments': departments, 'employee': employee})


@login_required
def department_add(request):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        if request.method == 'POST':
            form = DepartmentForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Department added successfully.')
                return redirect('human_resource:department_list')
        else:
            form = DepartmentForm()
        return render(request, 'hr/default/department/department_form.html', {'form': form, 'action': 'Add', 'employee': None, 'is_owner': True})
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to add departments.")
        return redirect('human_resource:hr_dashboard')
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department added successfully.')
            return redirect('human_resource:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'hr/default/department/department_form.html', {'form': form, 'action': 'Add', 'employee': employee})


@login_required
def department_edit(request, pk):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        department = get_object_or_404(Department, pk=pk)
        if request.method == 'POST':
            form = DepartmentForm(request.POST, instance=department)
            if form.is_valid():
                form.save()
                messages.success(request, 'Department updated successfully.')
                return redirect('human_resource:department_list')
        else:
            form = DepartmentForm(instance=department)
        return render(request, 'hr/default/department/department_form.html', {
            'form': form, 'action': 'Edit', 'employee': None, 'department': department, 'is_owner': True
        })
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to edit departments.")
        return redirect('human_resource:hr_dashboard')
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully.')
            return redirect('human_resource:department_list')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'hr/default/department/department_form.html', {
        'form': form, 'action': 'Edit', 'employee': employee, 'department': department
    })


@login_required
def department_delete(request, pk):
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if not emp_num:
        return redirect('login')
    
    # Owner bypass - allow access without Staff record
    if is_owner:
        department = get_object_or_404(Department, pk=pk)
        if request.method == 'POST':
            department.delete()
            messages.success(request, 'Department deleted successfully.')
            return redirect('human_resource:department_list')
        return render(request, 'hr/default/department/department_confirm_delete.html', {
            'department': department, 'employee': None, 'is_owner': True
        })
    
    employee = Staff.objects.filter(employee_number=emp_num).first()
    if not employee:
        messages.error(request, "Your account could not be found. Please log in again.")
        return redirect('login')
    role_name = employee.role.role_name if employee.role else ''
    if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
        messages.error(request, "You don't have permission to delete departments.")
        return redirect('human_resource:hr_dashboard')
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully.')
        return redirect('human_resource:department_list')
    return render(request, 'hr/default/department/department_confirm_delete.html', {
        'department': department, 'employee': employee
    })
