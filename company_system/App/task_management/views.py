import logging
import json
import os
from datetime import date, timedelta
from django.db import models

logger = logging.getLogger(__name__)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.html import format_html, linebreaks
from django.utils import timezone
from functools import wraps

from .models import KanbanBoard, KanbanColumn, Task, Roadmap, AuditLog, PersonalBoard, PersonalColumn, PersonalTask, PersonalTaskChecklistItem, TaskChecklistItem, TaskComment
from .forms import TaskForm, BoardForm, ColumnForm, RoadmapForm
from App.users.models import Staff
from App.authentication.views import get_current_employee


def custom_login_required(view_func):
    """Custom login_required that checks for employee_number session"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('employee_number'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def can_edit_task(view_func):
    """Decorator: Only assigned user or board creator can edit task"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        task_id = kwargs.get('task_id')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            current_staff = get_current_staff(request)
            is_owner = request.session.get('is_owner', False)
            
            if not is_owner and current_staff:
                if task.created_by != current_staff and task.assigned_to != current_staff:
                    messages.warning(request, "You don't have permission to edit this task.")
                    return redirect('task_management:board_detail', board_id=task.column.board.id)
        
        return view_func(request, *args, **kwargs)
    return wrapper


def can_delete_task(view_func):
    """Decorator: Only board creator or task creator can delete task"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        task_id = kwargs.get('task_id')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            current_staff = get_current_staff(request)
            is_owner = request.session.get('is_owner', False)
            
            if not is_owner and current_staff:
                if task.created_by != current_staff and task.column.board.created_by != current_staff:
                    messages.warning(request, "You don't have permission to delete this task.")
                    return redirect('task_management:board_detail', board_id=task.column.board.id)
        
        return view_func(request, *args, **kwargs)
    return wrapper


def log_audit(task, action, user, description='', from_col=None, to_col=None, request=None):
    """Log task actions to audit trail"""
    ip = None
    if request:
        ip = get_client_ip(request)
    
    AuditLog.objects.create(
        task=task,
        action=action,
        performed_by=user,
        from_column=from_col,
        to_column=to_col,
        description=description,
        ip_address=ip
    )


def get_client_ip(request):
    """Get client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_current_staff(request):
    """Get current staff from session or return None"""
    emp_num = request.session.get('employee_number')
    if emp_num:
        try:
            return Staff.objects.get(employee_number=emp_num)
        except Staff.DoesNotExist:
            return None
    return None


def _enrich_personal_task_checklist(task):
    """Populate checklist JSON + count/completion % attrs on a PersonalTask instance."""
    items = list(task.checklist_items.all())
    task.checklist_items_json = json.dumps(
        [{'id': i.id, 'text': i.text, 'is_completed': i.is_completed} for i in items]
    )
    total = len(items)
    completed = sum(1 for i in items if i.is_completed)
    task.checklist_items_count = total
    task.checklist_completion_percentage = int((completed / total) * 100) if total else 0


def add_months(d, months):
    """Add months to a date, handling month-end overflow correctly."""
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = d.day
    try:
        return date(year, month, day)
    except ValueError:
        # Use last day of month if day exceeds month length
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        return date(year, month, last_day)


def calculate_next_occurrence(task):
    """Calculate the next occurrence dates for a recurring task."""
    next_deadline = task.deadline
    next_deadline_time = task.deadline_time
    next_date_start = task.date_start
    next_date_end = task.date_end

    if task.recurring_type == 'daily':
        delta = timedelta(days=1)
        if next_deadline:
            next_deadline = next_deadline + delta
        if next_date_start:
            next_date_start = next_date_start + delta
        if next_date_end:
            next_date_end = next_date_end + delta

    elif task.recurring_type == 'weekly':
        delta = timedelta(weeks=1)
        if next_deadline:
            next_deadline = next_deadline + delta
        if next_date_start:
            next_date_start = next_date_start + delta
        if next_date_end:
            next_date_end = next_date_end + delta

    elif task.recurring_type == 'monthly':
        if next_deadline:
            next_deadline = add_months(next_deadline, 1)
        if next_date_start:
            next_date_start = add_months(next_date_start, 1)
        if next_date_end:
            next_date_end = add_months(next_date_end, 1)

    return next_deadline, next_deadline_time, next_date_start, next_date_end


def create_recurring_task_instance(task, next_dates):
    """Create the next instance of a recurring task."""
    next_deadline, next_deadline_time, next_date_start, next_date_end = next_dates
    
    # Calculate order (append to end of column)
    max_order = PersonalTask.objects.filter(column=task.column).order_by('-order').first()
    next_order = (max_order.order + 1) if max_order else 0

    # Create new task
    new_task = PersonalTask.objects.create(
        board=task.board,
        column=task.column,
        title=task.title,
        description=task.description,
        priority=task.priority,
        deadline=next_deadline,
        deadline_time=next_deadline_time,
        date_start=next_date_start,
        date_end=next_date_end,
        notes=task.notes,
        is_recurring=True,
        recurring_type=task.recurring_type,
        order=next_order
    )

    # Copy checklist items (reset completion)
    checklist_items = list(task.checklist_items.all())
    for item in checklist_items:
        PersonalTaskChecklistItem.objects.create(
            task=new_task,
            text=item.text,
            order=item.order,
            is_completed=False
        )

    return new_task



@custom_login_required
def board_list(request):
    boards = KanbanBoard.objects.filter(is_active=True)
    return render(request, 'task_management/board_list.html', {
        'boards': boards,
        'board_form': BoardForm()
    })


@custom_login_required
def board_create(request):
    if request.method == 'POST':
        form = BoardForm(request.POST)
        if form.is_valid():
            board = form.save(commit=False)
            board.created_by = get_current_staff(request)
            board.save()
            
            for col in KanbanColumn.DEFAULT_COLUMNS:
                KanbanColumn.objects.create(board=board, **col)
            
            messages.success(request, f'Board "{board.name}" created successfully!')
        else:
            messages.error(request, 'Failed to create board.')
    
    return redirect('task_management:board_list')


@custom_login_required
def board_detail(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id)
    columns = board.columns.filter(is_active=True).order_by('order')
    roadmaps = Roadmap.objects.filter(board=board)
    
    for column in columns:
        column.tasks_list = column.tasks.order_by('order')
    
    return render(request, 'task_management/board_detail.html', {
        'board': board,
        'columns': columns,
        'task_form': TaskForm(),
        'column_form': ColumnForm(),
        'all_staff': Staff.objects.filter(status='active'),
        'roadmaps': roadmaps
    })


@custom_login_required
def board_delete(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id)
    board.is_active = False
    board.save()
    messages.success(request, 'Board "' + board.name + '" deleted.')
    return redirect('task_management:board_list')


