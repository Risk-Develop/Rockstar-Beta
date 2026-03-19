from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Staff, Role, Department, Position, StaffHistory
from .forms import StaffForm, RoleForm, DepartmentForm, PositionForm
from django.urls import reverse
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime


#-------------------------------------
#
# Master_Employee
#
#--------------------------------------




# reload dashboard_user_mgnt view

def update_staff_role(request):
    if request.method == "POST":
        staff_id = request.POST.get("staff_id")
        role_id = request.POST.get("role")
        staff = get_object_or_404(Staff, id=staff_id)
        staff.role_id = role_id if role_id else None
        staff.save()
    return redirect('dashboard_user_mgnt')  # reload page after update 


def user_delete_dash(request, pk):
    obj = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        obj.delete()
        return redirect('dashboard_user_mgnt')
    return render(request, 'users/user_confirm_delete.html', {'staff': obj})



def dashboard_user_detail(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    return render(request, 'dashboard/d_user_detail.html', {'staff': staff})



def ajax_user_list(request):
    search = request.GET.get("search", "")
    page = request.GET.get("page", 1)

    # Filter by first or last name (case-insensitive)
    staff_qs = Staff.objects.select_related('role').filter(
        last_name__icontains=search
    ) | Staff.objects.filter(first_name__icontains=search)
    staff_qs = staff_qs.order_by('last_name', 'first_name')

    paginator = Paginator(staff_qs, 5)  # 10 users per page
    staff_list = paginator.get_page(page)
    roles = Role.objects.filter(is_active=True)

    html = render_to_string(
        "partials/d_user_table.html",
        {"staff_list": staff_list, "roles": roles},
        request=request
    )

    return JsonResponse({
        "html": html,
        "has_next": staff_list.has_next(),
        "has_previous": staff_list.has_previous(),
        "num_pages": paginator.num_pages,
        "current_page": staff_list.number,
    })

#Dashboard_user_mgnt view with pagination and active roles only

# Dashboard - User Management
def dashboard_user_mgnt(request):
    # Select related for both role and department to reduce DB hits
    staff_list = Staff.objects.select_related('role', 'departmentlink').order_by('last_name', 'first_name')
    
    paginator = Paginator(staff_list, 5)
    page_number = request.GET.get('page', 1)
    staff_page = paginator.get_page(page_number)
    
    roles = Role.objects.filter(is_active=True)
    
    return render(request, 'dashboard/dashboard_user_mgnt.html', {
        'staff_list': staff_page,
        'roles': roles
    })

# Add User
def dashboard_user_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            # Set the user who is creating this staff from session
            employee_id = request.session.get('employee_id')
            if employee_id:
                try:
                    staff._changed_by = Staff.objects.get(pk=employee_id)
                except Staff.DoesNotExist:
                    pass
            staff.save()
            return redirect('dashboard_user_mgnt')  # redirect to dashboard management page
    else:
        form = StaffForm()
    
    roles = Role.objects.filter(is_active=True)
    departments = Department.objects.filter(is_active=True)
    
    return render(request, 'dashboard/d_user_form.html', {
        'form': form,
        'action': 'Add',
        'roles': roles,
        'departments': departments
    })

# Edit User
def dashboard_user_edit(request, pk):
    obj = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=obj)
        if form.is_valid():
            staff = form.save(commit=False)
            # Set the user who is editing this staff from session
            employee_id = request.session.get('employee_id')
            if employee_id:
                try:
                    staff._changed_by = Staff.objects.get(pk=employee_id)
                except Staff.DoesNotExist:
                    pass
            staff.save()
            return redirect('dashboard_user_mgnt')  # redirect to dashboard management page
    else:
        form = StaffForm(instance=obj)
    
    roles = Role.objects.filter(is_active=True)
    departments = Department.objects.filter(is_active=True)
    
    return render(request, 'dashboard/d_user_form.html', {
        'form': form,
        'action': 'Edit',
        'staff': obj,
        'roles': roles,
        'departments': departments
    })

