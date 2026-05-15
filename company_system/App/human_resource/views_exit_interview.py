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

from .models import ExitInterview, ExitInterviewHistory, ExitFilterPreset, ExitInterviewNotification
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
        staff = None

    # Base queryset
    interviews = ExitInterview.objects.select_related('employee').all()

    # Search (status filter is handled client-side for view persistence)
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    if search_query:
        interviews = interviews.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__employee_number__icontains=search_query)
        )
    # NOTE: resignation_status filtering is intentionally NOT applied server-side.
    # The client-side JS in exit_interview.js toggles row visibility by status,
    # ensuring a single unified table and consistent view-mode switching.

    # Sort
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
    page_size = int(request.GET.get('page_size', 20))
    if page_size not in [10, 25, 50, 100]:
        page_size = 20
    paginator = Paginator(interviews, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Counts for status summary
    total_count = ExitInterview.objects.count()
    exit_count = ExitInterview.objects.filter(resignation_status='exit').count()
    revoked_count = ExitInterview.objects.filter(resignation_status='revoked').count()
    indefinite_count = ExitInterview.objects.filter(resignation_status='indefinite_leave').count()
    contract_end_count = ExitInterview.objects.filter(resignation_status='end_contract').count()

    # Saved presets & notification count
    presets_list = []
    unread_count = 0
    if not is_owner:
        _staff = Staff.objects.filter(employee_number=emp_num).first()
        if _staff:
            presets_list = [
                {'name': p.name, 'category': p.category, 'filter_params': p.filter_params}
                for p in ExitFilterPreset.objects.filter(user=_staff)
            ]
            unread_count = ExitInterviewNotification.objects.filter(
                user=_staff, is_read=False
            ).count()

    context = {
        'employee': employee,
        'is_owner': is_owner,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'resignation_status_choices': ExitInterview.RESIGNATION_STATUS_CHOICES,
        'all_statuses_choices': [{'value': v, 'label': l} for v, l in ExitInterview.RESIGNATION_STATUS_CHOICES],
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
        'view_mode': request.GET.get('view', 'list'),
        'current_page_size': page_size,
        'modes': [
            {'v': 'list',    'l': 'List',    'i': 'fa-list-ul'},
            {'v': 'calendar','l': 'Calendar','i': 'fa-calendar-alt'},
            {'v': 'kanban',  'l': 'Kanban',  'i': 'fa-columns'},
        ],
        'presets': presets_list,
        'notification_count': unread_count,
    }

    hx_request = request.headers.get('HX-Request')
    view_mode = context['view_mode']

    # ── Calendar partial ──────────────────────────────────────────────────────
    if view_mode == 'calendar' and hx_request:
        from collections import defaultdict
        from datetime import date
        calendar_data = defaultdict(list)
        for iv in page_obj:
            day = iv.approved_last_day or iv.desired_last_day
            if day:
                calendar_data[day].append(iv)
        context['calendar_data'] = dict(sorted(calendar_data.items()))
        return render(request, 'hr/default/exit_interview/_exit_interview_calendar_partial.html', context)

    # ── Kanban partial ────────────────────────────────────────────────────────
    if view_mode == 'kanban' and hx_request:
        from collections import defaultdict
        kanban_columns = defaultdict(list)
        for iv in page_obj:
            kanban_columns[iv.exit_interview_status].append(iv)
        context['kanban_columns'] = dict(sorted(kanban_columns.items()))
        context['status_choices'] = ExitInterview.EXIT_INTERVIEW_STATUS_CHOICES
        return render(request, 'hr/default/exit_interview/_exit_interview_kanban_partial.html', context)

    # ── Default list path ─────────────────────────────────────────────────────
    if hx_request:
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

    # ── Comparison data: dept avg vs company avg for progress % ────────────
    dept_name  = interview.get_department()
    dept_qs    = ExitInterview.objects.none()
    if dept_name:
        dept_qs = ExitInterview.objects.filter(
            employee__departmentlink__department_name=dept_name
        )
    dept_interviews  = dept_qs.exclude(pk=pk)
    dept_count = dept_interviews.count()
    dept_sum   = sum(ei.get_progress_percentage() for ei in dept_interviews)
    dept_avg   = round(dept_sum / dept_count) if dept_count else 0

    company_all      = ExitInterview.objects.exclude(pk=pk)
    company_sum      = sum(ei.get_progress_percentage() for ei in company_all)
    company_count    = company_all.count()
    company_avg      = round(company_sum / company_count) if company_count else 0

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
        'document_count': (1 if interview.resignation_letter else 0)
                         + (1 if interview.other_attachments else 0),
        'status_summary': [
            ('rendering_30day_status', '30-Day Rendering'),
            ('exit_interview_status', 'Exit Interview'),
            ('knowledge_transfer_status', 'Knowledge Transfer'),
            ('asset_return_status', 'Asset Return'),
            ('clearance_status', 'Clearance'),
            ('quitclaim_status', 'Quitclaim'),
            ('final_pay_status', 'Final Pay'),
        ],
        'dept_avg_progress': dept_avg,
        'company_avg_progress': company_avg,
        'dept_name': dept_name,
        # Comparison diff strings for template rendering (no |add: arithmetic)
        'dept_diff_pp': f'+{abs(progress_percentage - dept_avg)}' if progress_percentage > dept_avg
                       else str(abs(progress_percentage - dept_avg)),
        'company_diff_pp': f'+{abs(progress_percentage - company_avg)}' if progress_percentage > company_avg
                         else str(abs(progress_percentage - company_avg)),
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


# ═════════════════════════════════════════════════════════════════════════════
# NEW ENHANCED API VIEWS
# ═════════════════════════════════════════════════════════════════════════════


@login_required
def exit_interview_bulk_status_update(request):
    """
    HTMX / JSON endpoint: bulk update status fields on multiple interviews.
    Expected POST body (form-encoded):
        ids: comma-separated list of interview PKs
        field: the status field name to update
        value: the new value to set
    Returns the reloaded results partial (HTMX) or a JSON summary.
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

    ids_raw = request.POST.get('ids', '')
    field_name = request.POST.get('field', '')
    new_value = request.POST.get('value', '')

    if not ids_raw or not field_name or not new_value:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    ids = [pk.strip() for pk in ids_raw.split(',') if pk.strip()]
    allowed_fields = [
        'rendering_30day_status', 'exit_interview_status',
        'knowledge_transfer_status', 'asset_return_status',
        'clearance_status', 'quitclaim_status', 'final_pay_status',
    ]
    if field_name not in allowed_fields:
        return JsonResponse({'error': 'Invalid field'}, status=400)

    updated = ExitInterview.objects.in_bulk(ids)
    for pk_str, interview in updated.items():
        setattr(interview, field_name, new_value)
        interview.save(update_fields=[field_name])

    updated_count = len(updated)
    not_found = len(ids) - updated_count

    if request.headers.get('HX-Request'):
        # Re-render the results partial with current filters
        return _render_results_partial(request)

    return JsonResponse({
        'success': True,
        'updated': updated_count,
        'not_found': not_found,
    })


@login_required
def exit_interview_bulk_mark_all_read(request):
    """
    HTMX/JSON: Mark ALL currently-visible interviews as Completed for the
    'exit_interview_status' field (i.e. "read / actioned").
    If ?field=<name>&value=<val> is provided, those are used instead.
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

    # Build the same queryset as the list view (respects search; status is client-side)
    interviews = ExitInterview.objects.select_related('employee').all()

    search_query = request.POST.get('search', '').strip()
    status_filter = request.POST.get('status', '').strip()   # kept for context URL; NOT a DB filter
    if search_query:
        interviews = interviews.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__employee_number__icontains=search_query)
        )

    field_name = request.POST.get('field', 'exit_interview_status')
    new_value = request.POST.get('value', 'completed')
    allowed_fields = [
        'rendering_30day_status', 'exit_interview_status',
        'knowledge_transfer_status', 'asset_return_status',
        'clearance_status', 'quitclaim_status', 'final_pay_status',
    ]
    if field_name not in allowed_fields:
        field_name = 'exit_interview_status'

    updated_count = interviews.update(**{field_name: new_value})

    if request.headers.get('HX-Request'):
        return _render_results_partial(request, search_query=search_query, status_filter=status_filter)

    return JsonResponse({'success': True, 'updated': updated_count})


