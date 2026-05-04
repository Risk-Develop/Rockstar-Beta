from django.contrib import admin
from .models import KanbanBoard, KanbanColumn, Task, Roadmap, AuditLog


@admin.register(KanbanBoard)
class KanbanBoardAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']


@admin.register(KanbanColumn)
class KanbanColumnAdmin(admin.ModelAdmin):
    list_display = ['name', 'board', 'order', 'color', 'is_active']
    list_filter = ['board', 'is_active']
    search_fields = ['name']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'column', 'assigned_to', 'priority', 'deadline', 'created_at']
    list_filter = ['priority', 'column__board', 'is_completed']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ['name', 'board', 'start_date', 'end_date', 'created_by']
    list_filter = ['board', 'start_date']
    search_fields = ['name', 'description']
    date_hierarchy = 'start_date'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'action', 'performed_by', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['task__title', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['task', 'action', 'performed_by', 'from_column', 'to_column', 'description', 'created_at', 'ip_address']