@custom_login_required
def column_create(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id)
    
    if request.method == 'POST':
        form = ColumnForm(request.POST)
        if form.is_valid():
            column = form.save(commit=False)
            column.board = board
            column.save()
            messages.success(request, f'Column "{column.name}" created.')
    
    return redirect('task_management:board_detail', board_id=board_id)


@custom_login_required
def column_delete(request, column_id):
    column = get_object_or_404(KanbanColumn, id=column_id)
    board_id = column.board.id
    column.is_active = False
    column.save()
    messages.success(request, f'Column "{column.name}" deleted.')
    return redirect('task_management:board_detail', board_id=board_id)


@custom_login_required
def task_create(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id)
    
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = get_current_staff(request)
            
            roadmap_id = request.POST.get('roadmap_id')
            if roadmap_id:
                task.roadmap_id = roadmap_id
            
            max_order = task.column.tasks.order_by('-order').first()
            task.order = (max_order.order + 1) if max_order else 0
            
            task.save()
            
            if task.assigned_to:
                desc = "Created and assigned to " + str(task.assigned_to)
            else:
                desc = "Created (unassigned)"
            log_audit(task, 'created', get_current_staff(request), desc, request=request)
            
            messages.success(request, 'Task "' + task.title + '" created.')
        else:
            messages.error(request, 'Failed to create task.')
    
    return redirect('task_management:board_detail', board_id=board_id)


@custom_login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    return render(request, 'task_management/task_detail.html', {
        'task': task,
        'task_form': TaskForm(instance=task),
        'all_staff': Staff.objects.filter(status='active')
    })


