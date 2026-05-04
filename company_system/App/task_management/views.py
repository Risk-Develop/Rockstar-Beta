import logging
import json

logger = logging.getLogger(__name__)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
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
            
            # Allow if: owner, task creator, or assigned user
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
            
            # Allow if: owner, task creator, or board creator
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
    is_owner = request.session.get('is_owner', False)
    
    if is_owner or emp_num == 'OWNER':
        return None
    
    if emp_num:
        try:
            return Staff.objects.get(employee_number=emp_num)
        except Staff.DoesNotExist:
            return None
    return None


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
            
            # Seed default columns
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
            
            # Check if roadmap_id is provided
            roadmap_id = request.POST.get('roadmap_id')
            if roadmap_id:
                task.roadmap_id = roadmap_id
            
            # Set order to be last in column
            max_order = task.column.tasks.order_by('-order').first()
            task.order = (max_order.order + 1) if max_order else 0
            
            task.save()
            
            # Log audit for task creation
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
                f"Updated: {old_data} → {new_data}", request=request)
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
    """API to update task column and order via drag-drop"""
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
        
        # Log audit for column move
        if old_column_id != column_id:
            new_column = KanbanColumn.objects.get(id=column_id)
            user = get_current_staff(request)
            log_audit(task, 'moved', user,
                f"Moved from {old_column.name} to {new_column.name}",
                from_col=old_column, to_col=new_column, request=request)
        
        # Reorder tasks in the new column
        if old_column_id != column_id:
            # Tasks in old column - reassign order
            old_column_tasks = Task.objects.filter(column_id=old_column_id).order_by('order')
            for i, t in enumerate(old_column_tasks):
                if t.order != i:
                    t.order = i
                    t.save()
        
        # Tasks in new column - reassign order
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
    """API to get all tasks for a board (for HTMX partial updates)"""
    board = get_object_or_404(KanbanBoard, id=board_id)
    columns = board.columns.filter(is_active=True).order_by('order')
    
    for column in columns:
        column.tasks_list = column.tasks.order_by('order')
    
    return render(request, 'task_management/includes/_columns_partial.html', {
        'columns': columns,
        'all_staff': Staff.objects.filter(status='active')
    })


# Roadmap Views

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
    # Show tasks from the board (not just tasks with roadmap_id set)
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
    """Timeline view using FullCalendar"""
    import logging
    logger = logging.getLogger(__name__)
    
    roadmap = get_object_or_404(Roadmap, id=roadmap_id)
    # Get all tasks from the board (not just roadmap tasks)
    tasks = Task.objects.filter(column__board=roadmap.board).select_related('column').all()
    
    logger.error(f"Timeline view - Tasks count: {tasks.count()}, Roadmap: {roadmap.name}, Board: {roadmap.board.name}")
    
    calendar_events = []
    
    for task in tasks:
        if task.deadline:
            event = {
                'id': task.id,
                'title': task.title,
                'start': task.deadline.isoformat(),
                'className': 'priority-' + task.priority
            }
            calendar_events.append(event)
        else:
            event = {
                'id': task.id,
                'title': task.title + ' (No deadline)',
                'start': roadmap.start_date.isoformat(),
                'className': 'priority-' + task.priority
            }
            calendar_events.append(event)
    
    return render(request, 'task_management/timeline.html', {
        'roadmap': roadmap,
        'tasks': tasks,
        'calendar_events': json.dumps(calendar_events)
    })


# ========== PERSONAL PRODUCTIVITY SYSTEM VIEWS ==========

@custom_login_required
def personal_board_list(request):
    """List all personal boards for current user"""
    current_staff = get_current_staff(request)
    if not current_staff and not request.session.get('is_owner'):
        messages.warning(request, "Please log in to access personal boards.")
        return redirect('task_management:board_list')
    
    # Get or create default personal board for user
    from django.db.models import Count, Q
    personal_boards = PersonalBoard.objects.filter(user=current_staff).annotate(
        total_tasks=Count('tasks'),
        completed_tasks=Count('tasks', filter=Q(tasks__is_completed=True))
    ) if current_staff else []
    
    # Compute aggregate totals
    total_tasks_count = sum(board.total_tasks for board in personal_boards)
    completed_tasks_count = sum(board.completed_tasks for board in personal_boards)
    
    return render(request, 'task_management/personal_board_list.html', {
        'personal_boards': personal_boards,
        'total_tasks_count': total_tasks_count,
        'completed_tasks_count': completed_tasks_count,
    })