#User Views Testing

def user_detail(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    return render(request, 'users/user_detail.html', {'staff': staff})


def user_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            # Set the user who is creating this staff from session
            employee_id = request.session.get('employee_id')
            if employee_id:
                try:
                    staff._changed_by = Staff.objects.get(pk=employee_id)
                except Staff.DoesNotExist:
                    pass
            staff.save()
            return JsonResponse({'success': True, 'id': staff.id, 'name': str(staff)})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False, 'message': 'Only POST allowed'}, status=405)

def user_list(request):
    qs = Staff.objects.all().order_by('last_name', 'first_name')
    return render(request, 'users/user_list.html', {'staff_list': qs})

def user_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            # Set the user who is creating this staff from session
            employee_id = request.session.get('employee_id')
            if employee_id:
                try:
                    staff._changed_by = Staff.objects.get(pk=employee_id)
                except Staff.DoesNotExist:
                    pass
            staff.save()
            return redirect('user_list')
    else:
        form = StaffForm()
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Add'})

def user_edit(request, pk):
    obj = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=obj)
        if form.is_valid():
            staff = form.save(commit=False)
            # Set the user who is editing this staff from session
            employee_id = request.session.get('employee_id')
            if employee_id:
                try:
                    staff._changed_by = Staff.objects.get(pk=employee_id)
                except Staff.DoesNotExist:
                    pass
            staff.save()
            return redirect('user_list')
    else:
        form = StaffForm(instance=obj)
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Edit', 'staff': obj})

def user_delete(request, pk):
    obj = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        obj.delete()
        return redirect('user_list')
    return render(request, 'users/user_confirm_delete.html', {'staff': obj})



#-------------------------------------
#
# Master Role
#
#--------------------------------------

def assign_role(request, user_id):
    user = get_object_or_404(Staff, id=user_id)
    roles = Role.objects.filter(is_active=True)

    if request.method == "POST":
        role_id = request.POST.get('role')
        if role_id:
            user.role_id = role_id
            user.save()
        return redirect('user_list')

    return render(request, 'assign_role.html', {'user': user, 'roles': roles})

def role_add(request):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('role_list')
    else:
        form = RoleForm()
    return render(request, 'roles/role_form.html', {'form': form, 'action':'Add'})

