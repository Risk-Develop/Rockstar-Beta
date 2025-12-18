from django.shortcuts import render
from users.models import Staff
from authentication.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q,F,Value, CharField

# human_resource/views.py (or wherever your views live)
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.http import JsonResponse

from users.models import Staff, Role  # adjust if models are elsewhere
from users.forms import StaffForm     # if using a form for add/edit

# in human_resource/views.py (or the file where update_staff_role lives)
from django.urls import reverse

#in human resourece by default->employees profile setting
from .models import EmployeeProfileSettings, Attendance

#Attendance
from .models import Attendance, EmployeeShiftRule,LeaveCredit,LeaveRequest
from datetime import date, time,datetime
from django.utils import timezone
from .forms import EmployeeShiftRuleForm,LeaveCreditForm,LeaveRequestForm
from django.contrib import messages
from django.db import transaction
from django.db.models.functions import Concat
from decimal import Decimal



# Create your views here.
@login_required


# ============================================
# HR DASHBOARD (MAIN PAGE)
# ============================================
def human_resource_dashboard(request):
    emp_num = request.session.get('employee_number')
    emp = Staff.objects.get(employee_number=emp_num)

    context = {
        "employee": emp,
        
    }

    return render(request, "hr/dashboard/hr_dashboard.html", context)


# ============================================
# USER MANAGEMENT — MAIN PAGE
# ============================================
def hr_user_mgnt(request):
    staff_list = Staff.objects.select_related("role").order_by("last_name", "first_name")
    roles = Role.objects.filter(is_active=True).order_by("role_name")

    return render(request, "hr/default/user_mgnt/hr_user_mgnt.html", {
        "staff_list": staff_list,
        "roles": roles,
    })


# ============================================
# UPDATE STAFF ROLE
# ============================================
def update_staff_role(request):
    if request.method == "POST":
        staff_id = request.POST.get("staff_id")
        role_id = request.POST.get("role")

        staff = get_object_or_404(Staff, id=staff_id)
        staff.role_id = role_id if role_id else None
        staff.save()

    return redirect(reverse("human_resource:hr_user_mgnt"))


# ============================================
# DELETE STAFF
# ============================================
def hr_user_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)

    if request.method == "POST":
        staff.delete()
        return redirect('human_resource:hr_user_mgnt')  # back to user management

    return render(request, 'hr/default/user_mgnt/hr_user_delete.html', {'staff': staff})


# ============================================
# STAFF DETAILS
# ============================================
def dashboard_user_detail(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    return render(request, 'hr/default/user_mgnt/hr_user_details.html', {'staff': staff})




# ============================================
# AJAX USER LIST (search + pagination)
# ============================================
def ajax_user_list(request):
    search = request.GET.get("search", "")
    role_filter = request.GET.get("role", "")
    page = request.GET.get("page", 1)

    staff_qs = Staff.objects.select_related('role').all()

    if search:
        staff_qs = staff_qs.filter(
            last_name__icontains=search
        ) | staff_qs.filter(first_name__icontains=search)

    if role_filter:
        staff_qs = staff_qs.filter(role_id=role_filter)

    staff_qs = staff_qs.order_by('last_name', 'first_name')

    paginator = Paginator(staff_qs, 5)  # 5 per page
    staff_list = paginator.get_page(page)

    roles = Role.objects.filter(is_active=True)

    html = render_to_string(
        "hr/default/user_mgnt/hr_user_list_rows.html",  # render only tbody rows
        {"staff_list": staff_list, "roles": roles},
        request=request
    )

    return JsonResponse({
        "html": html,
        "page_number": staff_list.number,
        "num_pages": paginator.num_pages,
        "has_previous": staff_list.has_previous(),
        "has_next": staff_list.has_next()
    })


# ============================================
# ADD STAFF
# ============================================
def dashboard_user_add(request):
    if request.method == "POST":
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("human_resource:hr_user_mgnt"))
    else:
        form = StaffForm()

    return render(request, "hr/default/user_mgnt/hr_user_form.html", {'form': form, 'action': 'Add'})


# ============================================
# EDIT STAFF
# ============================================
def dashboard_user_edit(request, pk):
    obj = get_object_or_404(Staff, pk=pk)

    if request.method == "POST":
        form = StaffForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect(reverse("human_resource:hr_user_mgnt"))
    else:
        form = StaffForm(instance=obj)

    return render(request, "hr/default/user_mgnt/hr_user_form.html", {'form': form, 'action': 'Edit'})




