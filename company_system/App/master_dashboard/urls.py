# master_dashboard/urls.py
from django.urls import path, include
from . import views

app_name = 'master_dashboard'

urlpatterns = [
    path('sales/', include('App.sales.urls')),
    path('human_resource/', include('App.human_resource.urls')),
    path("login-history/", views.login_history, name="login_history"),
    path("staff-history/", views.staff_history_master_list, name="staff_history_master_list"),
    
    # User Management URLs
    path("usermgnt/", views.master_user_list, name="master_user_list"),
    path("usermgnt/add/", views.master_user_add, name="master_user_add"),
    path("usermgnt/edit/<int:pk>/", views.master_user_edit, name="master_user_edit"),
    path("usermgnt/detail/<int:pk>/", views.master_user_detail, name="master_user_detail"),
    path("usermgnt/delete/<int:pk>/", views.master_user_delete, name="master_user_delete"),
    path("usermgnt/update-role/", views.master_update_staff_role, name="master_update_staff_role"),
    
    # Password Reset URLs
    path("password-reset/", views.password_reset_list, name="password_reset_list"),
    path("password-reset/ajax/", views.password_reset_list_ajax, name="password_reset_list_ajax"),
    path("password-reset/confirm/<int:staff_id>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("password-reset/custom/<int:staff_id>/", views.password_reset_custom, name="password_reset_custom"),
    
    # Role Management URLs (using human_resource views)
    path("roles/", views.role_list_master, name="role_list"),
    path("roles/add/", views.role_add_master, name="role_add"),
    path("roles/edit/<int:pk>/", views.role_edit_master, name="role_edit"),
    path("roles/delete/<int:pk>/", views.role_delete_master, name="role_delete"),
    
    # Position Management URLs (using human_resource views)
    path("positions/", views.position_list_master, name="position_list"),
    path("positions/add/", views.position_add_master, name="position_add"),
    path("positions/edit/<int:pk>/", views.position_edit_master, name="position_edit"),
    path("positions/delete/<int:pk>/", views.position_delete_master, name="position_delete"),
    
    # Department Management URLs (using human_resource views)
    path("departments/", views.department_list_master, name="department_list"),
    path("departments/add/", views.department_add_master, name="department_add"),
    path("departments/edit/<int:pk>/", views.department_edit_master, name="department_edit"),
    path("departments/delete/<int:pk>/", views.department_delete_master, name="department_delete"),
    
    # Rank Management URLs (using human_resource views)
    path("ranks/", views.rank_list_master, name="rank_list"),
    path("ranks/add/", views.rank_add_master, name="rank_add"),
    path("ranks/edit/<int:pk>/", views.rank_edit_master, name="rank_edit"),
    path("ranks/delete/<int:pk>/", views.rank_delete_master, name="rank_delete"),
    
    path("", views.master_dashboard, name="master_dashboard"),
    path("attendance/clock/", views.attendance_clock_master, name="attendance_clock_master"),
    path("attendance/clock/absent-records/", views.get_absent_records_ajax_master, name="get_absent_records_ajax_master"),
    path("attendance/<int:pk>/appeal/", views.appeal_absent_master, name="appeal_absent_master"),
]