@custom_login_required
def personal_board_detail(request, board_id):
    """View personal kanban board"""
    import json
    
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    columns = board.columns.order_by('order')
    
    for column in columns:
        tasks = column.tasks.order_by('order')
        for task in tasks:
            checklist_items = list(task.checklist_items.all())
            task.checklist_items_json = json.dumps([
                {'id': item.id, 'text': item.text, 'is_completed': item.is_completed}
                for item in checklist_items
            ])
        column.tasks_list = tasks
    
    return render(request, 'task_management/personal_board_detail.html', {
        'board': board,
        'columns': columns
    })


@custom_login_required
def personal_board_create(request):
    """Create a new personal board"""
    current_staff = get_current_staff(request)
    if not current_staff:
        messages.error(request, "You must be logged in to create a personal board.")
        return redirect('task_management:board_list')
    
    if request.method == 'POST':
        name = request.POST.get('name', 'My Tasks')
        description = request.POST.get('description', '')
        
        # Check if board already exists for this user
        existing = PersonalBoard.objects.filter(user=current_staff, name=name).first()
        if existing:
            messages.warning(request, f'Board "{name}" already exists.')
            return redirect('task_management:personal_board_detail', board_id=existing.id)
        
        board = PersonalBoard.objects.create(
            user=current_staff,
            name=name,
            description=description
        )
        
        # Create default columns
        for col in PersonalColumn.DEFAULT_COLUMNS:
            PersonalColumn.objects.create(board=board, **col)
        
        messages.success(request, f'Personal board "{board.name}" created!')
    
    return redirect('task_management:personal_board_list')


@custom_login_required
def personal_board_edit(request, board_id):
    """Edit a personal board's name and description"""
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    
    if request.method == 'POST':
        name = request.POST.get('name', board.name)
        description = request.POST.get('description', board.description)
        
        board.name = name
        board.description = description
        board.save()
        
        messages.success(request, f'Board "{board.name}" updated!')
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True, 'message': 'Board updated!'})
    
    return redirect('task_management:personal_board_list')


@custom_login_required
def personal_task_create(request, board_id):
    """Create a personal task"""
    current_staff = get_current_staff(request)
    board = get_object_or_404(PersonalBoard, id=board_id, user=current_staff)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        column_id = request.POST.get('column')
        priority = request.POST.get('priority', 'medium')
        deadline = request.POST.get('deadline') or None
        date_start = request.POST.get('date_start') or None
        date_end = request.POST.get('date_end') or None
        notes = request.POST.get('notes', '')
        is_recurring = request.POST.get('is_recurring') == 'on'
        recurring_type = request.POST.get('recurring_type')
        
        if title and column_id:
            column = get_object_or_404(PersonalColumn, id=column_id, board=board)
            max_order = column.tasks.order_by('-order').first()
            order = (max_order.order + 1) if max_order else 0
            
            PersonalTask.objects.create(
                board=board,
                column=column,
                title=title,
                description=description,
                priority=priority,
                deadline=deadline,
                date_start=date_start,
                date_end=date_end,
                notes=notes,
                is_recurring=is_recurring,
                recurring_type=recurring_type if is_recurring else None,
                order=order
            )
            messages.success(request, f'Task "{title}" created!')
        else:
            messages.error(request, 'Title and column are required.')
    
    return redirect('task_management:personal_board_detail', board_id=board_id)


@custom_login_required
def personal_task_toggle(request, task_id):
    """Toggle personal task completion"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    
    task.is_completed = not task.is_completed
    if task.is_completed:
        from django.utils import timezone
        task.completed_at = timezone.now().date()
    else:
        task.completed_at = None
    task.save()
    
    if request.headers.get('HX-Request') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'completed': task.is_completed})
    
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_delete(request, task_id):
    """Delete a personal task"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    board_id = task.board.id
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('task_management:personal_board_detail', board_id=board_id)