def _render_results_partial(request, search_query='', status_filter=''):
    """Helper: rebuild and return the results partial HTML."""
    sort_by   = request.POST.get('sort') or request.GET.get('sort', 'created_at')
    sort_order = request.POST.get('order') or request.GET.get('order', 'desc')
    if search_query:
        qs = ExitInterview.objects.filter(
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query) |
            Q(employee__employee_number__icontains=search_query)
        )
    else:
        qs = ExitInterview.objects.all()
    # NOTE: resignation_status filtering is intentionally NOT applied here.
    # Client-side status toggling is handled by exit_interview.js, keeping a
    # single unified table regardless of the active status filter.
    allowed_sort_fields = [
        'employee__first_name', 'employee__last_name', 'resignation_status',
        'date_filed', 'approved_last_day', 'created_at',
    ]
    if sort_by not in allowed_sort_fields:
        sort_by = 'created_at'
    qs = qs.order_by(sort_by) if sort_order == 'asc' else qs.order_by(f'-{sort_by}')
    paginator = Paginator(qs.select_related('employee'), 20)
    page_number = request.POST.get('page') or request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'view_mode': request.GET.get('view', 'list'),
        'all_statuses_choices': [{'value': v, 'label': l} for v, l in ExitInterview.RESIGNATION_STATUS_CHOICES],
        'current_sort': sort_by,
        'current_order': sort_order,
        'page_window_start': page_obj.number - 3,
        'page_window_end': page_obj.number + 3,
        'rendering_30day_status_choices': ExitInterview.RENDERING_30DAY_STATUS_CHOICES,
        'exit_interview_status_choices': ExitInterview.EXIT_INTERVIEW_STATUS_CHOICES,
        'knowledge_transfer_status_choices': ExitInterview.KNOWLEDGE_TRANSFER_STATUS_CHOICES,
        'asset_return_status_choices': ExitInterview.ASSET_RETURN_STATUS_CHOICES,
        'clearance_status_choices': ExitInterview.CLEARANCE_STATUS_CHOICES,
        'quitclaim_status_choices': ExitInterview.QUITCLAIM_STATUS_CHOICES,
        'final_pay_status_choices': ExitInterview.FINAL_PAY_STATUS_CHOICES,
    }
    return render(request, 'hr/default/exit_interview/_exit_interview_results_partial.html', context)


