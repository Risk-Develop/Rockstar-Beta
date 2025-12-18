# human_resource/payroll_utils.py
from decimal import Decimal, ROUND_HALF_UP
import calendar
from datetime import date, timedelta, datetime, time

from .payroll_models import Benefit, EmployeeBenefit, Loan
from .models import Attendance, EmployeeShiftRule, LeaveRequest

ROUND = Decimal('0.01')

def month_end(year, month):
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)

def compute_hourly_rate(monthly_salary, expected_daily_hours=8, work_days_per_month=22):
    """
    Compute hourly rate from monthly salary.
    """
    daily_rate = (Decimal(monthly_salary) / Decimal(work_days_per_month)).quantize(ROUND)
    hourly = (daily_rate / Decimal(expected_daily_hours)).quantize(ROUND)
    return hourly

def compute_payroll_for_cutoff(employee, cutoff_start, cutoff_end, cutoff_no, shift_rule=None):
    """
    Compute payroll for a single employee per cutoff.
    Returns dict with gross, net, additions, deductions, details.
    """
    monthly_salary = Decimal(getattr(employee, 'monthly_salary', 0))
    salary_per_cutoff = (monthly_salary / Decimal(2)).quantize(ROUND)

    # 1️⃣ Determine shift_rule
    if not shift_rule:
        try:
            shift_rule = EmployeeShiftRule.objects.get(rank=employee.rank, shift=employee.shift)
        except EmployeeShiftRule.DoesNotExist:
            shift_rule = None

    expected_hours_per_day = Decimal(getattr(shift_rule, 'total_hours', 8)) if shift_rule else Decimal(8)
    work_days_per_cutoff = Decimal((cutoff_end - cutoff_start).days + 1)
    hourly_rate = compute_hourly_rate(monthly_salary, expected_daily_hours=expected_hours_per_day, work_days_per_month=Decimal(22))

    # 2️⃣ Attendance
    attendance_rows = Attendance.objects.filter(employee=employee, date__range=(cutoff_start, cutoff_end))
    hours_worked = Decimal('0.00')
    total_late_minutes = Decimal('0.00')
    total_ot_hours = Decimal('0.00')
    total_nsd_hours = Decimal('0.00')
    total_absent_days = Decimal('0.00')

    for att in attendance_rows:
        if att.clock_in and att.clock_out:
            delta = datetime.combine(date.min, att.clock_out) - datetime.combine(date.min, att.clock_in)
            hours_worked += Decimal(delta.total_seconds() / 3600)

            # Late calculation
            if shift_rule and att.clock_in > shift_rule.clock_in_end:
                grace = getattr(shift_rule, 'late_grace_period', 0)
                late_minutes = ((datetime.combine(date.min, att.clock_in) - datetime.combine(date.min, shift_rule.clock_in_end)).total_seconds() / 60) - grace
                total_late_minutes += Decimal(max(late_minutes, 0))

            # OT calculation
            if shift_rule and att.clock_out > shift_rule.clock_out:
                ot_hours = ((datetime.combine(date.min, att.clock_out) - datetime.combine(date.min, shift_rule.clock_out)).total_seconds() / 3600)
                total_ot_hours += Decimal(ot_hours)

            # NSD (assume 10PM-6AM)
            if shift_rule and getattr(shift_rule, 'nsd_applicable', False):
                nsd_start = datetime.combine(date.min, time(22, 0))
                nsd_end = datetime.combine(date.min + timedelta(days=1), time(6, 0))
                ci = datetime.combine(date.min, att.clock_in)
                co = datetime.combine(date.min, att.clock_out)
                overlap = max(min(co, nsd_end) - max(ci, nsd_start), timedelta(0))
                total_nsd_hours += Decimal(overlap.total_seconds() / 3600)
        else:
            total_absent_days += Decimal(1)

    # 3️⃣ Late deduction
    late_deduction = (total_late_minutes * (hourly_rate / Decimal(60))).quantize(ROUND)

    # 4️⃣ OT & NSD additions
    ot_amount = (total_ot_hours * hourly_rate * Decimal('1.25')).quantize(ROUND)
    nsd_amount = (total_nsd_hours * hourly_rate * Decimal('1.1')).quantize(ROUND)

    # 5️⃣ Leave handling (unpaid)
    unpaid_leaves = LeaveRequest.objects.filter(employee=employee, status='approved',
                                                start_date__lte=cutoff_end, end_date__gte=cutoff_start,
                                                leave_type__in=['unpaid'])
    unpaid_days = sum([(min(lr.end_date, cutoff_end) - max(lr.start_date, cutoff_start)).days + 1 for lr in unpaid_leaves])
    absent_amount = (unpaid_days * hourly_rate * expected_hours_per_day).quantize(ROUND)

    # 6️⃣ Loan deductions
    loans = Loan.objects.filter(employee=employee, status='approved')
    loan_deduction = sum([l.per_cutoff for l in loans], Decimal('0.00'))

    # 7️⃣ Benefits / statutory deductions
    statutory_deductions = Decimal('0.00')
    for eb in EmployeeBenefit.objects.filter(employee=employee):
        b = eb.benefit
        if b.use_percent:
            amt = (monthly_salary * (b.percent_value / Decimal(100))) / Decimal(2)  # per cutoff
        else:
            amt = b.amount
        statutory_deductions += amt

    # 8️⃣ Totals
    total_additions = ot_amount + nsd_amount
    total_deductions = absent_amount + late_deduction + loan_deduction + statutory_deductions
    gross = (salary_per_cutoff + total_additions).quantize(ROUND)
    net = (gross - total_deductions).quantize(ROUND)

    details = {
        'salary_per_cutoff': salary_per_cutoff,
        'hours_worked': hours_worked,
        'absent_days': total_absent_days + unpaid_days,
        'absent_amount': absent_amount,
        'late_deduction': late_deduction,
        'loan_deduction': loan_deduction,
        'statutory_deductions': statutory_deductions,
        'ot_hours': total_ot_hours,
        'ot_amount': ot_amount,
        'nsd_hours': total_nsd_hours,
        'nsd_amount': nsd_amount,
    }

    return {
        'gross': gross,
        'total_additions': total_additions,
        'total_deductions': total_deductions,
        'net': net,
        'details': details
    }
