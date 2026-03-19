from django.contrib import admin
from .models import Staff, Department, Position, StaffHistory


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'middle_name', 'last_name', 'job_title', 'type', 'department', 'status')
    search_fields = ('first_name', 'last_name', 'job_title', 'department')
    list_filter = ('department', 'type', 'status', 'job_title')


@admin.register(StaffHistory)
class StaffHistoryAdmin(admin.ModelAdmin):
    list_display = ('staff', 'field_name', 'old_value', 'new_value', 'changed_at', 'changed_by')
    search_fields = ('staff__first_name', 'staff__last_name', 'field_name', 'changed_by__username')
    list_filter = ('field_name', 'changed_at', 'changed_by')
    readonly_fields = ('staff', 'field_name', 'old_value', 'new_value', 'changed_at', 'changed_by', 'change_reason')
    ordering = ('-changed_at',)
    
    def has_add_permission(self, request):
        # Prevent manual creation from admin
        return False
    
    def has_change_permission(self, request, obj=None):
        # Make it read-only
        return False


admin.site.register(Department)
admin.site.register(Position)

