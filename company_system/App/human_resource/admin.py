from django.contrib import admin

from .models import EmployeeProfileSettings, EmployeeShiftRule
from .payroll_models import (
    PayrollRecord, Payout, PayoutDetail, Loan, Benefit, EmployeeBenefit,
    BankType, BankAccount, BankAllocation, PayrollOverride, PayrollAuditLog,
    GovernmentContributionRate
)
from .payroll_settings_models import (
    TierThresholdSetting,
    EmployeeSalarySetting,
    DeMinimisType,
    DeductionType,
    EmployeeDeductionAccount,
    PayrollPreview,
    PayrollHistory,
    DeMinimisEntry,
    DeductionEntry,
    PayrollAdjustment,
)
from .handbook_models import (
    OffenseGroup,
    OffenseSection,
    OffenseClassification,
    RemedialAction,
    ViolationCategory,
    ViolationType,
    EmployeeViolation,
)


# =============================================================================
# Existing registrations
# =============================================================================
# admin.site.register(Shift)
admin.site.register(EmployeeProfileSettings)
admin.site.register(EmployeeShiftRule)


# =============================================================================
# Payroll Settings Models
# =============================================================================

@admin.register(TierThresholdSetting)
class TierThresholdSettingAdmin(admin.ModelAdmin):
    list_display = ['tier_name', 'tier_label', 'threshold_percentage', 
                    'multiplier', 'effective_start_date', 'effective_end_date', 'is_active']
    list_filter = ['is_active', 'tier_name']
    search_fields = ['tier_name', 'tier_label']
    ordering = ['threshold_percentage']


@admin.register(EmployeeSalarySetting)
class EmployeeSalarySettingAdmin(admin.ModelAdmin):
    list_display = ['employee', 'base_salary_monthly', 'salary_per_cutoff', 
                    'tier', 'effective_start_date', 'effective_end_date', 'is_active']
    list_filter = ['is_active', 'tier']
    search_fields = ['employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee', 'tier']
    readonly_fields = ['salary_per_cutoff', 'created_at', 'updated_at']
    ordering = ['-effective_start_date']


@admin.register(DeMinimisType)
class DeMinimisTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_taxable', 'is_active', 
                    'display_order', 'effective_start_date', 'effective_end_date']
    list_filter = ['is_active', 'is_taxable']
    search_fields = ['name', 'code']
    ordering = ['display_order', 'name']


@admin.register(DeductionType)
class DeductionTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'is_government', 
                    'is_tax_applicable', 'is_active', 'display_order']
    list_filter = ['is_active', 'category', 'is_government']
    search_fields = ['name', 'code']
    ordering = ['category', 'display_order']


@admin.register(EmployeeDeductionAccount)
class EmployeeDeductionAccountAdmin(admin.ModelAdmin):
    list_display = ['employee', 'deduction_type', 'account_number', 'has_insurance', 
                    'is_active', 'effective_start_date', 'effective_end_date']
    list_filter = ['is_active', 'has_insurance', 'deduction_type__category', 'deduction_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_number', 
                    'account_number', 'insurance_policy_number']
    raw_id_fields = ['employee', 'deduction_type']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['employee__last_name', 'employee__first_name', 'deduction_type__category']


# =============================================================================
# Payroll Preview and History
# =============================================================================

@admin.register(PayrollPreview)
class PayrollPreviewAdmin(admin.ModelAdmin):
    list_display = ['employee', 'cutoff', 'cutoff_start_date', 'cutoff_end_date',
                    'salary_per_cutoff', 'gross_earnings', 'total_deductions', 
                    'net_pay', 'status']
    list_filter = ['status', 'cutoff', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee', 'payroll_record', 'employee_salary_setting', 'tier']
    readonly_fields = ['gross_earnings', 'total_additions', 'total_de_minimis',
                      'taxable_earnings', 'total_deductions', 'net_pay',
                      'overtime_amount', 'nsd_amount', 'holiday_amount','regular_holiday_amount', 
                      'leave_deduction', 'created_at', 'updated_at']
    ordering = ['-cutoff_start_date', 'employee']


@admin.register(PayrollHistory)
class PayrollHistoryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'cutoff', 'cutoff_start_date', 'cutoff_end_date',
                    'salary_per_cutoff', 'gross_earnings', 'total_deductions', 
                    'net_pay', 'posted_at', 'posted_by']
    list_filter = ['cutoff', 'posted_at']
    search_fields = ['employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee', 'payroll_record']
    readonly_fields = ['employee', 'payroll_record', 'cutoff', 'cutoff_start_date',
                       'cutoff_end_date', 'employee_salary_setting_id', 'base_salary_monthly',
                       'salary_per_cutoff', 'tier_id', 'tier_name', 'tier_threshold_percentage',
                       'gross_earnings', 'overtime_hours', 'overtime_amount', 'nsd_hours',
                       'nsd_amount', 'holiday_hours', 'holiday_amount', 'regular_holiday_amount', 'incentives',
                       'leave_days', 'leave_deduction', 'total_additions', 
                       'total_de_minimis', 'taxable_earnings', 'tax_amount',
                       'other_deductions', 'total_deductions', 'net_pay',
                       'posted_at', 'posted_by', 'original_preview_id', 'complete_snapshot']
    ordering = ['-cutoff_start_date', 'employee']


