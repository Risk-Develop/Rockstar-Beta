from django.contrib import admin

from .models import EmployeeProfileSettings, EmployeeShiftRule


# admin.site.register(Shift)
admin.site.register(EmployeeProfileSettings)
admin.site.register(EmployeeShiftRule)