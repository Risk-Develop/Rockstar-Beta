from django.urls import path
from . import views

urlpatterns = [


#dashboard_user_mgnt
    path('update-staff-role/', views.update_staff_role, name='update_staff_role'),
    path('dashboard/user/delete/<int:pk>/', views.user_delete_dash, name='user_delete_dash'),

    
    path('user_management/user/<int:pk>/', views.dashboard_user_detail, name='dashboard_user_detail'),

    path('dashboard/users/add/', views.dashboard_user_add, name='dashboard_user_add'),
    path('dashboard/users/edit/<int:pk>/', views.dashboard_user_edit, name='dashboard_user_edit'),







    path('', views.user_list, name='user_list'),
    path('ajax/user-list/', views.ajax_user_list, name='ajax_user_list'),
    path('add/', views.user_add, name='user_add'),
    path('edit/<int:pk>/', views.user_edit, name='user_edit'),
    path('delete/<int:pk>/', views.user_delete, name='user_delete'),
    path('get/<int:pk>/', views.user_edit, name='user_get'),
    path('user/<int:pk>/', views.user_detail, name='user_detail'),
    #path('roles/', views.user_role_list, name='user_role_list'),
    #path('assign-role/<int:user_id>/', views.assign_role, name='assign_role'),
    path('roles/', views.role_list, name='role_list'),
    path('roles/add/', views.role_add, name='role_add'),  # <-- this is needed
    path('roles/edit/<int:pk>/', views.role_edit, name='role_edit'),
    path('roles/delete/<int:pk>/', views.role_delete, name='role_delete'),
    path("assign-role/<int:staff_id>/", views.assign_role, name="assign_role"),

    #Department

    path('department/', views.department_list, name='department_list'),
    path('department/add/', views.department_add, name='department_add'),  # <-- this is needed
    path('department/edit/<int:pk>/', views.department_edit, name='department_edit'),
    path('department/delete/<int:pk>/', views.department_delete, name='department_delete'),
    path("department/assign-department/<int:staff_id>/", views.assign_department, name="assign_department"),
    
    

    #Positon

    path('position/', views.position_list, name='position_list'),
    path('position/add/', views.position_add, name='position_add'),
    path('position/edit/<int:pk>/', views.position_edit, name='position_edit'),
    path('position/delete/<int:pk>/', views.position_delete, name='position_delete'),
    path("position/assign-position/<int:staff_id>/", views.assign_position, name="assign_position"),

    # Staff History
    path('history/', views.staff_history_list, name='staff_history_list'),
    path('history/staff/<int:staff_id>/', views.staff_history_detail, name='staff_history_detail'),
]