@admin.register(PayrollAdjustment)
class PayrollAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_history', 'adjustment_type', 
                    'amount', 'description', 'is_taxable', 'created_by', 'created_at']
    list_filter = ['adjustment_type', 'is_taxable', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'description']
    raw_id_fields = ['employee', 'payroll_history', 'created_by']
    ordering = ['-created_at']


# =============================================================================
# Entry models (read-only in admin)
# =============================================================================

@admin.register(DeMinimisEntry)
class DeMinimisEntryAdmin(admin.ModelAdmin):
    list_display = ['payroll_preview', 'de_minimis_type', 'amount']
    list_filter = ['de_minimis_type']
    raw_id_fields = ['payroll_preview', 'payroll_history', 'de_minimis_type']


@admin.register(DeductionEntry)
class DeductionEntryAdmin(admin.ModelAdmin):
    list_display = ['payroll_preview', 'deduction_type', 'amount', 'notes']
    list_filter = ['deduction_type', 'deduction_type__category']
    raw_id_fields = ['payroll_preview', 'payroll_history', 'deduction_type']


# =============================================================================
# Existing payroll models (kept for reference)
# =============================================================================

@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ['cutoff', 'month', 'year', 'created_by', 'created_at', 'finalized']
    list_filter = ['finalized', 'cutoff', 'year', 'month']
    ordering = ['-year', '-month', '-created_at']


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ['employee', 'cutoff', 'month', 'year', 'gross', 
                   'total_deductions', 'net', 'created_at']
    list_filter = ['cutoff', 'month', 'year']
    search_fields = ['employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee', 'bank_account', 'payroll_record']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['employee', 'principal', 'balance', 'status', 
                   'monthly_deduction', 'per_cutoff', 'start_date']
    list_filter = ['status', 'start_date']
    search_fields = ['employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee']


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'amount', 'use_percent', 'percent_value']
    search_fields = ['name', 'code']


@admin.register(EmployeeBenefit)
class EmployeeBenefitAdmin(admin.ModelAdmin):
    list_display = ['employee', 'benefit', 'apply_per_cutoff', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name']
    raw_id_fields = ['employee', 'benefit']


@admin.register(BankType)
class BankTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['employee', 'account_number', 'bank', 'is_primary']
    search_fields = ['employee__first_name', 'employee__last_name', 'account_number']
    raw_id_fields = ['employee', 'bank']


@admin.register(PayrollOverride)
class PayrollOverrideAdmin(admin.ModelAdmin):
    list_display = ['payout', 'field_name', 'original_value', 
                   'override_value', 'overridden_by', 'overridden_at']
    list_filter = ['overridden_at']
    raw_id_fields = ['payout', 'overridden_by']


@admin.register(PayrollAuditLog)
class PayrollAuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'timestamp', 'employee', 'action', 'payout']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'employee__first_name', 'employee__last_name']
    readonly_fields = ['user', 'timestamp', 'employee', 'action', 'payout',
                      'before_values', 'after_values', 'ip_address', 'user_agent']


@admin.register(GovernmentContributionRate)
class GovernmentContributionRateAdmin(admin.ModelAdmin):
    list_display = ['contribution_type', 'salary_bracket_min', 'salary_bracket_max',
                   'employee_share', 'employer_share', 'effective_date', 'is_active']
    list_filter = ['contribution_type', 'is_active']
    ordering = ['contribution_type', 'salary_bracket_min']


# =============================================================================
# Handbook Offense Classification & Compliance Models
# =============================================================================

@admin.register(OffenseGroup)
class OffenseGroupAdmin(admin.ModelAdmin):
    list_display = ['group_number', 'group_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['group_number', 'group_name']
    ordering = ['group_number']


@admin.register(OffenseSection)
class OffenseSectionAdmin(admin.ModelAdmin):
    list_display = ['section_number', 'section_title', 'offense_group', 'is_active']
    list_filter = ['is_active', 'offense_group']
    search_fields = ['section_number', 'section_title']
    ordering = ['offense_group', 'section_number']
    raw_id_fields = ['offense_group']


@admin.register(OffenseClassification)
class OffenseClassificationAdmin(admin.ModelAdmin):
    list_display = ['offense_section', 'offense_description', 'default_range', 'is_active']
    list_filter = ['is_active', 'default_range', 'offense_section__offense_group']
    search_fields = ['offense_description']
    ordering = ['offense_section', 'id']
    raw_id_fields = ['offense_section']


@admin.register(RemedialAction)
class RemedialActionAdmin(admin.ModelAdmin):
    list_display = ['range_code', 'offense_count', 'action', 'is_active']
    list_filter = ['is_active', 'range_code']
    ordering = ['range_code', 'offense_count']


@admin.register(ViolationCategory)
class ViolationCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'display_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


@admin.register(ViolationType)
class ViolationTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'display_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


@admin.register(EmployeeViolation)
class EmployeeViolationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'incident_number', 'category', 'violation_type', 
                   'status', 'remedial_action_range', 'da_status', 'date_submitted']
    list_filter = ['status', 'da_status', 'remedial_action_range', 'category', 'violation_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'type_of_incident']
    ordering = ['-created_at']
    raw_id_fields = ['employee', 'submitted_by', 'offense_classification']
    readonly_fields = ['incident_number', 'offense_count', 'remedial_action_range', 
                       'created_at', 'updated_at', 'last_updated']