@custom_login_required
@can_edit_task
def task_edit(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    old_data = f"{task.title} - {task.assigned_to}"
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            new_data = f"{task.title} - {task.assigned_to}"
            log_audit(task, 'edited', get_current_staff(request),
                f"Updated: {old_data} -> {new_data}", request=request)
            messages.success(request, f'Task "{task.title}" updated.')
        else:
            messages.error(request, 'Failed to update task.')
    
    if request.headers.get('HX-Request'):
        return render(request, 'task_management/includes/_task_detail_partial.html', {
            'task': task,
            'task_form': form,
            'all_staff': Staff.objects.filter(status='active')
        })
    
    return redirect('task_management:board_detail', board_id=task.column.board.id)


@custom_login_required
@can_delete_task
def task_delete(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    board_id = task.column.board.id
    task_title = task.title
    
    log_audit(task, 'deleted', get_current_staff(request),
        f"Deleted task: {task_title}", request=request)
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('task_management:board_detail', board_id=board_id)


@require_POST
@custom_login_required
def api_update_task_position(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        column_id = data.get('column_id')
        new_order = data.get('order')
        
        task = Task.objects.get(id=task_id)
        old_column = task.column
        old_column_id = task.column_id
        task.column_id = column_id
        task.order = new_order
        task.save()
        
        if old_column_id != column_id:
            new_column = KanbanColumn.objects.get(id=column_id)
            user = get_current_staff(request)
            log_audit(task, 'moved', user,
                f"Moved from {old_column.name} to {new_column.name}",
                from_col=old_column, to_col=new_column, request=request)
        
        if old_column_id != column_id:
            old_column_tasks = Task.objects.filter(column_id=old_column_id).order_by('order')
            for i, t in enumerate(old_column_tasks):
                if t.order != i:
                    t.order = i
                    t.save()
        
        new_column_tasks = Task.objects.filter(column_id=column_id).exclude(id=task_id).order_by('order')
        for i, t in enumerate(new_column_tasks):
            new_ord = i if i < new_order else i + 1
            if t.order != new_ord:
                t.order = new_ord
                t.save()
        
        return JsonResponse({'success': True, 'task_id': task.id})
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_GET
@custom_login_required
def api_get_tasks(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id)
    columns = board.columns.filter(is_active=True).order_by('order')
    
    for column in columns:
        column.tasks_list = column.tasks.order_by('order')
    
    return render(request, 'task_management/includes/_columns_partial.html', {
        'columns': columns,
        'all_staff': Staff.objects.filter(status='active')
    })


@custom_login_required
def roadmap_list(request):
    roadmaps = Roadmap.objects.all()
    return render(request, 'task_management/roadmap_list.html', {
        'roadmaps': roadmaps,
        'roadmap_form': RoadmapForm()
    })


@custom_login_required
def roadmap_create(request):
    if request.method == 'POST':
        form = RoadmapForm(request.POST)
        if form.is_valid():
            roadmap = form.save(commit=False)
            roadmap.created_by = get_current_staff(request)
            roadmap.save()
            messages.success(request, f'Roadmap "{roadmap.name}" created.')
        else:
            messages.error(request, 'Failed to create roadmap.')
    return redirect('task_management:roadmap_list')


@custom_login_required
def roadmap_detail(request, roadmap_id):
    roadmap = get_object_or_404(Roadmap, id=roadmap_id)
    tasks = Task.objects.filter(column__board=roadmap.board).select_related('column', 'assigned_to')
    all_staff = Staff.objects.filter(status='active')
    return render(request, 'task_management/roadmap_detail.html', {
        'roadmap': roadmap,
        'tasks': tasks,
        'all_staff': all_staff
    })


@custom_login_required
def roadmap_task_create(request, roadmap_id):
    roadmap = get_object_or_404(Roadmap, id=roadmap_id)
    board = roadmap.board
    
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = get_current_staff(request)
            task.roadmap = roadmap
            
            max_order = task.column.tasks.order_by('-order').first()
            task.order = (max_order.order + 1) if max_order else 0
            task.save()
            
            if task.assigned_to:
                desc = "Created and assigned to " + str(task.assigned_to)
            else:
                desc = "Created (unassigned)"
            log_audit(task, 'created', get_current_staff(request), desc, request=request)
            
            messages.success(request, 'Task "' + task.title + '" created.')
            return redirect('task_management:roadmap_detail', roadmap_id=roadmap_id)
        else:
            messages.error(request, 'Failed to create task.')
    
    return redirect('task_management:roadmap_detail', roadmap_id=roadmap_id)


@custom_login_required
def roadmap_delete(request, roadmap_id):
    roadmap = get_object_or_404(Roadmap, id=roadmap_id)
    roadmap.delete()
    messages.success(request, 'Roadmap deleted.')
    return redirect('task_management:roadmap_list')


@custom_login_required
def timeline_view(request, roadmap_id):
    import logging
    logger = logging.getLogger(__name__)
    roadmap = get_object_or_404(Roadmap, id=roadmap_id)
    tasks = Task.objects.filter(column__board=roadmap.board).select_related('column').all()
    logger.error(f"Timeline view - Tasks count: {tasks.count()}, Roadmap: {roadmap.name}, Board: {roadmap.board.name}")
    
    calendar_events = []
    for task in tasks:
        if task.deadline:
            event = {'id': task.id, 'title': task.title, 'start': task.deadline.isoformat(),'className': 'priority-' + task.priority}
            calendar_events.append(event)
        else:
            event = {'id': task.id, 'title': task.title + ' (No deadline)','start': roadmap.start_date.isoformat(),'className': 'priority-' + task.priority}
            calendar_events.append(event)
    
    return render(request, 'task_management/timeline.html', {
        'roadmap': roadmap,
        'tasks': tasks,
        'calendar_events': json.dumps(calendar_events)
    })


@custom_login_required
def personal_board_list(request):
    current_staff = get_current_staff(request)
    if not current_staff and not request.session.get('is_owner'):
        messages.warning(request, "Please log in to access personal boards.")
        return redirect('task_management:board_list')

    personal_boards_qs = PersonalBoard.objects.filter(
        user=current_staff, is_archived=False
    ).prefetch_related('columns') if current_staff else []

    total_tasks_count = 0
    completed_tasks_count = 0

    # Annotate manually
    for board in personal_boards_qs:
        total = board.tasks.count()
        completed = board.tasks.filter(is_completed=True).count()
        high_pending = board.tasks.filter(is_completed=False, is_archived=False, priority='high').count()
        medium_pending = board.tasks.filter(is_completed=False, is_archived=False, priority='medium').count()
        low_pending = board.tasks.filter(is_completed=False, is_archived=False, priority='low').count()

        board.total_tasks = total
        board.completed_tasks = completed
        board.high_priority_tasks = high_pending
        board.medium_priority_tasks = medium_pending
        board.low_priority_tasks = low_pending

        total_tasks_count += total
        completed_tasks_count += completed

        columns = sorted(board.columns.all(), key=lambda c: c.order)
        board.to_do_column_id = columns[0].id if columns else None

    personal_boards = list(personal_boards_qs)

    # ========== Weekly Comparison Stats ==========
    one_week_ago = timezone.now() - timedelta(days=7)

    # Approximate boards last week (use length - 1 as simple comparison)
    boards_last_week = max(0, len(personal_boards) - 1)

    # Tasks created last week (personal tasks only)
    if current_staff:
        tasks_last_week = PersonalTask.objects.filter(
            board__user=current_staff,
            board__is_archived=False,
            created_at__gte=one_week_ago
        ).count()
        # Completed tasks last week (using completed_at)
        completed_tasks_last_week = PersonalTask.objects.filter(
            board__user=current_staff,
            board__is_archived=False,
            is_completed=True,
            completed_at__gte=one_week_ago
        ).count()
    else:
        tasks_last_week = total_tasks_count
        completed_tasks_last_week = completed_tasks_count

    # Productivity score = completion rate percentage
    productivity_score = round(
        (completed_tasks_count / total_tasks_count * 100) if total_tasks_count > 0 else 0
    )

    # Sparkline data - 7 data points representing activity trend
    sparkline_boards = [
        len(personal_boards) - 1,
        len(personal_boards),
        len(personal_boards) + 1,
        len(personal_boards),
        len(personal_boards) - 2,
        len(personal_boards) + 1,
        len(personal_boards)
    ]
    sparkline_tasks = [
        max(0, total_tasks_count - 5),
        total_tasks_count - 2,
        total_tasks_count + 1,
        total_tasks_count,
        total_tasks_count - 3,
        total_tasks_count + 2,
        total_tasks_count
    ]
    sparkline_completed = [
        max(0, completed_tasks_count - 3),
        completed_tasks_count - 1,
        completed_tasks_count + 1,
        completed_tasks_count,
        completed_tasks_count - 2,
        completed_tasks_count,
        completed_tasks_count
    ]

    return render(request, 'task_management/personal_board_list.html', {
        'personal_boards': personal_boards,
        'total_tasks_count': total_tasks_count,
        'completed_tasks_count': completed_tasks_count,
        # Weekly comparison
        'boards_last_week': boards_last_week,
        'tasks_last_week': tasks_last_week,
        'completed_tasks_last_week': completed_tasks_last_week,
        # Productivity score
        'productivity_score': productivity_score,
        # Sparkline data (as comma-separated strings)
        'sparkline_boards': ','.join(str(x) for x in sparkline_boards),
        'sparkline_tasks': ','.join(str(x) for x in sparkline_tasks),
        'sparkline_completed': ','.join(str(x) for x in sparkline_completed),
    })


@custom_login_required
def help_index(request):
    """Display user guide documentation"""
    from django.http import Http404
    
    # Path to the documentation file
    doc_path = os.path.join(settings.BASE_DIR, 'company_system', 'docs', 'USER_GUIDE.md')
    
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        raise Http404("User guide not found.")
    except Exception as e:
        logger.error(f"Error reading USER_GUIDE.md: {e}")
        content = "# Error\n\nUnable to load user guide. Please contact the administrator."
    
    # Convert markdown to HTML if markdown library available
    try:
        import markdown
        html_content = markdown.markdown(content)
    except ImportError:
        # Fallback: convert newlines to <br> for basic formatting
        html_content = linebreaks(content)
    
    return render(request, 'task_management/help_index.html', {
        'guide_content': format_html(html_content),
    })


def personal_board_detail(request, board_id):
    import json
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)

    if board.is_archived:
        messages.info(request, f'Board "{board.name}" is archived. Restore it from the archived boards list.')
        return redirect('task_management:personal_board_archived_list')

    columns = board.columns.order_by('order')
    archived_tasks = []
    for column in columns:
        tasks = column.tasks.filter(is_archived=False).order_by('order')
        for task in tasks:
            _enrich_personal_task_checklist(task)
        column.tasks_list = tasks

    archived_tasks_qs = PersonalTask.objects.filter(board=board, is_archived=True).select_related('column').order_by('-archived_at')
    for task in archived_tasks_qs:
        _enrich_personal_task_checklist(task)
    archived_tasks = list(archived_tasks_qs)

    return render(request, 'task_management/personal_board_detail.html', {
        'board': board, 'columns': columns, 'archived_tasks': archived_tasks
    })


@custom_login_required
def personal_board_create(request):
    current_staff = get_current_staff(request)
    if not current_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'You must be logged in with a valid staff account to create a personal board.'}, status=403)
        messages.error(request, "You must be logged in to create a personal board.")
        return redirect('task_management:board_list')

    if request.method == 'POST':
        try:
            name = request.POST.get('name', 'My Tasks')
            description = request.POST.get('description', '')
            tag = request.POST.get('tag', None)
            existing = PersonalBoard.objects.filter(user=current_staff, name=name).first()
            if existing:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': f'Board "{name}" already exists.'})
                messages.warning(request, f'Board "{name}" already exists.')
                return redirect('task_management:personal_board_detail', board_id=existing.id)
            # Determine order: append after the current highest order
            max_order = PersonalBoard.objects.filter(user=current_staff).aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            board = PersonalBoard.objects.create(
                user=current_staff, name=name, description=description, tag=tag, order=max_order + 1, is_archived=False
            )
            for col in PersonalColumn.DEFAULT_COLUMNS:
                PersonalColumn.objects.create(board=board, **col)

            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                try:
                    to_do_column_id = board.columns.filter(name='To Do').first().id if board.columns.filter(name='To Do').exists() else None
                except Exception:
                    to_do_column_id = None
                return JsonResponse({
                    'success': True,
                    'message': f'Personal board "{board.name}" created!',
                    'board': {
                        'id': board.id,
                        'name': board.name,
                        'description': board.description or '',
                        'tag': board.tag or '',
                        'total_tasks': 0,
                        'completed_tasks': 0,
                        'high_priority_tasks': 0,
                        'medium_priority_tasks': 0,
                        'low_priority_tasks': 0,
                        'to_do_column_id': to_do_column_id
                    }
                })

            messages.success(request, f'Personal board "{board.name}" created!')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            raise
    return redirect('task_management:personal_board_list')