@login_required
def exit_interview_add_note(request, pk):
    """
    HTMX/JSON endpoint: save a new HR annotation note to an exit interview's
    interview_notes field.  Existing notes are preserved and the new note is
    timestamped and prepended.
    Accepts POST with field 'note' (text) and optional 'change_reason'.
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
    note_text = request.POST.get('note', '').strip()
    change_reason = request.POST.get('change_reason', 'HR Note').strip()

    if not note_text:
        return JsonResponse({'error': 'Note cannot be empty'}, status=400)

    try:
        emp_num = request.session.get('employee_number')
        author = Staff.objects.filter(employee_number=emp_num).first()
        author_name = f"{author.first_name} {author.last_name}" if author else "System"
    except Exception:
        author_name = "System"

    timestamp = timezone.now().strftime('%b %d, %Y %I:%M %p')
    new_note = f"[{timestamp} – {author_name}] {note_text}"
    existing = interview.interview_notes or ''
    interview.interview_notes = new_note + ('\n\n' + existing if existing else '')
    interview.save(update_fields=['interview_notes', 'updated_at'])

    # Audit trail
    ExitInterviewHistory.objects.create(
        interview=interview,
        field_name='interview_notes',
        old_value='',
        new_value=new_note[:200],
        changed_by=author,
        change_reason=change_reason,
    )

    if request.headers.get('HX-Request'):
        return HttpResponse(new_note)

    return JsonResponse({'success': True, 'note': new_note})


@login_required
def exit_interview_request_update(request, pk):
    """
    Trigger a notification / reminder email to the employee (or their manager)
    requesting a status update on this exit interview.  The actual notification
    delivery (SES/SMTP) is handled by the background task system; this view
    enqueues it and returns 200 immediately.
    Request body: ?recipient=employee|manager
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
    recipient = request.POST.get('recipient', 'employee')

    # ── Placeholder enqueue logic ─────────────────────────────────────────────
    # Replace with your notification dispatch call here.
    # Example:
    #   send_update_request.delay(interview_id=pk, recipient=recipient,
    #                             requested_by=emp_num)
    # ──────────────────────────────────────────────────────────────────────────

    if request.headers.get('HX-Request'):
        html = (
            f'<div class="p-4 rounded-lg bg-green-50 dark:bg-green-900/30 '
            f'border border-green-200 dark:border-green-800 text-green-800 '
            f'dark:text-green-200">'
            f'<i class="fas fa-check-circle mr-2"></i>'
            f'Update request sent to '
            f'{"employee" if recipient == "employee" else "manager"}.'
            f'</div>'
        )
        return HttpResponse(html)

    return JsonResponse({'success': True})


