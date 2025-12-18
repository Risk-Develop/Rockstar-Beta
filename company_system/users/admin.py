from django.contrib import admin
from .models import Staff,Department,Position

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'middle_name', 'last_name', 'job_title', 'type', 'department', 'status')
    search_fields = ('first_name', 'last_name', 'job_title', 'department')
    list_filter = ('department', 'type', 'status', 'job_title')


    admin.site.register(Department)
    admin.site.register(Position)
