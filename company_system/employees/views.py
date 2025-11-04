# employees/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Sum, Avg
from .models import Employee
from .forms import EmployeeForm
import pandas as pd
from django.http import HttpResponse

def export_employees(request):
    qs = Employee.objects.all().values('name', 'position', 'department', 'salary')
    df = pd.DataFrame(list(qs))
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="employees.xlsx"'
    df.to_excel(response, index=False)
    return response

def dashboard(request):
    # Optional filter by department (GET param)
    selected_department = request.GET.get('department', '')

    qs = Employee.objects.all()
    if selected_department:
        qs = qs.filter(department=selected_department)

    # KPIs
    total_employees = qs.count()
    total_salary = qs.aggregate(Sum('salary'))['salary__sum'] or 0
    avg_salary = qs.aggregate(Avg('salary'))['salary__avg'] or 0

    # Chart data
    names = list(qs.values_list('name', flat=True))
    salaries = [float(s) for s in qs.values_list('salary', flat=True)]

    position_counts = (
        qs.values('position')
          .annotate(count=Count('id'))
          .order_by('position')
    )
    position_labels = [p['position'] for p in position_counts]
    position_values = [p['count'] for p in position_counts]

    # For filter dropdown
    departments = Employee.objects.values_list('department', flat=True).distinct()

    # Build context dict (either pass this variable or inline)
    context = {
        'employees': qs,
        'total_employees': total_employees,
        'total_salary': total_salary,
        'avg_salary': round(avg_salary, 2),
        'names': names,
        'salaries': salaries,
        'position_labels': position_labels,
        'position_values': position_values,
        'departments': departments,
        'selected_department': selected_department,
    }
    return render(request, 'employees/dashboard.html', context)


def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = EmployeeForm()
    return render(request, 'employees/add_employee.html', {'form': form})


def edit_employee(request, id):
    employee = get_object_or_404(Employee, id=id)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'employees/edit_employee.html', {'form': form, 'employee': employee})


def delete_employee(request, id):
    employee = get_object_or_404(Employee, id=id)
    if request.method == 'POST':
        employee.delete()
        return redirect('dashboard')
    return render(request, 'employees/confirm_delete.html', {'employee': employee})



