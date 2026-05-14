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
from App.authentication.decorators import login_required

from .models import ExitInterview
from .forms import ExitInterviewForm


# ═════════════════════════════════════════════════════════════════════════════
# EXIT INTERVIEW VIEWS
# ═════════════════════════════════════════════════════════════════════════════

@login_required
def exit_interview_list(request):
    """
    HR Dashboard: List all exit interviews with filtering and progress overview.
    Supports HTMX for live filtering without page reload.
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    # Permission check: only HR/Admin/Owner can access
    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return redirect('login')
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            messages.error(request, "Permission denied.")
            return redirect('human_resource:hr_dashboard')
    else:
        employee = None

    # Search & filter
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    interviews = ExitInterview.objects.select_related('employee').all()

    if search_query:
        interviews = interviews.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__employee_number__icontains=search_query)
        )

    if status_filter:
        interviews = interviews.filter(resignation_status=status_filter)

    # Pagination
    paginator = Paginator(interviews, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Counts for status summary
    total_count = ExitInterview.objects.count()
    exit_count = ExitInterview.objects.filter(resignation_status='exit').count()
    revoked_count = ExitInterview.objects.filter(resignation_status='revoked').count()
    indefinite_count = ExitInterview.objects.filter(resignation_status='indefinite_leave').count()
    contract_end_count = ExitInterview.objects.filter(resignation_status='end_contract').count()

    context = {
        'employee': employee,
        'is_owner': is_owner,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'resignation_status_choices': ExitInterview.RESIGNATION_STATUS_CHOICES,
        'total_count': total_count,
        'exit_count': exit_count,
        'revoked_count': revoked_count,
        'indefinite_count': indefinite_count,
        'contract_end_count': contract_end_count,
    }

    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request', False)

    if is_htmx:
        # Return only the partial content for HTMX
        return render(request, 'hr/default/exit_interview/_exit_interview_results_partial.html', context)

    return render(request, 'hr/default/exit_interview/exit_interview_list.html', context)


@login_required
def exit_interview_add(request):
    """
    Create a new Exit Interview record.
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return redirect('login')
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            messages.error(request, "Permission denied.")
            return redirect('human_resource:hr_dashboard')
    else:
        employee = None

    if request.method == 'POST':
        form = ExitInterviewForm(request.POST, request.FILES)
        if form.is_valid():
            interview = form.save()
            messages.success(request, f"Exit interview created for {interview.get_full_name()}.")
            return redirect('human_resource:exit_interview_list')
    else:
        form = ExitInterviewForm()

    # Get all active employees for the dropdown
    employees = Staff.objects.filter(status='active').order_by('first_name', 'last_name')

    context = {
        'employee': employee,
        'is_owner': is_owner,
        'form': form,
        'employees': employees,
        'title': 'Add Exit Interview',
    }
    return render(request, 'hr/default/exit_interview/exit_interview_form.html', context)


@login_required
def exit_interview_edit(request, pk):
    """
    Edit an existing Exit Interview record.
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return redirect('login')
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            messages.error(request, "Permission denied.")
            return redirect('human_resource:hr_dashboard')
    else:
        employee = None

    interview = get_object_or_404(ExitInterview, pk=pk)

    if request.method == 'POST':
        form = ExitInterviewForm(request.POST, request.FILES, instance=interview)
        if form.is_valid():
            interview = form.save()
            messages.success(request, f"Exit interview updated for {interview.get_full_name()}.")
            return redirect('human_resource:exit_interview_list')
    else:
        form = ExitInterviewForm(instance=interview)

    context = {
        'employee': employee,
        'is_owner': is_owner,
        'form': form,
        'interview': interview,
        'title': 'Edit Exit Interview',
    }
    return render(request, 'hr/default/exit_interview/exit_interview_form.html', context)


@login_required
def exit_interview_detail(request, pk):
    """
    View detailed Exit Interview information.
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return redirect('login')
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            messages.error(request, "Permission denied.")
            return redirect('human_resource:hr_dashboard')
    else:
        employee = None

    interview = get_object_or_404(
        ExitInterview.objects.select_related('employee'),
        pk=pk
    )

    # Calculate progress
    progress_percentage = interview.get_progress_percentage()
    is_complete = interview.is_process_complete()

    context = {
        'employee': employee,
        'is_owner': is_owner,
        'interview': interview,
        'progress_percentage': progress_percentage,
        'is_complete': is_complete,
        'title': 'Exit Interview Details',
    }
    return render(request, 'hr/default/exit_interview/exit_interview_detail.html', context)


@login_required
def exit_interview_quick_status_update(request, pk):
    """
    HTMX endpoint: Quick status update for a single field.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            return JsonResponse({'error': 'Permission denied'}, status=403)

    interview = get_object_or_404(ExitInterview, pk=pk)
    field_name = request.POST.get('field')
    new_value = request.POST.get('value')

    if not field_name or not new_value:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    # Validate field name
    allowed_fields = [
        'rendering_30day_status', 'exit_interview_status',
        'knowledge_transfer_status', 'asset_return_status',
        'clearance_status', 'quitclaim_status', 'final_pay_status',
        'nda_signed', 'nca_signed'
    ]
    if field_name not in allowed_fields:
        return JsonResponse({'error': 'Invalid field'}, status=400)

    # Handle boolean fields
    if field_name in ['nda_signed', 'nca_signed']:
        new_value = new_value.lower() == 'true'
    setattr(interview, field_name, new_value)
    interview.save()

    # Return updated badge HTML
    if field_name in ['rendering_30day_status', 'exit_interview_status',
                      'knowledge_transfer_status', 'asset_return_status',
                      'clearance_status', 'quitclaim_status', 'final_pay_status']:
        badge_class = interview.get_status_badge_class(field_name)
        display_value = getattr(interview, f'get_{field_name}_display')()
        html = f'<span class="{badge_class} inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium">{display_value}</span>'
        return HttpResponse(html)

    return JsonResponse({'success': True})


@login_required
def exit_interview_delete(request, pk):
    """
    Delete an exit interview record.
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return redirect('login')
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            messages.error(request, "Permission denied.")
            return redirect('human_resource:hr_dashboard')

    interview = get_object_or_404(ExitInterview, pk=pk)

    if request.method == 'POST':
        interview.delete()
        messages.success(request, "Exit interview deleted successfully.")
        return redirect('human_resource:exit_interview_list')

    context = {
        'interview': interview,
    }
    return render(request, 'hr/default/exit_interview/exit_interview_confirm_delete.html', context)
