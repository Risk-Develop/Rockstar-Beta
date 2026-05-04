from django.db import models
from django.conf import settings
from django.urls import reverse
from App.users.models import Staff


class KanbanBoard(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE,
        related_name='created_boards',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('task_management:board_detail', kwargs={'board_id': self.id})

    class Meta:
        ordering = ['-created_at']


class KanbanColumn(models.Model):
    DEFAULT_COLUMNS = [
        {'name': 'Backlog', 'order': 0, 'color': '#6b7280'},
        {'name': 'To Do', 'order': 1, 'color': '#3b82f6'},
        {'name': 'In Progress', 'order': 2, 'color': '#f59e0b'},
        {'name': 'Review', 'order': 3, 'color': '#8b5cf6'},
        {'name': 'Done', 'order': 4, 'color': '#10b981'},
    ]

    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=20, default='#6b7280')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        unique_together = ['board', 'name']

    def __str__(self):
        return f"{self.board.name} - {self.name}"


class Roadmap(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name='roadmaps')
    created_by = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='created_roadmaps',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['start_date']


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    column = models.ForeignKey(KanbanColumn, on_delete=models.CASCADE, related_name='tasks')
    order = models.PositiveIntegerField(default=0)

    assigned_to = models.ForeignKey(
        'users.Staff', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE,
        related_name='created_tasks',
        null=True,
        blank=True
    )

    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    deadline = models.DateField(null=True, blank=True)
    roadmap = models.ForeignKey(
        Roadmap, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tasks'
    )

    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['column__order', 'order']
        unique_together = ['column', 'title']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('task_management:task_detail', kwargs={'task_id': self.id})


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('moved', 'Moved'),
        ('edited', 'Edited'),
        ('deleted', 'Deleted'),
        ('assigned', 'Assigned'),
        ('completed', 'Completed'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        related_name='task_audit_logs'
    )
    
    # Track changes
    from_column = models.ForeignKey(
        KanbanColumn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_from'
    )
    to_column = models.ForeignKey(
        KanbanColumn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_to'
    )
    
    # Details about the change
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.task.title} - {self.action} by {self.performed_by}"


# ========== PERSONAL PRODUCTIVITY SYSTEM ==========
class PersonalBoard(models.Model):
    """Private board for personal tasks - separate from company Kanban"""
    user = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='personal_boards'
    )
    name = models.CharField(max_length=100, default="My Tasks")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name}'s Personal Board"

    class Meta:
        ordering = ['-updated_at']
        unique_together = ['user', 'name']


class PersonalColumn(models.Model):
    """Columns for personal board - same as company kanban"""
    DEFAULT_COLUMNS = [
        {'name': 'Backlog', 'order': 0, 'color': '#6b7280'},
        {'name': 'To Do', 'order': 1, 'color': '#3b82f6'},
        {'name': 'In Progress', 'order': 2, 'color': '#f59e0b'},
        {'name': 'Review', 'order': 3, 'color': '#8b5cf6'},
        {'name': 'Done', 'order': 4, 'color': '#10b981'},
    ]

    board = models.ForeignKey(PersonalBoard, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=20, default='#6b7280')

    class Meta:
        ordering = ['order']
        unique_together = ['board', 'name']

    def __str__(self):
        return f"{self.board.name} - {self.name}"


class PersonalTask(models.Model):
    """Private personal tasks - not company related"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    RECURRING_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    board = models.ForeignKey(PersonalBoard, on_delete=models.CASCADE, related_name='tasks')
    column = models.ForeignKey(PersonalColumn, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    deadline = models.DateField(null=True, blank=True)
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    
    # For habits/daily goals
    is_recurring = models.BooleanField(default=False)
    recurring_type = models.CharField(max_length=20, choices=RECURRING_CHOICES, blank=True, null=True)
    recurring_days = models.CharField(max_length=20, blank=True, null=True)  # Mon,Tue,Wed etc
    
    # Notes for personal tasks
    notes = models.TextField(blank=True)
    
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['column__order', 'order']

    def __str__(self):
        return self.title


class PersonalTaskChecklistItem(models.Model):
    """Checklist items for personal tasks"""
    task = models.ForeignKey(PersonalTask, on_delete=models.CASCADE, related_name='checklist_items')
    text = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"[{'x' if self.is_completed else ' '}] {self.text}"


# ========== ENHANCE COMPANY TASKS ==========
class TaskChecklistItem(models.Model):
    """Checklist items within a company task - like sub-tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='checklist_items')
    text = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"[{'x' if self.is_completed else ' '}] {self.text}"


class TaskComment(models.Model):
    """Comments/notes on company tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='task_comments'
    )
    content = models.TextField()
    is_note = models.BooleanField(default=False, help_text="If True, this is a note instead of a comment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.task.title}"