def check_employee_number(request):
    emp_no = request.GET.get("emp_no", "").strip()
    staff_id = request.GET.get("staff_id")  # when editing

    if not emp_no:
        return JsonResponse({"exists": False})

    # Check database
    qs = Staff.objects.filter(employee_number=emp_no)

    # Allow same number if editing the same employee
    if staff_id:
        qs = qs.exclude(id=staff_id)

    return JsonResponse({"exists": qs.exists()})


#=========================================
#
# EmployeeProfileSettings
#
#=========================================

# List all employees
def employee_list(request):
    employees = Staff.objects.all()
    return render(request, 'hr/default/employees/employeeproset_list.html', {'employees': employees})



# Edit employee profile settings
def employee_profile(request, employee_id):
    employee = get_object_or_404(Staff, id=employee_id)
    profile, created = EmployeeProfileSettings.objects.get_or_create(employee=employee)
    
    # Dynamic shift options from Staff model
    shifts = Staff.SHIFT_CHOICES

    if request.method == 'POST':
        rank = request.POST.get('rank')
        shift = request.POST.get('shift')
        vl = request.POST.get('vl')
        sl = request.POST.get('sl')

        profile.rank = rank
        profile.shift = shift
        profile.current_vl = vl
        profile.current_sl = sl
        profile.save()
        return redirect('human_resource:hr_employee_list')

    return render(request, 'hr/default/employees/employee_profile.html', {
        'employee': employee,
        'profile': profile,
        'shifts': shifts,
        'RANK_CHOICES': Staff.RANK_CHOICES
    })


#=========================================
#
# Attendance
#
#=========================================

#HR View
def attendance_list(request):
    attendances = Attendance.objects.select_related('employee').all().order_by('-date')
    return render(request, 'hr/default/attendance/attendance_list.html', {
        'attendances': attendances
    })

#Employee View
def attendance_clock(request):
    # --- Get employee from session ---
    emp_num = request.session.get('employee_number')
    if not emp_num:
        return redirect('login')  # not logged in

    employee = Staff.objects.get(employee_number=emp_num)
    today = date.today()

    # --- Get or create today's attendance ---
    attendance, created = Attendance.objects.get_or_create(employee=employee, date=today)

    # --- Fetch dynamic shift rule ---
    shift_rule = EmployeeShiftRule.objects.filter(shift=employee.shift, rank=employee.rank).first()

    # --- Handle Clock In / Clock Out ---
    if request.method == 'POST':
        action = request.POST.get('action')
        now = timezone.localtime().time()

        if action == 'clock_in':
            attendance.clock_in = now
        elif action == 'clock_out':
            attendance.clock_out = now

        # --- Calculate status safely ---
        if shift_rule:
            if attendance.clock_in:
                if shift_rule.clock_in_start and attendance.clock_in > shift_rule.clock_in_start:
                    attendance.status = 'late'
                else:
                    attendance.status = 'present'
            else:
                attendance.status = 'absent'

            if attendance.clock_out:
                if shift_rule.clock_out and attendance.clock_out < shift_rule.clock_out:
                    if ' / early_leave' not in attendance.status:
                        attendance.status += ' / early_leave'
        else:
            # fallback if no shift rule exists
            attendance.status = 'present' if attendance.clock_in else 'absent'

        attendance.save()
        return redirect('human_resource:attendance_clock')

    # --- Fetch attendance history ---
    history = Attendance.objects.filter(employee=employee).order_by('-date')

    # --- Determine if shift rule is missing/incomplete ---
    shift_rule_incomplete = False
    if not shift_rule or not (shift_rule.clock_in_start and shift_rule.clock_in_end and shift_rule.clock_out):
        shift_rule_incomplete = True

    # --- Fetch leave credits ---
    leave_credits = LeaveCredit.objects.filter(employee=employee)
    vl_credit = leave_credits.filter(leave_type='vl').first()
    sl_credit = leave_credits.filter(leave_type='sl').first()

    return render(request, 'hr/default/attendance/attendance_clock.html', {
        'attendance': attendance,
        'employee': employee,
        'shift_rule': shift_rule,
        'history': history,
        'shift_rule_incomplete': shift_rule_incomplete,
        'vl_credit': vl_credit,
        'sl_credit': sl_credit,
    })