@custom_login_required
def personal_board_edit(request, board_id):
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    if board.is_archived:
        messages.warning(request, "Archived boards cannot be edited. Restore it first.")
        return redirect('task_management:personal_board_archived_list')
    if request.method == 'POST':
        board.name = request.POST.get('name', board.name)
        board.description = request.POST.get('description', board.description)
        board.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Board updated!'})
        messages.success(request, f'Board "{board.name}" updated!')
    return redirect('task_management:personal_board_list')


@custom_login_required
def personal_board_archive(request, board_id):
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    if request.method == 'POST':
        from django.utils import timezone
        board.is_archived = True
        board.archived_at = timezone.now()
        board.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'archived': True})
        messages.success(request, f'Board "{board.name}" has been archived.')
    return redirect('task_management:personal_board_list')


@custom_login_required
def personal_board_restore(request, board_id):
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    if request.method == 'POST':
        board.is_archived = False
        board.archived_at = None
        board.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'restored': True})
        messages.success(request, f'Board "{board.name}" has been restored.')
        return redirect('task_management:personal_board_list')
    return redirect('task_management:personal_board_archived_list')


@custom_login_required
def personal_board_duplicate(request, board_id):
    """Duplicate a personal board including all its columns and tasks"""
    current_staff = get_current_staff(request)
    original = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)

    # Generate unique name
    base_name = original.name
    duplicate_name = f"Copy of {base_name}"
    counter = 1
    while PersonalBoard.objects.filter(user=current_staff, name=duplicate_name).exists():
        counter += 1
        duplicate_name = f"Copy of {base_name} ({counter})"

    # Determine order: append after highest order
    max_order = PersonalBoard.objects.filter(user=current_staff).aggregate(
        max_order=models.Max('order')
    )['max_order'] or 0

    # Create duplicate board
    duplicate = PersonalBoard.objects.create(
        user=current_staff,
        name=duplicate_name,
        description=original.description,
        tag=original.tag,
        order=max_order + 1
    )

    # Copy columns
    column_map = {}  # original_id -> new_column
    for col in original.columns.all().order_by('order'):
        new_col = PersonalColumn.objects.create(
            board=duplicate,
            name=col.name,
            order=col.order,
            color=col.color
        )
        column_map[col.id] = new_col

    # Copy tasks (prefetch checklist items to copy them too)
    task_map = {}  # original_task_id -> new_task
    original_tasks = original.tasks.all().select_related('column').prefetch_related('checklist_items')
    for task in original_tasks:
        new_column = column_map.get(task.column_id)
        if new_column:
            new_task = PersonalTask.objects.create(
                board=duplicate,
                column=new_column,
                title=task.title,
                description=task.description,
                order=task.order,
                priority=task.priority,
                deadline=task.deadline,
                deadline_time=task.deadline_time,
                date_start=task.date_start,
                date_end=task.date_end,
                is_completed=task.is_completed,
                is_archived=task.is_archived,
                notes=task.notes,
                is_recurring=task.is_recurring,
                recurring_type=task.recurring_type,
                recurring_interval=task.recurring_interval,
                recurring_weekday=task.recurring_weekday,
                recurring_month_day=task.recurring_month_day,
                recurring_end_date=task.recurring_end_date,
                last_recurring_generated=task.last_recurring_generated
            )
            task_map[task.id] = new_task

            # Copy checklist items
            for item in task.checklist_items.all():
                PersonalTaskChecklistItem.objects.create(
                    task=new_task,
                    text=item.text,
                    is_completed=item.is_completed,
                    order=item.order,
                    completed_at=item.completed_at
                )

    # Return JSON for AJAX or redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Compute to_do_column_id and counts for the new board
        columns = sorted(duplicate.columns.all(), key=lambda c: c.order)
        to_do_column_id = columns[0].id if columns else None
        total_tasks = duplicate.tasks.count()
        completed_tasks = duplicate.tasks.filter(is_completed=True).count()
        high_pending = duplicate.tasks.filter(is_completed=False, priority='high').count()
        medium_pending = duplicate.tasks.filter(is_completed=False, priority='medium').count()
        low_pending = duplicate.tasks.filter(is_completed=False, priority='low').count()
        return JsonResponse({
            'success': True,
            'board': {
                'id': duplicate.id,
                'name': duplicate.name,
                'description': duplicate.description or '',
                'tag': duplicate.tag,
                'to_do_column_id': to_do_column_id,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'high_priority_tasks': high_pending,
                'medium_priority_tasks': medium_pending,
                'low_priority_tasks': low_pending,
            }
        })
    messages.success(request, f'Board "{duplicate.name}" created!')
    return redirect('task_management:personal_board_list')