def role_edit(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            return redirect('role_list')
    else:
        form = RoleForm(instance=role)
    return render(request, 'roles/role_form.html', {'form': form, 'action':'Edit'})

def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        role.delete()
        return redirect('role_list')
    return render(request, 'roles/role_confirm_delete.html', {'role': role})

def role_list(request):
    roles = Role.objects.all().order_by('role_name')
    return render(request, 'roles/role_list.html', {'roles': roles})


#select_related('role') works like a SQL join — it fetches related role data in a single query for efficiency.
def user_role_list(request):
    roles = Role.objects.filter(is_active=True)
    return render(request, 'user_role_list.html', {'roles': roles})


def user_list(request):
    staff_list = Staff.objects.select_related('role').all().order_by('last_name', 'first_name')
    roles = Role.objects.filter(is_active=True)

    if request.method == "POST":
        staff_id = request.POST.get("staff_id")
        role_id = request.POST.get("role")
        staff = Staff.objects.get(id=staff_id)
        staff.role_id = role_id
        staff.save()
        return redirect("user_list")

    return render(request, "users/user_list.html", {"staff_list": staff_list, "roles": roles})



#-------------------------------------
#
# Master Department
#
#--------------------------------------


def assign_department(request, user_id):
    user = get_object_or_404(Staff, id=user_id)
    departments = Department.objects.filter(is_active=True)

    if request.method == "POST":
        department_id = request.POST.get('department')
        if department_id:
            user.department_id = department_id
            user.save()
        return redirect('user_list')

    return render(request, 'assign_department.html', {'user': user, 'departments': departments})

@login_required
def department_add(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('department_list')
    else:
        form = DepartmentForm()
    return render(request, 'department/department_form.html', {'form': form, 'action':'Add'})

@login_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'department/department_form.html', {'form': form, 'action':'Edit'})

@login_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        return redirect('department_list')
    return render(request, 'department/department_confirm_delete.html', {'department': department})

@login_required
def department_list(request):
    departments = Department.objects.all().order_by('department_name')
    return render(request, 'department/department_list.html', {'departments': departments})


#select_related('department') works like a SQL join — it fetches related department data in a single query for efficiency.
@login_required
def user_department_list(request):
    departments = Department.objects.filter(is_active=True)
    return render(request, 'user_department_list.html', {'departments': departments})





#-------------------------------------
#
# Master Position
#
#--------------------------------------


def assign_position(request, user_id):
    user = get_object_or_404(Staff, id=user_id)
    positions = Position.objects.filter(is_active=True)

    if request.method == "POST":
        position_id = request.POST.get('position')
        if position_id:
            user.position_id = position_id
            user.save()
        return redirect('user_list')

    return render(request, 'assign_position.html', {'user': user, 'positions': [positions]})

def position_add(request):
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('position_list')
    else:
        form = PositionForm()
    return render(request, 'position/position_form.html', {'form': form, 'action':'Add'})

def position_edit(request, pk):
    position = get_object_or_404(Position, pk=pk)
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            return redirect('position_list')
    else:
        form = PositionForm(instance=position)
    return render(request, 'position/position_form.html', {'form': form, 'action':'Edit'})

def position_delete(request, pk):
    position = get_object_or_404(Position, pk=pk)
    if request.method == 'POST':
        position.delete()
        return redirect('positon_list')
    return render(request, 'position/position_confirm_delete.html', {'position': position})

def position_list(request):
    positions = Position.objects.all().order_by('position_name')
    return render(request, 'position/position_list.html', {'positions': positions})


#select_related('position') works like a SQL join — it fetches related positon data in a single query for efficiency.
def user_position_list(request):
    positions = Position.objects.filter(is_active=True)
    return render(request, 'user_position_list.html', {'positions': positions})


#---------------------------------------
#
# Staff History Tracking
#
#---------------------------------------

def staff_history_list(request):
    """
    Display a list of all staff history records.
    Supports filtering by employee, field name, and date range.
    """
    history_records = StaffHistory.objects.select_related('staff', 'changed_by').all()
    
    # Get filter parameters
    staff_id = request.GET.get('staff')
    field_name = request.GET.get('field')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Apply filters
    if staff_id:
        history_records = history_records.filter(staff_id=staff_id)
    
    if field_name:
        history_records = history_records.filter(field_name=field_name)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            history_records = history_records.filter(changed_at__date__gte=start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            history_records = history_records.filter(changed_at__date__lte=end)
        except ValueError:
            pass
    
    # Paginate results
    paginator = Paginator(history_records, 20)
    page_number = request.GET.get('page', 1)
    history_page = paginator.get_page(page_number)
    
    # Get all staff for filter dropdown
    staff_list = Staff.objects.all().order_by('last_name', 'first_name')
    
    # Get field choices for filter
    field_choices = StaffHistory.FIELD_CHOICES
    
    return render(request, 'staff_history/staff_history_list.html', {
        'history_records': history_page,
        'staff_list': staff_list,
        'field_choices': field_choices,
        'staff_id': staff_id,
        'field_name': field_name,
        'start_date': start_date,
        'end_date': end_date,
    })


def staff_history_detail(request, staff_id):
    """
    Display history records for a specific staff member.
    """
    staff = get_object_or_404(Staff, pk=staff_id)
    history_records = StaffHistory.objects.filter(staff=staff).select_related('changed_by').order_by('-changed_at')
    
    # Paginate results
    paginator = Paginator(history_records, 20)
    page_number = request.GET.get('page', 1)
    history_page = paginator.get_page(page_number)
    
    return render(request, 'staff_history/staff_history_detail.html', {
        'staff': staff,
        'history_records': history_page,
    })
