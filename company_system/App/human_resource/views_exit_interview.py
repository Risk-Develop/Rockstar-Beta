from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseBadRequest, HttpResponseNotAllowed
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat
from django.utils import timezone
import csv

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
    HR Dashboard: List all exit interviews with filtering, sorting, and progress overview.
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

    # Base queryset
    interviews = ExitInterview.objects.select_related('employee').all()

    # Search & filter
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    if search_query:
        interviews = interviews.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__employee_number__icontains=search_query)
        )
    if status_filter:
        interviews = interviews.filter(resignation_status=status_filter)

    # Sorting
    sort_by = request.GET.get('sort', 'created_at')
    sort_order = request.GET.get('order', 'desc')
    allowed_sort_fields = [
        'employee__first_name', 'employee__last_name', 'resignation_status',
        'date_filed', 'approved_last_day', 'created_at'
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = 'created_at'
    interviews = interviews.order_by(sort_by) if sort_order == 'asc' else interviews.order_by(f'-{sort_by}')

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
        'current_sort': sort_by,
        'current_order': sort_order,
        'rendering_30day_status_choices': ExitInterview.RENDERING_30DAY_STATUS_CHOICES,
        'exit_interview_status_choices': ExitInterview.EXIT_INTERVIEW_STATUS_CHOICES,
        'knowledge_transfer_status_choices': ExitInterview.KNOWLEDGE_TRANSFER_STATUS_CHOICES,
        'asset_return_status_choices': ExitInterview.ASSET_RETURN_STATUS_CHOICES,
        'clearance_status_choices': ExitInterview.CLEARANCE_STATUS_CHOICES,
        'quitclaim_status_choices': ExitInterview.QUITCLAIM_STATUS_CHOICES,
        'final_pay_status_choices': ExitInterview.FINAL_PAY_STATUS_CHOICES,
    }

    if request.headers.get('HX-Request'):
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
            if request.POST.get('save_and_add_another'):
                return redirect('human_resource:exit_interview_add')
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
            interview = form.save(commit=False)
            # Capture the user who made this change for audit tracking
            emp_num = request.session.get('employee_number')
            changing_user = Staff.objects.filter(employee_number=emp_num).first()
            interview._changed_by = changing_user
            interview.save()
            form.save_m2m() if hasattr(form, 'save_m2m') else None
            messages.success(request, f"Exit interview updated for {interview.get_full_name()}.")
            if request.POST.get('save_and_add_another'):
                return redirect('human_resource:exit_interview_add')
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
        employee = Staff.objects.filter(employee_number=emp_num).first()

    interview = get_object_or_404(
        ExitInterview.objects.select_related('employee'),
        pk=pk
    )

    # Calculate progress
    progress_percentage = interview.get_progress_percentage()
    is_complete = interview.is_process_complete()

    # Fetch full audit history for timeline lookups (unlimited)
    history_qs = interview.history.select_related('changed_by').all()

    # Fetch recent history for display (limit to 50)
    history = history_qs[:50]

    # Compute timeline milestones
    # We'll build a list of events with label, date, and completion status
    timeline_events = []

    # 1. Form Filed
    if interview.date_filed:
        timeline_events.append({
            'label': 'Resignation Form Filed',
            'date': interview.date_filed,
            'completed': True,
            'icon': 'file-alt',
        })

    # 2. Exit Interview Completed
    exit_completed = interview.exit_interview_status == 'completed'
    exit_date = None
    if exit_completed:
        # Try to find the history entry when status changed to completed
        exit_hist = history_qs.filter(field_name='exit_interview_status', new_value='completed').first()
        exit_date = exit_hist.changed_at.date() if exit_hist else interview.updated_at.date()
    timeline_events.append({
        'label': 'Exit Interview',
        'date': exit_date,
        'completed': exit_completed,
        'icon': 'clipboard-check',
    })

    # 3. Knowledge Transfer Completed
    kt_completed = interview.knowledge_transfer_status == 'completed'
    kt_date = None
    if kt_completed:
        kt_hist = history_qs.filter(field_name='knowledge_transfer_status', new_value='completed').first()
        kt_date = kt_hist.changed_at.date() if kt_hist else interview.updated_at.date()
    timeline_events.append({
        'label': 'Knowledge Transfer',
        'date': kt_date,
        'completed': kt_completed,
        'icon': 'books',
    })

    # 4. Asset Return Completed
    asset_completed = interview.asset_return_status == 'completed'
    asset_date = None
    if asset_completed:
        asset_hist = history_qs.filter(field_name='asset_return_status', new_value='completed').first()
        asset_date = asset_hist.changed_at.date() if asset_hist else interview.updated_at.date()
    timeline_events.append({
        'label': 'Asset Return',
        'date': asset_date,
        'completed': asset_completed,
        'icon': 'box-open',
    })

    # 5. Clearance Completed
    clearance_completed = interview.clearance_status == 'completed'
    clearance_date = None
    if clearance_completed:
        clearance_hist = history_qs.filter(field_name='clearance_status', new_value='completed').first()
        clearance_date = clearance_hist.changed_at.date() if clearance_hist else interview.updated_at.date()
    timeline_events.append({
        'label': 'Clearance',
        'date': clearance_date,
        'completed': clearance_completed,
        'icon': 'check-shield',
    })

    # 6. Quitclaim Completed
    quitclaim_completed = interview.quitclaim_status == 'completed'
    quitclaim_date = None
    if quitclaim_completed:
        quitclaim_hist = history_qs.filter(field_name='quitclaim_status', new_value='completed').first()
        quitclaim_date = quitclaim_hist.changed_at.date() if quitclaim_hist else interview.updated_at.date()
    timeline_events.append({
        'label': 'Quitclaim',
        'date': quitclaim_date,
        'completed': quitclaim_completed,
        'icon': 'file-contract',
    })

    # 7. Final Pay Released
    final_pay_completed = interview.final_pay_status == 'released'
    final_pay_date = None
    if final_pay_completed:
        final_pay_hist = history_qs.filter(field_name='final_pay_status', new_value='released').first()
        final_pay_date = final_pay_hist.changed_at.date() if final_pay_hist else interview.updated_at.date()
    timeline_events.append({
        'label': 'Final Pay',
        'date': final_pay_date,
        'completed': final_pay_completed,
        'icon': 'money-bill-wave',
    })

    # Compute deadline statuses for widget
    from datetime import date, timedelta
    today = date.today()
    deadline_threshold = timedelta(days=7)  # 7 days threshold for "approaching"

    deadlines = []

    # Desired Last Day
    if interview.desired_last_day:
        due_date = interview.desired_last_day
        if due_date < today:
            status = 'overdue'
            status_text = 'Overdue'
        elif (due_date - today) <= deadline_threshold:
            status = 'approaching'
            status_text = 'Approaching'
        else:
            status = 'on_track'
            status_text = 'On Track'
        deadlines.append({
            'label': 'Desired Last Day',
            'date': due_date,
            'status': status,
            'status_text': status_text,
        })

    # Approved Last Day
    if interview.approved_last_day:
        due_date = interview.approved_last_day
        if due_date < today:
            status = 'overdue'
            status_text = 'Overdue'
        elif (due_date - today) <= deadline_threshold:
            status = 'approaching'
            status_text = 'Approaching'
        else:
            status = 'on_track'
            status_text = 'On Track'
        deadlines.append({
            'label': 'Approved Last Day',
            'date': due_date,
            'status': status,
            'status_text': status_text,
        })

    # 30-Day Rendering Deadline (if applicable)
    if interview.date_filed and interview.rendering_30day_status not in ['na', 'completed', 'immediate']:
        due_date = interview.date_filed + timedelta(days=30)
        if due_date < today:
            status = 'overdue'
            status_text = 'Overdue'
        elif (due_date - today) <= deadline_threshold:
            status = 'approaching'
            status_text = 'Approaching'
        else:
            status = 'on_track'
            status_text = 'On Track'
        deadlines.append({
            'label': '30-Day Rendering',
            'date': due_date,
            'status': status,
            'status_text': status_text,
        })

    context = {
        'employee': employee,
        'is_owner': is_owner,
        'interview': interview,
        'progress_percentage': progress_percentage,
        'is_complete': is_complete,
        'history': history,
        'timeline_events': timeline_events,
        'deadlines': deadlines,
        'title': 'Exit Interview Details',
    }
    return render(request, 'hr/default/exit_interview/exit_interview_detail.html', context)