@login_required
def exit_interview_satisfaction_chart(request, pk):
    """
    JSON API: return satisfaction-score data for a given exit interview used
    by the doughnut / sparkline chart on the detail view.
    Returns: { scores: { "Satisfaction": 85, "Work Environment": 70, ... },
                average: 78, primary_color: "#3b82f6" }
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    interview = get_object_or_404(ExitInterview.objects.select_related('employee'), pk=pk)
    qd = interview.qualitative_data or {}

    # Map qualitative keys to human-readable chart labels
    key_labels = {
        'primary_driver': 'Primary Driver',
        'categorization': 'Category',
        'improvement_areas': 'Improvement',
        'additional_feedback': 'Feedback',
    }

    scores = {}
    for key, label in key_labels.items():
        raw = qd.get(key, '')
        scores[label] = _sentiment_score(raw)

    average = round(sum(scores.values()) / len(scores)) if scores else 0

    # Company-wide average for comparison
    company_qs = ExitInterview.objects.exclude(pk=pk)
    company_scores = []
    for ei in company_qs:
        d = ei.qualitative_data or {}
        for key in key_labels:
            company_scores.append(_sentiment_score(d.get(key, '')))
    company_avg = round(sum(company_scores) / len(company_scores)) if company_scores else 0

    return JsonResponse({
        'scores': scores,
        'average': average,
        'company_average': company_avg,
        'department_label': interview.get_department(),
    })


def _sentiment_score(text):
    """
    Derive a 0–100 sentiment / satisfaction score from qualitative text.
    Rules:
      – positive words add, negative words subtract.
      – Longer / substantive text is weighted slightly higher.
    """
    if not text:
        return 50  # Neutral default

    positive = [
        'great', 'excellent', 'amazing', 'love', 'enjoy', 'fantastic',
        'wonderful', 'satisfied', 'happy', 'appreciate', 'thankful',
        'supportive', 'growth', 'opportunity', 'recommend',
    ]
    negative = [
        'bad', 'poor', 'terrible', 'hate', 'awful', 'frustrating',
        'toxic', 'unfair', 'underpaid', 'overworked', 'stress', 'burnout',
        'lack', 'worst', 'disappointed', 'unhappy', 'unsatisfied',
    ]

    words = text.lower().split()
    score = 50
    for word in words:
        if word in positive:
            score += 5
        elif word in negative:
            score -= 5

    # Weight by text length (longer = more reliable signal)
    weight = min(len(words) / 20, 1.0)
    score = round(score * (0.5 + 0.5 * weight))

    return max(0, min(100, score))


# ══════════════════════════════════════════════════════════════════════════════
# FILTER PRESETS — Save / list user filter configurations
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def exit_interview_filter_preset_list(request):
    """Return JSON array of the current user's saved filter presets."""
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    if is_owner:
        return JsonResponse([], safe=False)
    staff = Staff.objects.filter(employee_number=emp_num).first()
    if not staff:
        return JsonResponse([], safe=False)
    presets = ExitFilterPreset.objects.filter(user=staff)
    data = [
        {
            'id': p.id,
            'name': p.name,
            'category': p.category,
            'filter_params': p.filter_params,
        }
        for p in presets
    ]
    return JsonResponse(data, safe=False)


