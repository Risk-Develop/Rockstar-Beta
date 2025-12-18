from django.urls import path
from . import views_payroll
#from .views_payroll import payroll_preview
from . import views


app_name = "human_resource"  # Important for namespacing

urlpatterns = [
    # Main dashboard
    path("", views.human_resource_dashboard, name="hr_dashboard"),

    # User Management
    path("user-management/", views.hr_user_mgnt, name="hr_user_mgnt"),

    # AJAX user list for search/pagination
    path("ajax_user_list/", views.ajax_user_list, name="ajax_user_list"),

    # Add / Edit / Details / Delete
    path("user/add/", views.dashboard_user_add, name="dashboard_user_add"),
    path("user/edit/<int:pk>/", views.dashboard_user_edit, name="dashboard_user_edit"),
    path("user/details/<int:pk>/", views.dashboard_user_detail, name="dashboard_user_detail"),

    path("user/delete/<int:pk>/", views.hr_user_delete, name="user_delete_dash"),
    # Update staff role inline
    path("user/update-role/", views.update_staff_role, name="update_staff_role"),

    #check duplicates
    path("check-emp-number/", views.check_employee_number, name="check_emp_number"),

    #Employee Profile Setting
    path('employees/', views.employee_list, name='hr_employee_list'),
    path('employees/<int:employee_id>/', views.employee_profile, name='hr_employee_profile'),

    #Attendance
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/clock/', views.attendance_clock, name='attendance_clock'),
    #Attendance->Shift Rule
    path('shift-rules/', views.hr_shift_rules_list, name='hr_shift_rules_list'),
  
  #Leave Credit
    path("leave-credits/", views.leave_credit_list, name="leave_credit_list"),
    path("leave-credits/add/", views.leave_credit_add, name="leave_credit_add"),
    path("leave-credits/<int:pk>/edit/", views.leave_credit_edit, name="leave_credit_edit"),
    #path("leave-credits/get-rank/", views.ajax_get_employee_rank, name="get_employee_rank"),
    path('leave-credits/get-rank/', views.get_employee_rank, name='get_employee_rank'),
    # Leave Requests
    path('leave-requests/', views.leave_request_list, name='leave_request_list'),
    path('leave-request/add/', views.leave_request_add, name='leave_request_add'),
    path('leave-request/edit/<int:pk>/', views.leave_request_edit, name='leave_request_edit'),
    path('leave-requests/get-employee-info/', views.get_employee_info, name='get_employee_info'),
# hr/urls.py
 
# ==============================
    # Payroll
    # ==============================
    path('payroll/preview/', views_payroll.payroll_preview, name='payroll_preview'),
    path('payroll/finalize/', views_payroll.payroll_finalize, name='payroll_finalize'),
    path('payroll/record/<int:pk>/', views_payroll.payroll_record_detail, name='payroll_record_detail'),

    # ==============================
    # Optional: Bank Accounts
    # ==============================
    # path('payroll/bankaccounts/', views_payroll.bank_account_list, name='bank_account_list'),
    # path('payroll/bankaccounts/add/', views_payroll.bank_account_add, name='bank_account_add'),

    # ==============================
    # Optional: Loans
    # ==============================
    # path('payroll/loans/', views_payroll.loan_list, name='loan_list'),
    # path('payroll/loans/add/', views_payroll.loan_add, name='loan_add'),
    # path('payroll/loans/<int:pk>/', views_payroll.loan_detail, name='loan_detail'),

    #path('payroll/generate/', payroll_generate, name='payroll_generate'),
    path('payout/<int:payout_id>/pdf/', views_payroll.payout_pdf, name='payout_pdf')

]