#=========================================
#
# Shift Rule
#
#=========================================
# List all shift rules
def hr_shift_rules_list(request):
    # Pre-fill all shift x rank combinations dynamically
    for shift, _ in Staff.SHIFT_CHOICES:
        for rank, _ in Staff.RANK_CHOICES:
            EmployeeShiftRule.objects.get_or_create(shift=shift, rank=rank)

    rules = EmployeeShiftRule.objects.all().order_by('shift', 'rank')

    if request.method == 'POST':
        for rule in rules:
            clock_in_start = request.POST.get(f'clock_in_start_{rule.id}')
            clock_in_end = request.POST.get(f'clock_in_end_{rule.id}')
            clock_out = request.POST.get(f'clock_out_{rule.id}')

            if clock_in_start and clock_in_end and clock_out:
                try:
                    rule.clock_in_start = datetime.strptime(clock_in_start, "%H:%M").time()
                    rule.clock_in_end = datetime.strptime(clock_in_end, "%H:%M").time()
                    rule.clock_out = datetime.strptime(clock_out, "%H:%M").time()
                    rule.save()
                except ValueError:
                    messages.error(request, f"Invalid time format for {rule}")
        messages.success(request, "Shift rules updated successfully!")
        return redirect('human_resource:hr_shift_rules_list')

    context = {'rules': rules}
    return render(request, 'hr/default/shift_rules/shift_rules_list.html', context)




#=========================================
#
# Leave Credit
#
#=========================================

# --- Leave Credit List ---
def leave_credit_list(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'year')

    credits = LeaveCredit.objects.select_related('employee')

    if query:
        credits = credits.filter(
            Q(employee__first_name__icontains=query) |
            Q(employee__last_name__icontains=query)
        )

    allowed_sorts = ['year', '-year', 'leave_type', '-leave_type', 'employee', '-employee']
    if sort in ['employee', '-employee']:
        credits = credits.annotate(
            full_name=Concat(
                F('employee__first_name'),
                Value(' '),
                F('employee__last_name'),
                output_field=CharField()
            )
        ).order_by('full_name' if sort == 'employee' else '-full_name')
    elif sort in allowed_sorts:
        credits = credits.order_by(sort)
    else:
        credits = credits.order_by('year')

    paginator = Paginator(credits, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hr/default/leave/leave_credit_list.html', {
        'leave_credits': page_obj,
        'query': query,
        'sort': sort,
    })


# Add / Edit Leave Credit
def leave_credit_add(request):
    if request.method == 'POST':
        form = LeaveCreditForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('human_resource:leave_credit_list')
    else:
        form = LeaveCreditForm()

    return render(request, 'hr/default/leave/leave_credit_form.html', {
        'form': form,
        'leave_credit': None
    })



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
        'form': form,
        'leave_credit': credit
    })

#def ajax_get_employee_rank(request):
#    emp_id = request.GET.get('employee_id')
#    try:
#        employee = Staff.objects.get(id=emp_id)
#        return JsonResponse({"rank": employee.rank})
#    except Staff.DoesNotExist:
#        return JsonResponse({"rank": ""})
    
def get_employee_rank(request):
    emp_id = request.GET.get('employee_id')
    if emp_id:
        try:
            emp = Staff.objects.get(id=emp_id)
            return JsonResponse({'rank': emp.get_rank_display()})
        except Staff.DoesNotExist:
            return JsonResponse({'rank': 'Not found'})
    return JsonResponse({'rank': ''})



# -----------------------------
# List of leave requests
# -----------------------------
# AJAX: fetch rank & department
def get_employee_info(request):
    emp_id = request.GET.get('employee_id')
    if not emp_id:
        return JsonResponse({'rank': '', 'department': ''})
    try:
        emp = Staff.objects.get(pk=emp_id)
        rank_display = getattr(emp, 'rank', '') or getattr(emp, 'job_title', '')
        dept = getattr(emp, 'department', '') or ''
        try:
            rank_label = emp.get_rank_display()
        except Exception:
            rank_label = rank_display
        return JsonResponse({'rank': rank_label, 'department': dept})
    except Staff.DoesNotExist:
        return JsonResponse({'rank': '', 'department': ''})

# List leave requests