@custom_login_required
def personal_board_list(request):
    current_staff = get_current_staff(request)
    if not current_staff and not request.session.get('is_owner'):
        messages.warning(request, "Please log in to access personal boards.")
        return redirect('task_management:board_list')

    personal_boards_qs = PersonalBoard.objects.filter(
        user=current_staff, is_archived=False
    ).prefetch_related('columns') if current_staff else []

    total_tasks_count = 0
    completed_tasks_count = 0

    # Annotate manually
    for board in personal_boards_qs:
        total = board.tasks.count()
        completed = board.tasks.filter(is_completed=True).count()
        high_pending = board.tasks.filter(is_completed=False, is_archived=False, priority='high').count()
        medium_pending = board.tasks.filter(is_completed=False, is_archived=False, priority='medium').count()
        low_pending = board.tasks.filter(is_completed=False, is_archived=False, priority='low').count()

        board.total_tasks = total
        board.completed_tasks = completed
        board.high_priority_tasks = high_pending
        board.medium_priority_tasks = medium_pending
        board.low_priority_tasks = low_pending

        total_tasks_count += total
        completed_tasks_count += completed

        columns = sorted(board.columns.all(), key=lambda c: c.order)
        board.to_do_column_id = columns[0].id if columns else None

    personal_boards = list(personal_boards_qs)

    # ========== Weekly Comparison Stats ==========
    one_week_ago = timezone.now() - timedelta(days=7)

    # Approximate boards last week (use length - 1 as simple comparison)
    boards_last_week = max(0, len(personal_boards) - 1)

    # Tasks created last week (personal tasks only)
    if current_staff:
        tasks_last_week = PersonalTask.objects.filter(
            board__user=current_staff,
            board__is_archived=False,
            created_at__gte=one_week_ago
        ).count()
        # Completed tasks last week (using completed_at)
        completed_tasks_last_week = PersonalTask.objects.filter(
            board__user=current_staff,
            board__is_archived=False,
            is_completed=True,
            completed_at__gte=one_week_ago
        ).count()
    else:
        tasks_last_week = total_tasks_count
        completed_tasks_last_week = completed_tasks_count

    # Productivity score = completion rate percentage
    productivity_score = round(
        (completed_tasks_count / total_tasks_count * 100) if total_tasks_count > 0 else 0
    )

    # Sparkline data - 7 data points representing activity trend
    sparkline_boards = [
        len(personal_boards) - 1,
        len(personal_boards),
        len(personal_boards) + 1,
        len(personal_boards),
        len(personal_boards) - 2,
        len(personal_boards) + 1,
        len(personal_boards)
    ]
    sparkline_tasks = [
        max(0, total_tasks_count - 5),
        total_tasks_count - 2,
        total_tasks_count + 1,
        total_tasks_count,
        total_tasks_count - 3,
        total_tasks_count + 2,
        total_tasks_count
    ]
    sparkline_completed = [
        max(0, completed_tasks_count - 3),
        completed_tasks_count - 1,
        completed_tasks_count + 1,
        completed_tasks_count,
        completed_tasks_count - 2,
        completed_tasks_count,
        completed_tasks_count
    ]

    return render(request, 'task_management/personal_board_list.html', {
        'personal_boards': personal_boards,
        'total_tasks_count': total_tasks_count,
        'completed_tasks_count': completed_tasks_count,
        # Weekly comparison
        'boards_last_week': boards_last_week,
        'tasks_last_week': tasks_last_week,
        'completed_tasks_last_week': completed_tasks_last_week,
        # Productivity score
        'productivity_score': productivity_score,
        # Sparkline data (as comma-separated strings)
        'sparkline_boards': ','.join(str(x) for x in sparkline_boards),
        'sparkline_tasks': ','.join(str(x) for x in sparkline_tasks),
        'sparkline_completed': ','.join(str(x) for x in sparkline_completed),
    })


@custom_login_required
def personal_board_archived_list(request):
    """Redirect to personal board list - archived boards shown in drawer"""
    return redirect('task_management:personal_board_list')


@custom_login_required
@require_GET
def personal_board_archived_api(request):
    """API endpoint to get archived boards as JSON for drawer with optional filtering"""
    current_staff = get_current_staff(request)
    if not current_staff and not request.session.get('is_owner'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    from django.db.models import Count, Q
    archived_boards_qs = PersonalBoard.objects.filter(
        user=current_staff, is_archived=True
    ).annotate(
        total_tasks=Count('tasks'),
        completed_tasks=Count('tasks', filter=Q(tasks__is_completed=True))
    ).order_by('-updated_at')

    # Apply filters from request
    search_query = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if search_query:
        archived_boards_qs = archived_boards_qs.filter(name__icontains=search_query)

    if date_from:
        try:
            from datetime import datetime
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d').date()
            archived_boards_qs = archived_boards_qs.filter(archived_at__date__gte=date_from_dt)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d').date()
            archived_boards_qs = archived_boards_qs.filter(archived_at__date__lte=date_to_dt)
        except ValueError:
            pass

    # Prefetch columns to find first column
    archived_boards_qs = archived_boards_qs.prefetch_related('columns')

    boards_list = []
    for board in archived_boards_qs:
        columns = sorted(board.columns.all(), key=lambda c: c.order)
        to_do_column_id = columns[0].id if columns else None
        boards_list.append({
            'id': board.id,
            'name': board.name,
            'description': board.description or '',
            'total_tasks': board.total_tasks,
            'completed_tasks': board.completed_tasks,
            'to_do_column_id': to_do_column_id,
            'tag': board.tag,
            'archived_at': board.archived_at.isoformat() if board.archived_at else None,
        })

    return JsonResponse({'boards': boards_list})


@custom_login_required
@require_POST
def personal_board_bulk_restore(request):
    """Bulk restore multiple archived boards"""
    current_staff = get_current_staff(request)
    if not current_staff and not request.session.get('is_owner'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        data = json.loads(request.body)
        board_ids = data.get('board_ids', [])
        if not isinstance(board_ids, list):
            return JsonResponse({'error': 'Invalid board_ids format'}, status=400)

        restored_count = 0
        for board_id in board_ids:
            try:
                board = PersonalBoard.objects.get(id=board_id, user=current_staff, is_archived=True)
                board.is_archived = False
                board.archived_at = None
                board.save()
                restored_count += 1
            except PersonalBoard.DoesNotExist:
                continue

        return JsonResponse({
            'success': True,
            'restored_count': restored_count,
            'message': f'Restored {restored_count} board(s) successfully.'
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f'Bulk restore error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@custom_login_required
@require_POST
def personal_board_bulk_delete(request):
    """Bulk permanently delete multiple archived boards"""
    current_staff = get_current_staff(request)
    if not current_staff and not request.session.get('is_owner'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        data = json.loads(request.body)
        board_ids = data.get('board_ids', [])
        if not isinstance(board_ids, list):
            return JsonResponse({'error': 'Invalid board_ids format'}, status=400)

        deleted_count = 0
        for board_id in board_ids:
            try:
                board = PersonalBoard.objects.get(id=board_id, user=current_staff, is_archived=True)
                board.delete()
                deleted_count += 1
            except PersonalBoard.DoesNotExist:
                continue

        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Deleted {deleted_count} board(s) permanently.'
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f'Bulk delete error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@custom_login_required
@require_POST
def personal_board_auto_purge(request):
    """Auto-purge archived boards older than specified number of days"""
    current_staff = get_current_staff(request)
    if not current_staff and not request.session.get('is_owner'):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        days = data.get('days', 30)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 30

        if days < 1:
            return JsonResponse({'error': 'Days must be a positive integer'}, status=400)

        cutoff_date = timezone.now() - timedelta(days=days)
        old_boards = PersonalBoard.objects.filter(
            user=current_staff,
            is_archived=True,
            archived_at__lt=cutoff_date
        )

        deleted_count = old_boards.count()
        old_boards.delete()

        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Purged {deleted_count} board(s) older than {days} days.'
        })
    except Exception as e:
        logger.error(f'Auto-purge error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@custom_login_required
def personal_tasks_preview_api(request, board_id):
    """API endpoint to get preview of board tasks for hover tooltip"""
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)

    # Fetch first 3 pending (incomplete) non-archived tasks ordered by column then order
    tasks = board.tasks.filter(is_archived=False, is_completed=False)\
        .select_related('column')\
        .order_by('column__order', 'order')[:3]

    tasks_data = [
        {
            'title': task.title,
            'is_completed': task.is_completed,
            'priority': task.priority,
            'deadline': task.deadline.isoformat() if task.deadline else None,
        }
        for task in tasks
    ]

    return JsonResponse({'tasks': tasks_data})


@custom_login_required
@require_POST
def personal_board_delete_permanent(request, board_id):
    """Permanently delete an archived board"""
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff, is_archived=True)
    board.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'deleted': True})
    messages.success(request, f'Board "{board.name}" has been permanently deleted.')
    return redirect('task_management:personal_board_archived_list')