@login_required
def exit_interview_filter_preset_save(request):
    """Save or update a named filter preset (POST)."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    if is_owner:
        return JsonResponse({'success': True})  # owner has no personal presets
    staff = Staff.objects.filter(employee_number=emp_num).first()
    if not staff:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    name = request.POST.get('name', '').strip()
    category = request.POST.get('category', 'custom')
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)

    # Build filter_params from current request params (exclude preset keys)
    filter_params = {k: v for k, v in request.GET.items() if k not in ('preset', 'notification_dismissed', 'page')}

    preset, _ = ExitFilterPreset.objects.update_or_create(
        user=staff,
        name=name,
        defaults={'category': category, 'filter_params': filter_params},
    )
    return JsonResponse({'id': preset.id, 'name': preset.name})


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH AUTOCOMPLETE — JSON suggestions for the search field
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def exit_interview_search_suggestions(request):
    """Return up to 10 employee name / employee-number matches as JSON for autocomplete."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'suggestions': []})
    matches = (
        ExitInterview.objects
        .select_related('employee')
        .filter(
            Q(employee__first_name__icontains=q) |
            Q(employee__last_name__icontains=q) |
            Q(employee__employee_number__icontains=q)
        )
        .values('id', 'employee__first_name', 'employee__last_name',
                'employee__employee_number')[:10]
    )
    suggestions = [{
        'id': m['id'],
        'label': f"{m['employee__first_name']} {m['employee__last_name']} (#{m['employee__employee_number']})",
    } for m in matches]
    return JsonResponse({'suggestions': suggestions})


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS — Bell icon dropdown + mark-as-read
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def exit_interview_notifications_dropdown(request):
    """Return an HTML fragment for the bell dropdown panel."""
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    if is_owner:
        return render(request, 'hr/default/exit_interview/_exit_interview_notifications_dropdown.html',
                      {'notifications': [], 'unread_count': 0})
    staff = Staff.objects.filter(employee_number=emp_num).first()
    if not staff:
        return render(request, 'hr/default/exit_interview/_exit_interview_notifications_dropdown.html',
                      {'notifications': [], 'unread_count': 0})
    qs = ExitInterviewNotification.objects.filter(
        user=staff, is_read=False
    ).select_related('interview', 'interview__employee')[:20]
    return render(request, 'hr/default/exit_interview/_exit_interview_notifications_dropdown.html',
                  {'notifications': qs, 'unread_count': qs.count()})


@login_required
def exit_interview_notifications(request):
    """Return unread notification count + list (JSON) — used by JS poller only."""
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    if is_owner:
        return JsonResponse({'count': 0, 'notifications': []})
    staff = Staff.objects.filter(employee_number=emp_num).first()
    if not staff:
        return JsonResponse({'count': 0, 'notifications': []})
    qs = ExitInterviewNotification.objects.filter(
        user=staff, is_read=False
    ).select_related('interview', 'interview__employee')[:20]
    data = [{
        'id': n.id,
        'type': n.get_notification_type_display(),
        'interview_id': n.interview_id,
        'employee': n.interview.get_full_name(),
        'created_at': n.created_at.strftime('%b %d, %Y %I:%M %p'),
        'url': reverse('human_resource:exit_interview_detail', args=[n.interview_id]),
    } for n in qs]
    return JsonResponse({'count': qs.count(), 'notifications': data})


@login_required
def exit_interview_notification_mark_read(request, notif_id):
    """Mark a single notification as read (POST)."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    if is_owner:
        return JsonResponse({'status': 'ok'})
    staff = Staff.objects.filter(employee_number=emp_num).first()
    if not staff:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    ExitInterviewNotification.objects.filter(id=notif_id, user=staff).update(is_read=True)
    return JsonResponse({'status': 'ok'})


# ══════════════════════════════════════════════════════════════════════════════
# COLUMN TOGGLE — persist which columns are visible
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def exit_interview_toggle_column(request):
    """Toggle visibility of a specific column (per-user, stored in session for now)."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    column_field = request.POST.get('column_field', '').strip()
    visible = request.POST.get('visible', '0') == '1'
    emp_num = request.session.get('employee_number')
    if not emp_num:
        return JsonResponse({'status': 'ok'})
    key = f'exit_interview_hidden_columns_{emp_num}'
    hidden = request.session.get(key, [])
    if visible:
        if column_field in hidden:
            hidden = [h for h in hidden if h != column_field]
    else:
        if column_field not in hidden:
            hidden.append(column_field)
    request.session[key] = hidden
    request.session.modified = True
    return JsonResponse({'status': 'ok', 'hidden_columns': hidden})


# ══════════════════════════════════════════════════════════════════════════════
# PAGE SIZE — persist preferred row count per-user
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def exit_interview_set_page_size(request):
    """Store user's preferred page size in session."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    page_size = request.POST.get('page_size', '20')
    emp_num = request.session.get('employee_number') or 'anon'
    request.session[f'exit_interview_page_size_{emp_num}'] = int(page_size)
    return JsonResponse({'status': 'ok'})