@require_POST
@custom_login_required
def personal_task_update_notes(request, task_id):
    """Update personal task notes"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    
    notes = request.POST.get('notes', '')
    task.notes = notes
    task.save()
    
    messages.success(request, 'Notes saved!')
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_edit(request, task_id):
    """Edit personal task details"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    
    if request.method == 'POST':
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.priority = request.POST.get('priority', task.priority)
        task.deadline = request.POST.get('deadline') or None
        task.date_start = request.POST.get('date_start') or None
        task.date_end = request.POST.get('date_end') or None
        task.notes = request.POST.get('notes', task.notes)
        task.save()
        
        # Check if AJAX request - return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Task updated!'})
        
        # Normal form submit
        messages.success(request, 'Task updated!')
        return redirect('task_management:personal_board_detail', board_id=task.board.id)
    
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@custom_login_required
def personal_task_checklist_add(request, task_id):
    """Add checklist item to personal task"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(PersonalTask, id=task_id, board__user=current_staff)
    
    if request.method == 'POST':
        text = request.POST.get('checklist_text')
        if text:
            max_order = task.checklist_items.order_by('-order').first()
            order = (max_order.order + 1) if max_order else 0
            
            item = PersonalTaskChecklistItem.objects.create(
                task=task,
                text=text,
                order=order
            )
            
            # Always return JSON for AJAX
            return JsonResponse({'success': True, 'id': item.id, 'text': text, 'is_completed': False})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@require_POST
@custom_login_required
def personal_task_checklist_toggle(request, item_id):
    """Toggle personal task checklist item"""
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
    """Delete checklist item"""
    item = get_object_or_404(PersonalTaskChecklistItem, id=item_id)
    task = item.task
    item.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Checklist item deleted.')
    return redirect('task_management:personal_board_detail', board_id=task.board.id)


@require_POST
@custom_login_required
def personal_task_update_position(request):
    """Update personal task position via drag-drop"""
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


# ========== TASK CHECKLIST & COMMENTS VIEWS ==========

@custom_login_required
def task_checklist_add(request, task_id):
    """Add a checklist item to a task"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'POST':
        text = request.POST.get('text')
        if text:
            max_order = task.checklist_items.order_by('-order').first()
            order = (max_order.order + 1) if max_order else 0
            
            TaskChecklistItem.objects.create(
                task=task,
                text=text,
                order=order
            )
            messages.success(request, 'Checklist item added.')
        else:
            messages.error(request, 'Text is required.')
    
    return redirect('task_management:task_detail', task_id=task_id)


@require_POST
@custom_login_required
def task_checklist_toggle(request, item_id):
    """Toggle checklist item completion"""
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
    """Delete a checklist item"""
    item = get_object_or_404(TaskChecklistItem, id=item_id)
    task_id = item.task.id
    item.delete()
    messages.success(request, 'Checklist item deleted.')
    return redirect('task_management:task_detail', task_id=task_id)


@custom_login_required
def task_comment_add(request, task_id):
    """Add a comment or note to a task"""
    current_staff = get_current_staff(request)
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        is_note = request.POST.get('is_note') == 'on'
        
        if content:
            TaskComment.objects.create(
                task=task,
                author=current_staff,
                content=content,
                is_note=is_note
            )
            if is_note:
                messages.success(request, 'Note added.')
            else:
                messages.success(request, 'Comment added.')
        else:
            messages.error(request, 'Content is required.')
    
    return redirect('task_management:task_detail', task_id=task_id)


@custom_login_required
def task_comment_delete(request, comment_id):
    """Delete a comment"""
    current_staff = get_current_staff(request)
    comment = get_object_or_404(TaskComment, id=comment_id)
    
    # Only author can delete their own comment
    if comment.author != current_staff and not request.session.get('is_owner'):
        messages.error(request, "You can only delete your own comments.")
        return redirect('task_management:task_detail', task_id=comment.task.id)
    
    task_id = comment.task.id
    comment.delete()
    messages.success(request, 'Comment deleted.')
    return redirect('task_management:task_detail', task_id=task_id)