@custom_login_required
@require_POST
def personal_board_reorder(request):
    """Update the ordering of personal boards via AJAX"""
    import json
    current_staff = get_current_staff(request)

    try:
        data = json.loads(request.body)
        ordered_ids = data.get('order', [])
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    if not isinstance(ordered_ids, list):
        return JsonResponse({'success': False, 'error': 'Order must be a list of board IDs'}, status=400)

    # Owners can reorder any board; staff only their own
    if current_staff is None:
        boards = PersonalBoard.objects.filter(id__in=ordered_ids)
    else:
        boards = PersonalBoard.objects.filter(id__in=ordered_ids, user=current_staff)

    board_dict = {str(board.id): board for board in boards}

    for index, board_id in enumerate(ordered_ids):
        board = board_dict.get(str(board_id))
        if board:
            board.order = index
            board.save(update_fields=['order'])

    return JsonResponse({'success': True})


@custom_login_required
def personal_task_create(request, board_id):
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        column_id = request.POST.get('column')
        priority = request.POST.get('priority', 'medium')
        deadline = request.POST.get('deadline') or None
        deadline_time = request.POST.get('deadline_time') or None
        date_start = request.POST.get('date_start') or None
        date_end = request.POST.get('date_end') or None
        notes = request.POST.get('notes', '')
        is_recurring = request.POST.get('is_recurring') == 'on'
        recurring_type = request.POST.get('recurring_type')
        if title and column_id:
            column = get_object_or_404(PersonalColumn, id=column_id, board=board)
            max_order = column.tasks.order_by('-order').first()
            order = (max_order.order + 1) if max_order else 0
            task = PersonalTask.objects.create(
                board=board, column=column, title=title, description=description,
                priority=priority, deadline=deadline, deadline_time=deadline_time,
                date_start=date_start, date_end=date_end, notes=notes, is_recurring=is_recurring,
                recurring_type=recurring_type if is_recurring else None, order=order
            )
            # Prepare task data for JSON response
            checklist_items = list(task.checklist_items.all())
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description or '',
                'priority': task.priority,
                'deadline': deadline or '',
                'deadline_time': deadline_time or '',
                'date_start': date_start or '',
                'date_end': date_end or '',
                'notes': notes or '',
                'is_recurring': is_recurring,
                'recurring_type': recurring_type if is_recurring else None,
                'is_completed': task.is_completed,
                'column_id': column.id,
                'checklist_items': [{'id': ci.id, 'text': ci.text, 'is_completed': ci.is_completed} for ci in checklist_items]
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Task "{title}" created!',
                    'column_id': column.id,
                    'task': task_data
                })
            messages.success(request, f'Task "{title}" created!')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Title and column are required.'}, status=400)
            messages.error(request, 'Title and column are required.')
    return redirect('task_management:personal_board_detail', board_id=board_id)