@login_required
def exit_interview_quick_status_update(request, pk):
    """
    HTMX endpoint: Quick status update for a single field.
    Returns the updated table row HTML for HTMX requests.
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

    # If HTMX request, return the updated row HTML
    if request.headers.get('HX-Request'):
        # Render the row partial with full context
        context = {
            'interview': interview,
            'request': request,
            'rendering_30day_status_choices': ExitInterview.RENDERING_30DAY_STATUS_CHOICES,
            'exit_interview_status_choices': ExitInterview.EXIT_INTERVIEW_STATUS_CHOICES,
            'knowledge_transfer_status_choices': ExitInterview.KNOWLEDGE_TRANSFER_STATUS_CHOICES,
            'asset_return_status_choices': ExitInterview.ASSET_RETURN_STATUS_CHOICES,
            'clearance_status_choices': ExitInterview.CLEARANCE_STATUS_CHOICES,
            'quitclaim_status_choices': ExitInterview.QUITCLAIM_STATUS_CHOICES,
            'final_pay_status_choices': ExitInterview.FINAL_PAY_STATUS_CHOICES,
        }
        html = render_to_string('hr/default/exit_interview/_exit_interview_row.html', context)
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


@login_required
def exit_interview_export(request):
    """
    Export filtered exit interviews to CSV.
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

    # Get filter parameters (same as list)
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

    # Sorting
    sort_by = request.GET.get('sort', 'created_at')
    sort_order = request.GET.get('order', 'desc')
    allowed_sort_fields = [
        'employee__first_name', 'employee__last_name', 'resignation_status',
        'date_filed', 'approved_last_day', 'created_at'
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = 'created_at'
    if sort_order == 'asc':
        interviews = interviews.order_by(sort_by)
    else:
        interviews = interviews.order_by(f'-{sort_by}')

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="exit_interviews.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Employee Number', 'Full Name', 'Department', 'Job Title', 'Employment Type',
        'Resignation Status', 'Date Filed', 'Desired Last Day', 'Approved Last Day',
        '30-Day Status', 'Exit Interview Status', 'Knowledge Transfer Status',
        'Asset Return Status', 'Clearance Status', 'Quitclaim Status', 'Final Pay Status',
        'Progress %', 'NDA Signed', 'NCA Signed'
    ])

    for interview in interviews:
        writer.writerow([
            interview.get_employee_number(),
            interview.get_full_name(),
            interview.get_department(),
            interview.employee.job_title or '',
            interview.employee.get_type_display() if interview.employee.type else '',
            interview.get_resignation_status_display(),
            interview.date_filed.strftime('%Y-%m-%d') if interview.date_filed else '',
            interview.desired_last_day.strftime('%Y-%m-%d') if interview.desired_last_day else '',
            interview.approved_last_day.strftime('%Y-%m-%d') if interview.approved_last_day else '',
            interview.get_rendering_30day_status_display(),
            interview.get_exit_interview_status_display(),
            interview.get_knowledge_transfer_status_display(),
            interview.get_asset_return_status_display(),
            interview.get_clearance_status_display(),
            interview.get_quitclaim_status_display(),
            interview.get_final_pay_status_display(),
            interview.get_progress_percentage(),
            'Yes' if interview.nda_signed else 'No',
            'Yes' if interview.nca_signed else 'No',
        ])

    return response


