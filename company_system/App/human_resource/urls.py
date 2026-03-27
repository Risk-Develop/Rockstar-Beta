from django.urls import path
from . import views_payroll
from . import views
from . import views_payroll_settings
from . import views_enps


app_name = "human_resource"  # Important for namespacing

urlpatterns = [
    # Main dashboard
    path("", views.human_resource_dashboard, name="hr_dashboard"),

    # Staff History
    path("dashboard/staff-history/", views.staff_history_hr_list, name="staff_history_hr_list"),

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

    # Role Management
    path("roles/", views.role_list, name="role_list"),
    path("roles/add/", views.role_add, name="role_add"),
    path("roles/edit/<int:pk>/", views.role_edit, name="role_edit"),
    path("roles/delete/<int:pk>/", views.role_delete, name="role_delete"),

    #check duplicates
    path("check-emp-number/", views.check_employee_number, name="check_emp_number"),

    #Employee Profile Setting
    path('employees/', views.employee_list, name='hr_employee_list'),
    path('employees/<int:employee_id>/', views.employee_profile, name='hr_employee_profile'),

    #Attendance
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/clock/', views.attendance_clock, name='attendance_clock'),
    path('attendance/clock/history/', views.attendance_history_ajax, name='attendance_history_ajax'),
    path('attendance/clock/absent-records/', views.get_absent_records_ajax, name='get_absent_records_ajax'),
    path('attendance/add/', views.attendance_add, name='attendance_add'),
    path('attendance/<int:pk>/edit/', views.attendance_edit, name='attendance_edit'),
    path('attendance/mark-absent/', views.hr_mark_absent, name='hr_mark_absent'),
    path('attendance/mark-absent/employees/', views.get_employees_without_attendance_htmx, name='get_employees_without_attendance_htmx'),
    path('attendance/<int:pk>/acknowledge/', views.acknowledge_attendance, name='acknowledge_attendance'),
    path('attendance/<int:pk>/appeal/', views.appeal_absent, name='appeal_absent'),
    #Attendance->Shift Rule
    path('shift-rules/', views.hr_shift_rules_list, name='hr_shift_rules_list'),
    path('shift-rules/add/', views.hr_shift_rule_add, name='hr_shift_rule_add'),
    path('shift-rules/<int:pk>/edit/', views.hr_shift_rule_edit, name='hr_shift_rule_edit'),
    path('shift-rules/<int:pk>/delete/', views.hr_shift_rule_delete, name='hr_shift_rule_delete'),

  #Leave Credit
    path("leave-credits/", views.leave_credit_list, name="leave_credit_list"),
    path("leave-credits/add/", views.leave_credit_add, name="leave_credit_add"),
    path("leave-credits/<int:pk>/edit/", views.leave_credit_edit, name="leave_credit_edit"),
    path('leave-credits/get-rank/', views.get_employee_rank, name='get_employee_rank'),
    # Leave Requests
    path('leave-requests/', views.leave_request_list, name='leave_request_list'),
    path('leave-requests/ajax/', views.leave_request_list_ajax, name='leave_request_list_ajax'),
    path('leave-request/add/', views.leave_request_add, name='leave_request_add'),
    path('leave-request/edit/<int:pk>/', views.leave_request_edit, name='leave_request_edit'),
    path('leave-requests/<int:pk>/quick-status/', views.leave_request_quick_status, name='leave_request_quick_status'),
    path('leave-requests/get-employee-info/', views.get_employee_info, name='get_employee_info'),

    # ==============================
    # Payroll
    # ==============================
    path('payroll/preview/', views_payroll.payroll_preview, name='payroll_preview'),
    path('payroll/finalize/', views_payroll.payroll_finalize, name='payroll_finalize'),
    path('payroll/record/<int:pk>/', views_payroll.payroll_record_detail, name='payroll_record_detail'),
    
    # Enhanced Batch Payroll
    path('payroll/batch-preview/', views_payroll.batch_payroll_preview, name='batch_payroll_preview'),
    path('payroll/batch-finalize/', views_payroll.batch_payroll_finalize, name='batch_payroll_finalize'),

    # Individual Payroll Processing
    path('payroll/individual/', views_payroll.individual_payroll, name='individual_payroll'),
    
    path('payroll/individual/preview/', views_payroll.individual_payroll_preview, name='individual_payroll_preview'),
    
    path('payroll/individual/finalize/', views_payroll.individual_payroll_finalize, name='individual_payroll_finalize'),
    
    # API Endpoints
    path('api/employee/<int:employee_id>/', views_payroll.api_employee_info, name='api_employee_info'),
    path('api/attendance/', views_payroll.api_attendance_data, name='api_attendance_data'),
    
    # Self-Service
    path('self-service/', views_payroll.hr_self_service, name='hr_self_service'),

    # Payouts
    path('payout/', views_payroll.payout_list, name='payout_list'),
    path('payout/<int:pk>/', views_payroll.payout_detail, name='payout_detail'),
    path('payout/<int:payout_id>/pdf/', views_payroll.payout_pdf, name='payout_pdf'),
    path('payout/<int:pk>/edit/', views_payroll.payout_edit, name='payout_edit'),
    path('payout/<int:pk>/delete/', views_payroll.payout_delete, name='payout_delete'),
    path('payout/<int:pk>/unfinalize/', views_payroll.payout_unfinalize, name='payout_unfinalize'),
    path('payout/<int:payout_id>/finalize/', views_payroll.payout_finalize, name='payout_finalize'),
    path('payout/<int:payout_id>/release/', views_payroll.payout_release, name='payout_release'),
    path('payout/batch-release/', views_payroll.payout_batch_release, name='payout_batch_release'),
    path('payout/export/csv/', views_payroll.payout_export_csv, name='payout_export_csv'),

    # Bank Accounts
    path('bank-accounts/', views_payroll.bankaccount_list, name='bankaccount_list'),
    path('bank-accounts/add/', views_payroll.bankaccount_form, name='bankaccount_add'),
    path('bank-accounts/<int:pk>/edit/', views_payroll.bankaccount_form, name='bankaccount_edit'),

    # Loans
    path('loans/', views_payroll.loan_list, name='loan_list'),
    path('loans/add/', views_payroll.loan_form, name='loan_add'),
    path('loans/<int:pk>/', views_payroll.loan_detail, name='loan_detail'),
    path('loans/<int:pk>/edit/', views_payroll.loan_form, name='loan_edit'),
    path('loans/<int:pk>/update-status/', views_payroll.loan_update_status, name='loan_update_status'),

    # Bank Types
    path('bank-types/', views_payroll.banktype_list, name='banktype_list'),
    path('bank-types/add/', views_payroll.banktype_form, name='banktype_add'),
    path('bank-types/<int:pk>/edit/', views_payroll.banktype_form, name='banktype_edit'),
    path('bank-types/<int:pk>/delete/', views_payroll.banktype_delete, name='banktype_delete'),

    # ==============================
    # Payroll Settings
    # ==============================
    # Tier Threshold Settings
    path('payroll-settings/tiers/', views_payroll_settings.tier_list, name='tier_list'),
    path('payroll-settings/tiers/add/', views_payroll_settings.tier_add, name='tier_add'),
    path('payroll-settings/tiers/<int:pk>/edit/', views_payroll_settings.tier_edit, name='tier_edit'),
    
    # Employee Salary Settings
    path('payroll-settings/salaries/', views_payroll_settings.salary_setting_list, name='salary_setting_list'),
    path('payroll-settings/salaries/add/', views_payroll_settings.salary_setting_add, name='salary_setting_add'),
    path('payroll-settings/salaries/<int:pk>/edit/', views_payroll_settings.salary_setting_edit, name='salary_setting_edit'),
    
    # De Minimis Types
    path('payroll-settings/deminimis/', views_payroll_settings.deminimis_list, name='demiminimis_list'),
    path('payroll-settings/deminimis/add/', views_payroll_settings.deminimis_form, name='demiminimis_type_add'),
    path('payroll-settings/deminimis/<int:pk>/edit/', views_payroll_settings.deminimis_form, name='demiminimis_type_edit'),
    path('payroll-settings/deminimis/<int:pk>/delete/', views_payroll_settings.deminimis_delete, name='demiminimis_type_delete'),
    
    # Deduction Types
    path('payroll-settings/deductions/', views_payroll_settings.deduction_type_list, name='deduction_type_list'),
    path('payroll-settings/deductions/add/', views_payroll_settings.deduction_type_form, name='deduction_type_add'),
    path('payroll-settings/deductions/<int:pk>/edit/', views_payroll_settings.deduction_type_form, name='deduction_type_edit'),
    path('payroll-settings/deductions/<int:pk>/delete/', views_payroll_settings.deduction_type_delete, name='deduction_type_delete'),
    
    # Employee Deduction Accounts
    path('payroll-settings/deduction-accounts/', views_payroll_settings.employee_deduction_account_list, name='employee_deduction_account_list'),
    path('payroll-settings/deduction-accounts/add/', views_payroll_settings.employee_deduction_account_form, name='employee_deduction_account_add'),
    path('payroll-settings/deduction-accounts/<int:pk>/edit/', views_payroll_settings.employee_deduction_account_form, name='employee_deduction_account_edit'),
    path('payroll-settings/deduction-accounts/<int:pk>/delete/', views_payroll_settings.employee_deduction_account_delete, name='employee_deduction_account_delete'),
    path('payroll-settings/deduction-accounts/employee/<int:employee_id>/', views_payroll_settings.employee_deduction_accounts_by_employee, name='employee_deduction_accounts_by_employee'),
    
    # Payroll History
    path('payroll-settings/history/', views_payroll.payroll_history_list, name='payroll_history_list'),
    path('payroll-settings/history/<int:pk>/', views_payroll.payroll_history_detail, name='payroll_history_detail'),

    # Positions
    path('positions/', views.position_list, name='position_list'),
    path('positions/add/', views.position_add, name='position_add'),
    path('positions/edit/<int:pk>/', views.position_edit, name='position_edit'),
    path('positions/delete/<int:pk>/', views.position_delete, name='position_delete'),

    # Department
    path('department/', views.department_list, name='department_list'),
    path('departments/add/', views.department_add, name='department_add'),
    path('departments/edit/<int:pk>/', views.department_edit, name='department_edit'),
    path('departments/delete/<int:pk>/', views.department_delete, name='department_delete'),

    # ==============================
    # ENPS Survey
    # ==============================
    # Survey Management
    path('enps/', views_enps.enps_survey_list, name='enps_survey_list'),
    path('enps/create/', views_enps.enps_survey_create, name='enps_survey_create'),
    path('enps/<int:survey_id>/', views_enps.enps_survey_detail, name='enps_survey_detail'),
    path('enps/<int:survey_id>/edit/', views_enps.enps_survey_edit, name='enps_survey_edit'),
    path('enps/<int:survey_id>/delete/', views_enps.enps_survey_delete, name='enps_survey_delete'),
    path('enps/<int:survey_id>/analytics/', views_enps.enps_analytics, name='enps_analytics'),
    path('enps/<int:survey_id>/refresh-analytics/', views_enps.refresh_all_department_analytics, name='enps_refresh_analytics'),
    
    # Employee-facing survey form
    path('enps/take/<int:survey_id>/', views_enps.enps_take_survey, name='enps_take_survey'),
    path('enps/take/<int:survey_id>/submit/', views_enps.enps_submit_response, name='enps_submit'),
    
    # HTMX endpoints
    path('enps/<int:survey_id>/responses/', views_enps.enps_responses_ajax, name='enps_responses_ajax'),
    path('enps/<int:survey_id>/department-data/', views_enps.enps_department_data_ajax, name='enps_department_data_ajax'),
    path('enps/<int:survey_id>/trend-data/', views_enps.enps_trend_data_ajax, name='enps_trend_data_ajax'),
    path('enps/<int:survey_id>/heatmap-data/', views_enps.enps_heatmap_data_ajax, name='enps_heatmap_data_ajax'),
    path('enps/<int:survey_id>/analytics-data/', views_enps.enps_analytics_data_ajax, name='enps_analytics_data_ajax'),
    path('enps/<int:survey_id>/question-analytics/', views_enps.enps_question_analytics_ajax, name='enps_question_analytics_ajax'),
    
    # Employee lookup API
    path('enps/lookup-employee/', views_enps.lookup_employee, name='lookup_employee'),


]