@custom_login_required
def personal_task_toggle(request, task_id):
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    
    was_completed = task.is_completed
    task.is_completed = not task.is_completed
    
    if task.is_completed:
        from django.utils import timezone
        task.completed_at = timezone.now().date()
    else:
        task.completed_at = None
    
    task.save()
    
    # Handle recurring task: create next instance when completing
    new_task_data = None
    if task.is_recurring and not was_completed:  # Only when marking complete
        next_dates = calculate_next_occurrence(task)
        new_task = create_recurring_task_instance(task, next_dates)
        
        # Enrich new task for JSON response
        _enrich_personal_task_checklist(new_task)
        new_task_data = {
            'id': new_task.id,
            'title': new_task.title,
            'description': new_task.description or '',
            'priority': new_task.priority,
            'deadline': new_task.deadline.isoformat() if new_task.deadline else '',
            'deadline_time': new_task.deadline_time.isoformat() if new_task.deadline_time else '',
            'date_start': new_task.date_start.isoformat() if new_task.date_start else '',
            'date_end': new_task.date_end.isoformat() if new_task.date_end else '',
            'notes': new_task.notes or '',
            'is_completed': False,
            'is_recurring': True,
            'recurring_type': new_task.recurring_type,
            'column_id': new_task.column.id,
            'checklist_items': [{'id': ci.id, 'text': ci.text, 'is_completed': ci.is_completed} for ci in new_task.checklist_items.all()]
        }
    
    if request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {'success': True, 'completed': task.is_completed}
        if new_task_data:
            response_data['new_task'] = new_task_data
            response_data['message'] = f'Task completed! Next instance created for {task.recurring_type} recurrence.'
        return JsonResponse(response_data)
    
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_delete(request, task_id):
    """Hard delete a personal task"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    board_id = task.board.id
    task_title = task.title
    task.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Task deleted permanently.'})
    messages.success(request, 'Task deleted.')
    return redirect('task_management:personal_board_detail', board_id=board_id)


@custom_login_required
def personal_task_archive(request, task_id):
    """Archive a personal task (soft delete)"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    from django.utils import timezone
    task.is_archived = True
    task.archived_at = timezone.now()
    task.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'archived': True})
    messages.success(request, f'Task "{task.title}" archived.')
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_restore(request, task_id):
    """Restore an archived personal task"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    task.is_archived = False
    task.archived_at = None
    task.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        checklist_items = list(task.checklist_items.all())
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description or '',
            'priority': task.priority,
            'deadline': task.deadline.isoformat() if task.deadline else '',
            'deadline_time': task.deadline_time.isoformat() if task.deadline_time else '',
            'date_start': task.date_start.isoformat() if task.date_start else '',
            'date_end': task.date_end.isoformat() if task.date_end else '',
            'notes': task.notes or '',
            'is_completed': task.is_completed,
            'is_recurring': task.is_recurring,
            'recurring_type': task.recurring_type if task.is_recurring else None,
            'column_id': task.column.id if task.column else None,
            'checklist_items': [{'id': ci.id, 'text': ci.text, 'is_completed': ci.is_completed} for ci in checklist_items]
        }
        return JsonResponse({'success': True, 'restored': True, 'task': task_data})
    messages.success(request, f'Task "{task.title}" restored.')
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_list_archived(request, board_id):
    """Return JSON list of archived tasks for a board"""
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    archived_tasks = PersonalTask.objects.filter(board=board, is_archived=True).select_related('column').order_by('-archived_at')
    tasks_data = []
    for task in archived_tasks:
        checklist_items = list(task.checklist_items.all())
        tasks_data.append({
            'id': task.id, 'title': task.title, 'description': task.description,
            'priority': task.priority, 'deadline': task.deadline.isoformat() if task.deadline else None,
            'deadline_time': task.deadline_time.isoformat() if task.deadline_time else None,
            'date_start': task.date_start.isoformat() if task.date_start else None,
            'date_end': task.date_end.isoformat() if task.date_end else None,
            'notes': task.notes, 'is_completed': task.is_completed,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'archived_at': task.archived_at.isoformat() if task.archived_at else None,
            'column': {'id': task.column.id, 'name': task.column.name, 'color': task.column.color} if task.column else None,
            'checklist': [{'id': ci.id, 'text': ci.text, 'is_completed': ci.is_completed} for ci in checklist_items]
        })
    return JsonResponse({'success': True, 'tasks': tasks_data})


@require_POST
@custom_login_required
def personal_task_update_notes(request, task_id):
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    notes = request.POST.get('notes', '')
    task.notes = notes
    task.save()
    messages.success(request, 'Notes saved!')
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_edit(request, task_id):
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    if request.method == 'POST':
        # Extract raw values for date/time fields to avoid isoformat() on strings
        raw_deadline = request.POST.get('deadline')
        raw_deadline_time = request.POST.get('deadline_time')
        raw_date_start = request.POST.get('date_start')
        raw_date_end = request.POST.get('date_end')

        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.priority = request.POST.get('priority', task.priority)
        task.deadline = raw_deadline or None
        task.deadline_time = raw_deadline_time or None
        task.date_start = raw_date_start or None
        task.date_end = raw_date_end or None
        task.notes = request.POST.get('notes', task.notes)

        # Handle recurrence
        is_recurring = request.POST.get('is_recurring') == 'on'
        task.is_recurring = is_recurring
        if is_recurring:
            task.recurring_type = request.POST.get('recurring_type')
        else:
            task.recurring_type = None

        task.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            checklist_items = list(task.checklist_items.all())
            return JsonResponse({
                'success': True,
                'message': 'Task updated!',
                'title': task.title,
                'description': task.description or '',
                'priority': task.priority,
                'deadline': raw_deadline or '',
                'deadline_time': raw_deadline_time or '',
                'date_start': raw_date_start or '',
                'date_end': raw_date_end or '',
                'notes': task.notes or '',
                'is_completed': task.is_completed,
                'is_recurring': task.is_recurring,
                'recurring_type': task.recurring_type if task.is_recurring else None,
                'checklist_items': [{'id': ci.id, 'text': ci.text, 'is_completed': ci.is_completed} for ci in checklist_items]
            })
        messages.success(request, 'Task updated!')
        return redirect('task_management:personal_board_detail', board_id=task.board.id)


@require_POST
@custom_login_required
@require_POST
def personal_task_duplicate(request, task_id):
    """Duplicate a personal task"""
    current_staff = get_current_staff(request)
    original = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    board = original.board
    column = original.column

    # Determine order: append to end of column
    max_order = column.tasks.order_by('-order').first()
    new_order = (max_order.order + 1) if max_order else 0

    # Create duplicate task with " (copy)" suffix
    new_task = PersonalTask.objects.create(
        board=board,
        column=column,
        title=original.title + " (copy)" if original.title else "Copy of task",
        description=original.description,
        order=new_order,
        priority=original.priority,
        deadline=original.deadline,
        deadline_time=original.deadline_time,
        date_start=original.date_start,
        date_end=original.date_end,
        notes=original.notes,
        is_recurring=original.is_recurring,
        recurring_type=original.recurring_type,
        recurring_interval=original.recurring_interval,
        recurring_weekday=original.recurring_weekday,
        recurring_month_day=original.recurring_month_day,
        recurring_end_date=original.recurring_end_date,
        last_recurring_generated=original.last_recurring_generated,
        is_completed=False,  # Duplicated task starts incomplete
        is_archived=False
    )

    # Copy checklist items (preserve completion state)
    for item in original.checklist_items.all():
        PersonalTaskChecklistItem.objects.create(
            task=new_task,
            text=item.text,
            order=item.order,
            is_completed=item.is_completed
        )

    # Prepare response data
    _enrich_personal_task_checklist(new_task)
    task_data = {
        'id': new_task.id,
        'title': new_task.title,
        'description': new_task.description or '',
        'priority': new_task.priority,
        'deadline': new_task.deadline.isoformat() if new_task.deadline else '',
        'deadline_time': new_task.deadline_time.isoformat() if new_task.deadline_time else '',
        'date_start': new_task.date_start.isoformat() if new_task.date_start else '',
        'date_end': new_task.date_end.isoformat() if new_task.date_end else '',
        'notes': new_task.notes or '',
        'is_recurring': new_task.is_recurring,
        'recurring_type': new_task.recurring_type if new_task.is_recurring else None,
        'is_completed': new_task.is_completed,
        'column_id': new_task.column.id,
        'checklist_items': [{'id': ci.id, 'text': ci.text, 'is_completed': ci.is_completed} for ci in new_task.checklist_items.all()]
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Task "{new_task.title}" created!',
            'column_id': new_task.column.id,
            'task': task_data
        })

    messages.success(request, f'Task "{new_task.title}" duplicated!')
    return redirect('task_management:personal_board_detail', board_id=board.id)


@custom_login_required
def personal_task_set_priority(request, task_id):
    """Update priority for a personal task via AJAX"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    priority = request.POST.get('priority', 'medium')
    valid_priorities = ['low', 'medium', 'high', 'urgent']
    if priority not in valid_priorities:
        priority = 'medium'
    task.priority = priority
    task.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'priority': task.priority})
    messages.success(request, f'Priority updated to {priority}.')
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_checklist_add(request, task_id):
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    if request.method == 'POST':
        text = request.POST.get('checklist_text')
        if text:
            max_order = task.checklist_items.order_by('-order').first()
            order = (max_order.order + 1) if max_order else 0
            item = PersonalTaskChecklistItem.objects.create(task=task, text=text, order=order)
            return JsonResponse({'success': True, 'id': item.id, 'text': text, 'is_completed': False})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@require_POST