@login_required
def exit_interview_quick_view(request, pk):
    """
    Return quick view HTML for modal (HTMX).
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            return JsonResponse({'error': 'Permission denied'}, status=403)

    interview = get_object_or_404(ExitInterview.objects.select_related('employee'), pk=pk)
    progress_percentage = interview.get_progress_percentage()
    is_complete = interview.is_process_complete()

    context = {
        'interview': interview,
        'progress_percentage': progress_percentage,
        'is_complete': is_complete,
    }
    return render(request, 'hr/default/exit_interview/_exit_interview_quick_view.html', context)


@login_required
def exit_interview_auto_save(request):
    """
    AJAX endpoint for client-side auto-save.
    Accepts partial POST data and persists a draft ExitInterview. Returns 200 JSON.
    Does NOT redirect on render — always JSON.
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)

    if not is_owner:
        employee = Staff.objects.filter(employee_number=emp_num).first()
        if not employee:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        role_name = employee.role.role_name if employee.role else ''
        if role_name not in ['Owner', 'Master', 'Developer', 'Admin', 'HR']:
            return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    pk = request.POST.get('pk')
    bound_flags = request.POST.get('bound_fields')

    if pk:
        interview = get_object_or_404(ExitInterview, pk=pk)
        form = ExitInterviewForm(request.POST, request.FILES, instance=interview)
    else:
        form = ExitInterviewForm(request.POST, request.FILES)

    if form.is_valid():
        interview = form.save(commit=False)
        interview.save()
        form.save_m2m() if hasattr(form, 'save_m2m') else None
        return JsonResponse({
            'status': 'ok',
            'id': interview.pk,
            'timestamp': timezone.now().isoformat(),
        })
    else:
        return JsonResponse({
            'status': 'error',
            'errors': form.errors,
        }, status=400)