# --- Leave Request List ---
def leave_request_list(request):
    search = request.GET.get("search", "").strip()
    employee_id = request.GET.get("employee")
    leave_type = request.GET.get("leave_type")
    sort = request.GET.get("sort", "-date_filed")

    allowed_sorts = [
        "date_filed", "-date_filed",
        "created_at", "-created_at",
        "status", "-status",
        "leave_type", "-leave_type",
        "employee__first_name", "-employee__first_name",
        "employee__last_name", "-employee__last_name",
    ]
    if sort not in allowed_sorts:
        sort = "-date_filed"

    qs = LeaveRequest.objects.select_related("employee")
    if search:
        qs = qs.filter(
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search) |
            Q(leave_type__icontains=search) |
            Q(status__icontains=search)
        )
    if employee_id:
        qs = qs.filter(employee__id=employee_id)
    if leave_type:
        qs = qs.filter(leave_type=leave_type)

    qs = qs.order_by(sort)
    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

 # --- Leave Credits dict ---
    employee_ids = [req.employee.id for req in page_obj]
    credits = LeaveCredit.objects.filter(employee__id__in=employee_ids)
    credit_dict = {}
    for c in credits:
        if c.employee_id not in credit_dict:
            credit_dict[c.employee_id] = {}
        credit_dict[c.employee_id][c.leave_type] = {
            "used": float(c.used),
            "total": float(c.total),
            "remaining": float(c.total) - float(c.used)
        }

    return render(request, "hr/default/leave/leave_request_list.html", {
        "leave_requests": page_obj,
        "search": search,
        "employee_id": employee_id,
        "leave_type": leave_type,
        "sort": sort,
        "leave_credits": credit_dict,
    })

# --- Add Leave Request ---
def leave_request_add(request):
    employee_id = request.GET.get('employee')
    employee = get_object_or_404(Staff, pk=employee_id)

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, initial={'employee': employee})
        if form.is_valid():
            try:
                with transaction.atomic():
                    lr = form.save(commit=False)
                    lr.position = form.cleaned_data['position']
                    lr.department = form.cleaned_data['department']
                    lr.employee = employee
                    lr.save()

                    if lr.status == 'approved':
                        credit, _ = LeaveCredit.objects.get_or_create(
                            employee=employee,
                            leave_type=lr.leave_type,
                            defaults={
                                "total": Decimal('0.0'),
                                "used": Decimal('0.0'),
                                "year": date.today().year
                            }
                        )
                        credit.used += Decimal(str(lr.total_days or 0))
                        credit.save()

                    messages.success(request, "Leave request saved.")
                    return redirect('human_resource:leave_request_list')
            except Exception as e:
                messages.error(request, f"Error saving leave request: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LeaveRequestForm(initial={'employee': employee})

    return render(request, 'hr/default/leave/leave_request_form.html', {'form': form})


# --- Edit Leave Request ---
def leave_request_edit(request, pk):
    lr = get_object_or_404(LeaveRequest, pk=pk)
    old_status = lr.status
    old_total = Decimal(str(lr.total_days or 0))

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, instance=lr)
        if form.is_valid():
            try:
                with transaction.atomic():
                    updated = form.save(commit=False)
                    updated.position = form.cleaned_data['position']
                    updated.department = form.cleaned_data['department']
                    updated.save()

                    credit, _ = LeaveCredit.objects.get_or_create(
                        employee=updated.employee,
                        leave_type=updated.leave_type,
                        defaults={
                            "total": Decimal('0.0'),
                            "used": Decimal('0.0'),
                            "year": date.today().year
                        }
                    )

                    updated_total = Decimal(str(updated.total_days or 0))

                    # Adjust used leave based on status change
                    if old_status != 'approved' and updated.status == 'approved':
                        credit.used += updated_total
                    elif old_status == 'approved' and updated.status != 'approved':
                        credit.used = max(Decimal('0.0'), credit.used - old_total)
                    elif old_status == 'approved' and updated.status == 'approved':
                        diff = updated_total - old_total
                        credit.used = max(Decimal('0.0'), credit.used + diff)

                    credit.save()
                    messages.success(request, "Leave request updated.")
                    return redirect('human_resource:leave_request_list')
            except Exception as e:
                messages.error(request, f"Error updating leave request: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LeaveRequestForm(instance=lr)

    return render(request, 'hr/default/leave/leave_request_form.html', {'form': form})