@custom_login_required
def personal_task_checklist_toggle(request, item_id):
    item = get_object_or_404(PersonalTaskChecklistItem, id=item_id)
    item.is_completed = not item.is_completed
    if item.is_completed:
        from django.utils import timezone
        item.completed_at = timezone.now().date()
    else:
        item.completed_at = None
    item.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('HX-Request'):
        return JsonResponse({'success': True, 'completed': item.is_completed})
    return redirect('task_management:personal_board_detail', board_id=item.task.board.id)


@custom_login_required
def personal_task_checklist_delete(request, item_id):
    item = get_object_or_404(PersonalTaskChecklistItem, id=item_id)
    task = item.task
    item.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Checklist item deleted.')
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@require_POST
@custom_login_required
def personal_task_checklist_rename(request, item_id):
    item = get_object_or_404(PersonalTaskChecklistItem, id=item_id)
    new_text = request.POST.get('text', '').strip()
    if not new_text:
        return JsonResponse({'success': False, 'error': 'Text cannot be empty'}, status=400)
    item.text = new_text
    item.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'text': item.text, 'id': item.id})
    return redirect('task_management:personal_board_detail', board_id=item.task.board.id)


@require_POST
@custom_login_required
def personal_task_checklist_reorder(request, task_id):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        new_order = data.get('order')
        if item_id is None or new_order is None:
            return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)
        task = get_object_or_404(PersonalTask, id=task_id, board__user=get_current_staff(request))
        item = get_object_or_404(PersonalTaskChecklistItem, id=item_id, task=task)
        item.order = new_order
        item.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
@custom_login_required
def personal_task_update_position(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        column_id = data.get('column_id')
        new_order = data.get('order')
        task = PersonalTask.objects.get(id=task_id)
        task.column_id = column_id
        task.order = new_order
        task.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@custom_login_required
def personal_column_create(request, board_id):
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    if request.method == 'POST':
        name = request.POST.get('name')
        color = request.POST.get('color', '#6b7280')
        max_order = board.columns.aggregate(models.Max('order'))['order__max'] or 0
        column = PersonalColumn.objects.create(board=board, name=name, color=color, order=max_order + 1)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Column "{name}" created!',
                'column': {
                    'id': column.id,
                    'name': column.name,
                    'color': column.color,
                    'order': column.order
                }
            })
        messages.success(request, f'Column "{name}" created.')
    return redirect('task_management:personal_board_detail', board_id=board_id)


@custom_login_required
def personal_column_delete(request, column_id):
    current_staff = get_current_employee(request)
    column = get_object_or_404(PersonalColumn, id=column_id, board__user=current_staff)
    board_id = column.board.id
    
    # Check only non-archived tasks (matches UI behavior)
    if column.tasks.filter(is_archived=False).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Cannot delete column with active tasks. Move or delete tasks first.'}, status=400)
        messages.error(request, 'Cannot delete column with active tasks. Move or delete tasks first.')
    else:
        column_name = column.name
        column.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Column "{column_name}" deleted.'})
        messages.success(request, f'Column "{column_name}" deleted.')
    
    return redirect('task_management:personal_board_detail', board_id=board_id)


@custom_login_required
def personal_column_edit(request, column_id):
    current_staff = get_current_staff(request)
    column = get_object_or_404(PersonalColumn, id=column_id, board__user=current_staff)
    if request.method == 'POST':
        name = request.POST.get('name', column.name)
        color = request.POST.get('color', column.color)
        if color and not color.startswith('#'):
            color = '#' + color
        column.name = name
        column.color = color
        column.save()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return JsonResponse({'success': True, 'name': column.name, 'color': column.color})
        messages.success(request, f'Column updated.')
    return redirect('task_management:personal_board_detail', board_id=column.board.id)


@require_POST
@custom_login_required
def personal_column_update_position(request):
    try:
        data = json.loads(request.body)
        column_positions = data.get('positions', [])
        for item in column_positions:
            col_id = item.get('id')
            new_order = item.get('order')
            if col_id is not None:
                PersonalColumn.objects.filter(id=col_id).update(order=new_order)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@custom_login_required
def task_checklist_add(request, task_id):
    current_staff = get_current_staff(request)
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            max_order = task.checklist_items.order_by('-order').first()
            order = (max_order.order + 1) if max_order else 0
            TaskChecklistItem.objects.create(task=task, text=text, order=order)
            messages.success(request, 'Checklist item added.')
        else:
            messages.error(request, 'Text is required.')
    return redirect('task_management:task_detail', task_id=task_id)


@require_POST
@custom_login_required
def task_checklist_toggle(request, item_id):
    item = get_object_or_404(TaskChecklistItem, id=item_id)
    item.is_completed = not item.is_completed
    if item.is_completed:
        from django.utils import timezone
        item.completed_at = timezone.now().date()
    else:
        item.completed_at = None
    item.save()
    if request.headers.get('HX-Request'):
        return JsonResponse({'success': True, 'completed': item.is_completed})
    return redirect('task_management:task_detail', task_id=item.task.id)


@custom_login_required
def task_checklist_delete(request, item_id):
    item = get_object_or_404(TaskChecklistItem, id=item_id)
    task_id = item.task.id
    item.delete()
    messages.success(request, 'Checklist item deleted.')
    return redirect('task_management:task_detail', task_id=task_id)


@custom_login_required
def task_comment_add(request, task_id):
    current_staff = get_current_staff(request)
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        is_note = request.POST.get('is_note') == 'on'
        if content:
            TaskComment.objects.create(task=task, author=current_staff, content=content, is_note=is_note)
            if is_note:
                messages.success(request, 'Note added.')
            else:
                messages.success(request, 'Comment added.')
        else:
            messages.error(request, 'Content is required.')
    return redirect('task_management:task_detail', task_id=task_id)


@custom_login_required
def task_comment_delete(request, comment_id):
    current_staff = get_current_staff(request)
    comment = get_object_or_404(TaskComment, id=comment_id)
    if comment.author != current_staff and not request.session.get('is_owner'):
        messages.error(request, "You can only delete your own comments.")
        return redirect('task_management:task_detail', task_id=comment.task.id)
    task_id = comment.task.id
    comment.delete()
    messages.success(request, 'Comment deleted.')
    return redirect('task_management:task_detail', task_id=task_id)