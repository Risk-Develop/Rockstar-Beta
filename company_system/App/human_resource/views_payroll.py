# human_resource/views_payroll.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta, datetime
import calendar
from decimal import Decimal

from App.authentication.decorators import login_required
from App.authentication.views import get_current_user

ROUND = Decimal('0.01')


def safe_decimal(value, default='0'):
    """Safely convert a value to Decimal, returning default on failure."""
    try:
        if value is None or value == '':
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


from django.http import HttpResponse
from weasyprint import HTML

from .payroll_models import PayrollRecord, Payout, BankAccount, BankType, Loan
from .payroll_utils import compute_payroll_for_cutoff
from App.users.models import Staff, Department
from .models import EmployeeShiftRule


# ════════════════════════════════════════════════════════════
# Payroll Preview (before finalizing)
# ════════════════════════════════════════════════════════════
@login_required
def payroll_preview(request):
    from .payroll_settings_models import EmployeeSalarySetting, DeMinimisType, DeductionType
    from .models import Attendance
    
    month  = int(request.GET.get('month',  date.today().month))
    year   = int(request.GET.get('year',   date.today().year))
    cutoff = request.GET.get('cutoff', '1')
    
    # Filter parameters
    department_id = request.GET.get('department')
    status_filter = request.GET.get('status', 'active')

    if cutoff == '1':
        start = date(year, month, 1)
        end   = date(year, month, 15)
    else:
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 16)
        end   = date(year, month, last_day)

    # Base queryset - filter by status
    if status_filter == 'active':
        employees = Staff.objects.filter(status='active')
    elif status_filter == 'inactive':
        employees = Staff.objects.filter(status='inactive')
    else:
        employees = Staff.objects.all()
    
    # Filter by department if provided
    if department_id:
        employees = employees.filter(departmentlink_id=department_id)
    
    preview_list = []
    
    total_net = Decimal('0.00')
    total_deductions = Decimal('0.00')
    total_gross = Decimal('0.00')
    total_absent = Decimal('0.00')
    total_late = Decimal('0.00')
    total_loans = Decimal('0.00')
    total_basic = Decimal('0.00')

    for emp in employees:
        # Get salary from EmployeeSalarySetting
        salary_per_cutoff = Decimal('0.00')
        try:
            salary_setting = EmployeeSalarySetting.objects.get(employee=emp, is_active=True, effective_start_date__lte=end)
            salary_per_cutoff = salary_setting.salary_per_cutoff or Decimal('0.00')
        except EmployeeSalarySetting.DoesNotExist:
            # Try to get any active salary setting
            salary_setting = EmployeeSalarySetting.objects.filter(employee=emp, is_active=True).first()
            if salary_setting:
                salary_per_cutoff = salary_setting.salary_per_cutoff or Decimal('0.00')
        except Exception:
            pass
        
        # Get attendance records
        attendance_records = Attendance.objects.filter(employee=emp, date__range=(start, end))
        
        # Calculate hours (for reference only - HR inputs OT/NSD manually)
        days_present = 0
        total_late_minutes = Decimal('0.00')
        
        for att in attendance_records:
            if att.clock_in and att.clock_out:
                days_present += 1
        
        # Total days in period
        total_days = (end - start).days + 1
        # Absent = days not present
        absent_days = max(0, total_days - days_present)
        
        # Calculate hourly rate for absent amount
        working_days = 10  # Approximate working days per cutoff
        hourly_rate = (salary_per_cutoff / Decimal(working_days * 8)).quantize(ROUND) if salary_per_cutoff > 0 else Decimal('0.00')
        absent_amount = (Decimal(absent_days) * hourly_rate * Decimal(8)).quantize(ROUND)
        
        # Get loan deductions
        from .payroll_models import Loan
        loans = Loan.objects.filter(employee=emp, status='approved')
        loan_deduction = sum([l.per_cutoff or Decimal('0.00') for l in loans], Decimal('0.00'))
        
        # No automatic statutory deductions - HR inputs manually in batch/individual payroll
        
        # Calculate totals (HR inputs OT, NSD, Late manually)
        total_deductions = absent_amount + loan_deduction
        gross = salary_per_cutoff  # No OT/NSD added automatically
        net = (gross - total_deductions).quantize(ROUND)
        
        preview_list.append({
            'employee': emp, 
            'pay': {
                'gross': gross,
                'total_additions': Decimal('0.00'),  # HR inputs manually
                'total_deductions': total_deductions,
                'net': net,
                'details': {
                    'salary_per_cutoff': salary_per_cutoff,
                    'ot_amount': Decimal('0.00'),  # HR inputs manually
                    'nsd_amount': Decimal('0.00'),  # HR inputs manually
                    'absent_amount': absent_amount,
                    'late_deduction': Decimal('0.00'),  # HR inputs manually
                    'loan_deduction': loan_deduction,
                    'statutory_deductions': Decimal('0.00'),  # HR inputs manually
                }
            },
            'department': getattr(emp, 'departmentlink', None),
            'position': getattr(emp, 'positionlink', None),
        })
        
        # Accumulate totals
        total_net += net
        total_gross += gross
        total_absent += absent_amount
        total_late += Decimal('0.00')
        total_loans += loan_deduction
        total_basic += salary_per_cutoff

    # Get departments for filter dropdown
    departments = Department.objects.all()

    # Month choices for template
    months = [(i, str(i)) for i in range(1, 13)]
    years = [(y, str(y)) for y in range(2024, 2029)]

    return render(request, 'hr/default/payroll/preview.html', {
        'preview': preview_list,
        'month':   month,
        'year':    year,
        'cutoff':  cutoff,
        'months': months,
        'years': years,
        'total_net': total_net.quantize(Decimal('0.01')),
        'total_deductions': total_deductions.quantize(Decimal('0.01')),
        'total_gross': total_gross.quantize(Decimal('0.01')),
        'total_absent': total_absent.quantize(Decimal('0.01')),
        'total_loans': total_loans.quantize(Decimal('0.01')),
        'total_basic': total_basic.quantize(Decimal('0.01')),
        'departments': departments,
        'selected_department': department_id,
        'selected_status': status_filter,
    })


# ════════════════════════════════════════════════════════════
# Payroll Finalize (creates PayrollRecord + Payouts)
# ════════════════════════════════════════════════════════════
@login_required
def payroll_finalize(request):
    if request.method == 'POST':
        month  = int(request.POST['month'])
        year   = int(request.POST['year'])
        cutoff = request.POST['cutoff']

        if cutoff == '1':
            start = date(year, month, 1)
            end   = date(year, month, 15)
        else:
            last_day = calendar.monthrange(year, month)[1]
            start = date(year, month, 16)
            end   = date(year, month, last_day)

        # Get the current user from session-based auth
        current_user = get_current_user(request)
        
        pr = PayrollRecord.objects.create(month=month, year=year, cutoff=cutoff, created_by=current_user)
        employees = Staff.objects.all()

        for emp in employees:
            try:
                shift_rule = EmployeeShiftRule.objects.get(rank=emp.rank, shift=emp.shift)
            except EmployeeShiftRule.DoesNotExist:
                shift_rule = None

            pay      = compute_payroll_for_cutoff(emp, start, end, cutoff, shift_rule)
            bank_acc = BankAccount.objects.filter(employee=emp, is_primary=True).first()

            Payout.objects.create(
                payroll_record=pr,
                employee=emp,
                bank_account=bank_acc,
                gross=pay['gross'],
                total_additions=pay['total_additions'],
                total_deductions=pay['total_deductions'],
                net=pay['net'],
                cutoff=cutoff,
                month=month,
                year=year,
            )

        pr.finalized = True
        pr.save()
        return redirect('human_resource:payroll_record_detail', pk=pr.pk)

    return render(request, 'hr/default/payroll/finalize_form.html', {'now': date.today()})


# ════════════════════════════════════════════════════════════
# Payroll Record Detail
# ════════════════════════════════════════════════════════════
@login_required
def payroll_record_detail(request, pk):
    payroll = get_object_or_404(PayrollRecord, pk=pk)
    payouts = payroll.payouts.select_related('employee', 'bank_account', 'bank_account__bank')

    total_gross      = sum([p.gross            for p in payouts], Decimal('0.00'))
    total_additions  = sum([p.total_additions  for p in payouts], Decimal('0.00'))
    total_deductions = sum([p.total_deductions for p in payouts], Decimal('0.00'))
    total_net        = sum([p.net              for p in payouts], Decimal('0.00'))

    return render(request, 'hr/default/payroll/record_detail.html', {
        'payroll':          payroll,
        'payouts':          payouts,
        'total_gross':      total_gross,
        'total_additions':  total_additions,
        'total_deductions': total_deductions,
        'total_net':        total_net,
    })


# ════════════════════════════════════════════════════════════
# Bank Accounts
# ════════════════════════════════════════════════════════════
@login_required
def bankaccount_list(request):
    accounts = BankAccount.objects.select_related('employee', 'bank')
    return render(request, 'hr/default/payroll_bank/bankaccount_list.html', {'accounts': accounts})


@login_required
def bankaccount_form(request, pk=None):
    account = get_object_or_404(BankAccount, pk=pk) if pk else None

    if request.method == 'POST':
        employee_id    = request.POST.get('employee')
        bank_id        = request.POST.get('bank')
        account_number = request.POST.get('account_number')
        is_primary     = 'is_primary' in request.POST

        if not employee_id or not bank_id or not account_number:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'hr/default/payroll_bank/bankaccount_form.html', {
                'account':   account,
                'employees': Staff.objects.filter(status='active'),
                'banks':     BankType.objects.filter(is_active=True),
            })

        emp  = get_object_or_404(Staff,    pk=employee_id)
        bank = get_object_or_404(BankType, pk=bank_id)

        if account:
            account.employee       = emp
            account.bank           = bank
            account.account_number = account_number
            account.is_primary     = is_primary
            account.save()
            messages.success(request, 'Bank account updated successfully.')
        else:
            BankAccount.objects.create(employee=emp, bank=bank, account_number=account_number, is_primary=is_primary)
            messages.success(request, 'Bank account created successfully.')

        return redirect('human_resource:bankaccount_list')

    return render(request, 'hr/default/payroll_bank/bankaccount_form.html', {
        'account':   account,
        'employees': Staff.objects.filter(status='active'),
        'banks':     BankType.objects.filter(is_active=True),
    })


# ════════════════════════════════════════════════════════════
# Loans
# ════════════════════════════════════════════════════════════
@login_required
def loan_list(request):
    loans = Loan.objects.select_related('employee').order_by('-created_at')
    
    # Calculate summary statistics
    from django.db.models import Sum, Count
    total_balance = loans.aggregate(total=Sum('balance'))['total'] or 0
    approved_count = loans.filter(status='approved').count()
    pending_count = loans.filter(status='pending').count()
    
    # Get monthly payment totals from PayoutDetail (access year/month through payout FK)
    from .payroll_models import PayoutDetail
    monthly_payments = []
    payout_data = PayoutDetail.objects.filter(
        loan_deduction__gt=0
    ).values('payout__year', 'payout__month').annotate(
        total=Sum('loan_deduction'),
        count=Count('id')
    ).order_by('-payout__year', '-payout__month')[:6]
    
    import calendar
    for p in payout_data:
        month_num = p['payout__month']
        year_num = p['payout__year']
        month_name = calendar.month_abbr[month_num] if month_num else 'N/A'
        monthly_payments.append({
            'month_name': f"{month_name} {year_num}",
            'total': p['total'],
            'count': p['count']
        })
    
    return render(request, 'hr/default/payroll_loans/loan_list.html', {
        'loans': loans,
        'total_balance': total_balance,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'monthly_payments': monthly_payments
    })


@login_required
def loan_form(request, pk=None):
    loan = get_object_or_404(Loan, pk=pk) if pk else None

    if request.method == 'POST':
        emp = get_object_or_404(Staff, pk=request.POST['employee'])
        if loan:
            loan.employee      = emp
            loan.principal     = request.POST['principal']
            loan.interest_rate = request.POST['interest_rate']
            loan.term_months   = request.POST['term_months']
            loan.start_date    = request.POST['start_date']
            loan.status        = request.POST['status']
            loan.save()
        else:
            Loan.objects.create(
                employee=emp,
                principal=request.POST['principal'],
                interest_rate=request.POST['interest_rate'],
                term_months=request.POST['term_months'],
                start_date=request.POST['start_date'],
                status=request.POST['status'],
            )
        return redirect('human_resource:loan_list')

    return render(request, 'hr/default/payroll_loans/loan_form.html', {
        'loan':      loan,
        'employees': Staff.objects.filter(status='active'),
        'loan_status': Loan.STATUS,
    })


# ════════════════════════════════════════════════════════════
# Payout List
# ════════════════════════════════════════════════════════════
# FEATURES:
# - Department filter added
# - Employee dropdown dynamically filtered by selected department (client-side)
# - Uses employee__departmentlink for efficient querying
@login_required
def payout_list(request):
    filter_month    = request.GET.get('month')
    filter_year     = request.GET.get('year')
    filter_status   = request.GET.get('status')
    filter_employee = request.GET.get('employee')
    # Added: filter by department using departmentlink ForeignKey
    filter_department = request.GET.get('department')
    # Added: filter by released status
    filter_released = request.GET.get('released')

    payouts = Payout.objects.select_related(
        'employee', 'employee__departmentlink', 'bank_account', 'payroll_record', 'details'
    )

    if filter_month and filter_month.isdigit():    payouts = payouts.filter(month=int(filter_month))
    if filter_year and filter_year.isdigit():     payouts = payouts.filter(year=int(filter_year))
    if filter_status == 'finalized':
        payouts = payouts.filter(payroll_record__finalized=True)
    elif filter_status == 'draft':
        payouts = payouts.filter(payroll_record__finalized=False)
    if filter_employee and filter_employee.isdigit(): payouts = payouts.filter(employee__id=int(filter_employee))
    # Added: filter by departmentlink__id
    if filter_department and filter_department.isdigit(): payouts = payouts.filter(employee__departmentlink__id=int(filter_department))
    # Added: filter by released status
    if filter_released == 'released':
        payouts = payouts.filter(released=True)
    elif filter_released == 'unreleased':
        payouts = payouts.filter(released=False)

    payouts = payouts.order_by('-year', '-month', '-cutoff', 'employee__last_name')

    total_gross      = sum([p.gross            for p in payouts], Decimal('0.00'))
    total_deductions = sum([p.total_deductions for p in payouts], Decimal('0.00'))
    total_net        = sum([p.net              for p in payouts], Decimal('0.00'))

    total_de_minimis = Decimal('0.00')
    for payout in payouts:
        if hasattr(payout, 'details') and payout.details:
            total_de_minimis += payout.details.total_de_minimis or Decimal('0.00')

    total_earnings = total_gross + total_de_minimis

    current_year = date.today().year
    # Changed: Show only current year and future years
    years  = range(current_year, current_year + 3)
    months = [
        (1,'January'),(2,'February'),(3,'March'),(4,'April'),
        (5,'May'),(6,'June'),(7,'July'),(8,'August'),
        (9,'September'),(10,'October'),(11,'November'),(12,'December'),
    ]
    employees = Staff.objects.select_related('departmentlink').order_by('last_name', 'first_name')
    # Added: Get departments for filter dropdown
    departments = Department.objects.filter(is_active=True).order_by('department_name')

    return render(request, 'hr/default/payout/payout_list.html', {
        'payouts':           payouts,
        'years':             years,
        'months':            months,
        'employees':         employees,
        'departments':       departments,  # Added: for department filter dropdown
        'selected_month':    int(filter_month)    if filter_month    else None,
        'selected_year':     int(filter_year)     if filter_year     else None,
        'selected_status':   filter_status,
        'selected_employee': int(filter_employee)  if filter_employee else None,
        'selected_department': int(filter_department) if filter_department else None,  # Added: preserve selected department
        'selected_released': filter_released,  # Added: preserve selected release status
        'total_gross':       total_gross,
        'total_deductions':  total_deductions,
        'total_net':         total_net,
        'total_de_minimis':  total_de_minimis,
        'total_earnings':    total_earnings,
    })


# ════════════════════════════════════════════════════════════
# Payout Detail
# ════════════════════════════════════════════════════════════
@login_required
def payout_detail(request, pk):
    payout = get_object_or_404(Payout, pk=pk)

    from .payroll_models import PayoutDetail
    details, _ = PayoutDetail.objects.get_or_create(
        payout=payout,
        defaults={'basic_salary': payout.gross}
    )

    from .payroll_settings_models import DeMinimisEntry, DeductionEntry
    de_minimis_entries = DeMinimisEntry.objects.filter(payout=payout).select_related('de_minimis_type')
    total_de_minimis   = sum([e.amount for e in de_minimis_entries], Decimal('0.00'))
    deduction_entries  = DeductionEntry.objects.filter(payout=payout).select_related('deduction_type')

    total_earnings = (
        (details.basic_salary         or Decimal('0.00')) +
        (details.tips_others          or Decimal('0.00')) +
        (details.lodging_allowance    or Decimal('0.00')) +
        (details.incentives           or Decimal('0.00')) +
        (details.holiday_pay          or Decimal('0.00')) +
        (details.regular_holiday_pay  or Decimal('0.00')) +
        (details.overtime_pay         or Decimal('0.00')) +
        (details.night_differential   or Decimal('0.00'))
    )

    # Calculate leave deduction (unpaid) = leave_days_unpaid * daily_rate
    daily_rate = details.get_daily_rate()
    leave_deduction_amount = (details.leave_days_unpaid * daily_rate).quantize(Decimal('0.01')) if details.leave_days_unpaid else Decimal('0.00')

    return render(request, 'hr/default/payout/payout_detail.html', {
        'payout':            payout,
        'details':           details,
        'de_minimis_entries':de_minimis_entries,
        'total_de_minimis':  total_de_minimis,
        'total_earnings':    total_earnings,
        'deduction_entries': deduction_entries,
        'leave_deduction_amount': leave_deduction_amount,
    })


# ════════════════════════════════════════════════════════════
# Payout Finalize
# ════════════════════════════════════════════════════════════
@login_required
def payout_finalize(request, payout_id):
    payout = get_object_or_404(Payout, id=payout_id)

    if payout.payroll_record.finalized:
        messages.warning(request, 'This payout has already been finalized.')
        return redirect('human_resource:payout_detail', pk=payout.id)

    # Show confirmation page for GET request
    if request.method == 'GET':
        return render(request, 'hr/default/payout/payout_finalize_confirm.html', {'payout': payout})

    # Process finalization for POST request
    if request.method == 'POST':
        payout.payroll_record.finalized = True
        # Get the current user from session-based auth
        current_user = get_current_user(request)
        if current_user:
            payout.payroll_record.finalized_by = current_user
        payout.payroll_record.finalized_at = timezone.now()
        payout.payroll_record.save()

        messages.success(request, f'Payout for {payout.employee.first_name} {payout.employee.last_name} has been finalized.')
        return redirect('human_resource:payout_list')

    return redirect('human_resource:payout_detail', pk=payout.id)


# ════════════════════════════════════════════════════════════
# Payout Release (Mark salary as released)
# ════════════════════════════════════════════════════════════
@login_required
def payout_release(request, payout_id):
    """Release salary for a payout - marks as released/paid"""
    payout = get_object_or_404(Payout, id=payout_id)
    
    if not payout.payroll_record.finalized:
        messages.warning(request, 'This payout must be finalized before releasing.')
        return redirect('human_resource:payout_detail', pk=payout.id)
    
    if payout.released:
        messages.warning(request, 'This payout has already been released.')
        return redirect('human_resource:payout_detail', pk=payout.id)

    # Show confirmation page for GET request
    if request.method == 'GET':
        return render(request, 'hr/default/payout/payout_release_confirm.html', {'payout': payout})

    # Process release for POST request
    if request.method == 'POST':
        payout.released = True
        # Get the current user from session-based auth
        current_user = get_current_user(request)
        if current_user:
            payout.released_by = current_user
        payout.released_at = timezone.now()
        payout.save()

        messages.success(request, f'Salary for {payout.employee.first_name} {payout.employee.last_name} has been released.')
        return redirect('human_resource:payout_list')

    return redirect('human_resource:payout_detail', pk=payout.id)


# ════════════════════════════════════════════════════════════
# Batch Release (Release multiple payouts at once)
# ════════════════════════════════════════════════════════════
@login_required
def payout_batch_release(request):
    """Batch release multiple payouts at once"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('human_resource:payout_list')
    
    payout_ids = request.POST.getlist('payout_ids')
    
    if not payout_ids:
        messages.warning(request, 'No payouts selected for release')
        return redirect('human_resource:payout_list')
    
    released_count = 0
    # Get the current user from session-based auth
    current_user = get_current_user(request)
    for payout_id in payout_ids:
        try:
            payout = Payout.objects.get(id=payout_id)
            if payout.payroll_record.finalized and not payout.released:
                payout.released = True
                if current_user:
                    payout.released_by = current_user
                payout.released_at = timezone.now()
                payout.save()
                released_count += 1
        except Payout.DoesNotExist:
            continue
    
    messages.success(request, f'{released_count} payout(s) have been released.')
    return redirect('human_resource:payout_list')


# ════════════════════════════════════════════════════════════
# Export Payouts to CSV
# ════════════════════════════════════════════════════════════
@login_required
def payout_export_csv(request):
    """Export payout history to CSV"""
    import csv
    from django.http import HttpResponse
    
    try:
        filter_month    = request.GET.get('month')
        filter_year     = request.GET.get('year')
        filter_status   = request.GET.get('status')
        filter_employee = request.GET.get('employee')
        filter_department = request.GET.get('department')
        filter_released = request.GET.get('released')

        payouts = Payout.objects.select_related(
            'employee', 'employee__departmentlink', 'bank_account', 'payroll_record'
        )

        if filter_month and filter_month.isdigit():    payouts = payouts.filter(month=int(filter_month))
        if filter_year and filter_year.isdigit():     payouts = payouts.filter(year=int(filter_year))
        if filter_status == 'finalized':
            payouts = payouts.filter(payroll_record__finalized=True)
        elif filter_status == 'draft':
            payouts = payouts.filter(payroll_record__finalized=False)
        if filter_employee and filter_employee.isdigit(): payouts = payouts.filter(employee__id=int(filter_employee))
        if filter_department and filter_department.isdigit(): payouts = payouts.filter(employee__departmentlink__id=int(filter_department))
        if filter_released == 'released':
            payouts = payouts.filter(released=True)
        elif filter_released == 'unreleased':
            payouts = payouts.filter(released=False)

        payouts = payouts.order_by('-year', '-month', '-cutoff', 'employee__last_name')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payout_history.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee Number', 'Employee Name', 'Department', 'Period', 'Cutoff',
            'Gross', 'Total Additions', 'Total Deductions', 'Net Pay',
            'Status', 'Released', 'Bank Account'
        ])
        
        # Month names mapping
        MONTH_NAMES = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        CUTOFF_NAMES = {'1': '1st', '2': '2nd'}
        
        for p in payouts:
            try:
                employee_name = f"{p.employee.first_name} {p.employee.last_name}" if p.employee else 'N/A'
                employee_number = p.employee.employee_number if p.employee else 'N/A'
                department_name = p.employee.departmentlink.department_name if p.employee and p.employee.departmentlink else ''
            except Exception:
                employee_name = 'N/A'
                employee_number = 'N/A'
                department_name = ''
            
            month_name = MONTH_NAMES.get(p.month, str(p.month))
            cutoff_name = CUTOFF_NAMES.get(p.cutoff, p.cutoff)
            
            writer.writerow([
                employee_number,
                employee_name,
                department_name,
                f"{month_name} {p.year}",
                cutoff_name,
                str(p.gross),
                str(p.total_additions),
                str(p.total_deductions),
                str(p.net),
                'Finalized' if p.payroll_record.finalized else 'Draft',
                'Yes' if p.released else 'No',
                p.bank_account.account_number if p.bank_account else ''
            ])
        
        return response
    except Exception as e:
        messages.error(request, f'Error exporting CSV: {str(e)}')
        return redirect('human_resource:payout_list')


# ════════════════════════════════════════════════════════════
# Payout PDF
# ════════════════════════════════════════════════════════════
@login_required
def payout_pdf(request, payout_id):
    payout = get_object_or_404(Payout, id=payout_id)
    html_string = render(
        request,
        'hr/default/payroll/payout/payout_details.html',
        {'payout': payout}
    ).content.decode('utf-8')

    response = HttpResponse(content_type='application/pdf')
    emp_name = f"{payout.employee.first_name}_{payout.employee.last_name}"
    response['Content-Disposition'] = (
        f'filename=payslip_{emp_name}_{payout.month}_{payout.year}.pdf'
    )
    HTML(string=html_string).write_pdf(response)
    return response


# ════════════════════════════════════════════════════════════
# Batch Payroll Preview
# ════════════════════════════════════════════════════════════
@login_required
def batch_payroll_preview(request):
    from .payroll_settings_models import EmployeeSalarySetting, DeMinimisType, DeductionType
    from .models import Attendance

    month  = int(request.GET.get('month',  date.today().month))
    year   = int(request.GET.get('year',   date.today().year))
    cutoff = request.GET.get('cutoff', '1')

    de_minimis_types = DeMinimisType.objects.filter(is_active=True).order_by('display_order')
    deduction_types  = DeductionType.objects.filter(is_active=True).order_by('display_order')

    start_date, end_date, _ = calculate_cutoff_dates(month, year, cutoff)

    active_employees      = Staff.objects.filter(status='active')
    total_active_employees = active_employees.count()

    existing_payouts = Payout.objects.filter(month=month, year=year, cutoff=cutoff).select_related('payroll_record', 'employee')

    finalized_employees = []
    draft_employees     = []
    for payout in existing_payouts:
        emp_data = {
            'name':     f"{payout.employee.first_name} {payout.employee.last_name}",
            'net':      payout.net,
            'payout_id':payout.id,
            'employee': payout.employee,
        }
        if payout.payroll_record and payout.payroll_record.finalized:
            finalized_employees.append(emp_data)
        else:
            draft_employees.append(emp_data)

    skipped_count         = len(finalized_employees) + len(draft_employees)
    processed_employee_ids = {pe['employee'].id for pe in finalized_employees + draft_employees}

    preview_list = []
    for emp in active_employees:
        if emp.id in processed_employee_ids:
            continue

        salary_per_cutoff = Decimal('0.00')
        work_schedule     = '9.5H'
        try:
            from .payroll_settings_models import EmployeeSalarySetting
            salary_setting    = EmployeeSalarySetting.objects.get(employee=emp, is_active=True, effective_start_date__lte=end_date)
            salary_per_cutoff = salary_setting.salary_per_cutoff
            work_schedule     = salary_setting.work_schedule
        except Exception:
            monthly_salary = getattr(emp, 'monthly_salary', None)
            if monthly_salary:
                salary_per_cutoff = (Decimal(str(monthly_salary)) / Decimal('2')).quantize(ROUND)

        attendance_records = Attendance.objects.filter(employee=emp, date__range=(start_date, end_date))

        days_present    = 0
        total_ot_hours  = Decimal('0.00')
        total_nsd_hours = Decimal('0.00')
        for att in attendance_records:
            if att.clock_in and att.clock_out:
                days_present += 1
                if hasattr(att, 'overtime_hours') and att.overtime_hours:
                    total_ot_hours  += Decimal(str(att.overtime_hours))
                if hasattr(att, 'nsd_hours') and att.nsd_hours:
                    total_nsd_hours += Decimal(str(att.nsd_hours))

        working_days = count_working_days(start_date, end_date)

        preview_list.append({
            'employee':         emp,
            'name':             f"{emp.first_name} {emp.last_name}",
            'salary_per_cutoff':salary_per_cutoff,
            'work_schedule':    work_schedule,
            'total_ot_hours':   total_ot_hours,
            'total_nsd_hours':  total_nsd_hours,
            'days_present':     days_present,
            'working_days':     working_days,
            'gross':            salary_per_cutoff,
            'net':              salary_per_cutoff,
        })

    return render(request, 'hr/default/payroll/batch_preview.html', {
        'employees':            active_employees,
        'preview_list':         preview_list,
        'to_process_employees': preview_list,
        'month':                month,
        'year':                 year,
        'cutoff':               cutoff,
        'start':                start_date,
        'end':                  end_date,
        'total_active_employees': total_active_employees,
        'skipped_count':        skipped_count,
        'finalized_employees':  finalized_employees,
        'draft_employees':      draft_employees,
        'de_minimis_types':     de_minimis_types,
        'deduction_types':      deduction_types,
    })


# ════════════════════════════════════════════════════════════
# Batch Payroll Finalize
# ════════════════════════════════════════════════════════════
@login_required
def batch_payroll_finalize(request):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('human_resource:payroll_preview')

    from .payroll_models import PayoutDetail
    from .payroll_settings_models import DeMinimisEntry, DeMinimisType, DeductionType, DeductionEntry

    month  = int(request.POST.get('month',  date.today().month))
    year   = int(request.POST.get('year',   date.today().year))
    cutoff = request.POST.get('cutoff', '1')

    start_date, end_date, working_days = calculate_cutoff_dates(month, year, cutoff)

    # Get the current user from session-based auth
    current_user = get_current_user(request)
    
    payroll_record, _ = PayrollRecord.objects.get_or_create(
        month=month, year=year, cutoff=cutoff,
        defaults={'created_by': current_user}
    )

    employee_ids = [
        request.POST.get(key)
        for key in request.POST
        if key.endswith('_employee_id') and request.POST.get(key)
    ]

    success_count = 0
    error_count   = 0

    for emp_id in employee_ids:
        try:
            employee = Staff.objects.get(pk=emp_id)
            prefix   = f'emp_{emp_id}_'

            bank_account = BankAccount.objects.filter(employee=employee, is_primary=True).first()

            # Delete existing draft if present
            existing = Payout.objects.filter(
                employee=employee, month=month, year=year, cutoff=cutoff,
                payroll_record__finalized=False
            ).first()
            if existing:
                from .payroll_models import PayoutDetail as PD
                PD.objects.filter(payout=existing).delete()
                existing.delete()

            # ── Read all form values ───────────────────────────────────────
            basic_salary      = safe_decimal(request.POST.get(f'{prefix}basic_salary',    '0'))
            gross             = safe_decimal(request.POST.get(f'{prefix}gross',           '0'))
            total_additions   = safe_decimal(request.POST.get(f'{prefix}total_additions', '0'))
            total_deductions  = safe_decimal(request.POST.get(f'{prefix}total_deductions','0'))
            total_demiminis   = safe_decimal(request.POST.get(f'{prefix}total_demiminis', '0'))
            net               = safe_decimal(request.POST.get(f'{prefix}net',             '0'))

            overtime_hours    = safe_decimal(request.POST.get(f'{prefix}overtime_hours',      '0'))
            overtime_pay      = safe_decimal(request.POST.get(f'{prefix}overtime_pay',        '0'))
            nsd_hours         = safe_decimal(request.POST.get(f'{prefix}nsd_hours',           '0'))
            night_differential= safe_decimal(request.POST.get(f'{prefix}night_differential',  '0'))
            holiday_hours     = safe_decimal(request.POST.get(f'{prefix}holiday_hours',       '0'))
            holiday_pay       = safe_decimal(request.POST.get(f'{prefix}holiday_pay',         '0'))
            reg_hol_hours     = safe_decimal(request.POST.get(f'{prefix}regular_holiday_hours','0'))
            reg_hol_pay       = safe_decimal(request.POST.get(f'{prefix}regular_holiday_pay', '0'))
            incentives        = safe_decimal(request.POST.get(f'{prefix}incentives',          '0'))
            tips_others       = safe_decimal(request.POST.get(f'{prefix}tips_others',         '0'))
            lodging_allowance = safe_decimal(request.POST.get(f'{prefix}lodging_allowance',   '0'))

            # ✅ Leave days — HR-entered directly (no hidden duplicate in batch form)
            leave_days_paid   = safe_decimal(request.POST.get(f'{prefix}leave_days_paid',   '0'))
            leave_days_unpaid = safe_decimal(request.POST.get(f'{prefix}leave_days_unpaid', '0'))

            withholding_tax   = safe_decimal(request.POST.get(f'{prefix}withholding_tax',   '0'))
            late_minutes      = safe_decimal(request.POST.get(f'{prefix}late_minutes',      '0'))
            late_hours_equiv  = safe_decimal(request.POST.get(f'{prefix}late_hours_equivalent','0'))
            late_deduction    = safe_decimal(request.POST.get(f'{prefix}late_deduction',    '0'))
            absence_deduction = safe_decimal(request.POST.get(f'{prefix}absence_deduction', '0'))
            other_deductions  = safe_decimal(request.POST.get(f'{prefix}other_deductions',  '0'))
            loan_deduction    = safe_decimal(request.POST.get(f'{prefix}loan_deduction',    '0'))
            note              = request.POST.get(f'{prefix}note', '')

            # ── Create Payout ──────────────────────────────────────────────
            payout = Payout.objects.create(
                payroll_record=payroll_record,
                employee=employee,
                bank_account=bank_account,
                gross=gross,
                total_additions=total_additions,
                total_deductions=total_deductions,
                net=net,
                cutoff=cutoff,
                month=month,
                year=year,
            )

            # ── Create PayoutDetail ────────────────────────────────────────
            detail = PayoutDetail.objects.create(
                payout=payout,
                basic_salary=basic_salary,
                housing_allowance=Decimal('0.00'),
                transportation_allowance=Decimal('0.00'),
                meal_allowance=Decimal('0.00'),
                medical_allowance=Decimal('0.00'),
                other_allowances=Decimal('0.00'),

                overtime_hours=overtime_hours,
                overtime_pay=overtime_pay,
                nsd_hours=nsd_hours,
                night_differential=night_differential,

                holiday_hours=holiday_hours,
                holiday_pay=holiday_pay,
                regular_holiday_hours=reg_hol_hours,
                regular_holiday_pay=reg_hol_pay,

                incentives=incentives,
                tips_others=tips_others,
                lodging_allowance=lodging_allowance,

                # ✅ Leave days saved correctly
                leave_days_paid=leave_days_paid,
                leave_days_unpaid=leave_days_unpaid,

                working_days=working_days,
                days_present=Decimal('0.00'),
                days_absent=Decimal('0.00'),

                late_minutes=late_minutes,
                late_hours_equivalent=late_hours_equiv,
                late_deduction=late_deduction,
                late_occurrences=0,

                absence_deduction=absence_deduction,
                loan_deduction=loan_deduction,
                other_deductions=other_deductions,

                sss_contribution=Decimal('0.00'),
                philhealth_contribution=Decimal('0.00'),
                pagibig_contribution=Decimal('0.00'),

                taxable_income=gross,
                tax_bracket='',
                withholding_tax=withholding_tax,

                note=note,
            )

            # ── De Minimis entries ─────────────────────────────────────────
            de_minimis_types = DeMinimisType.objects.filter(is_active=True)
            total_de_minimis = Decimal('0.00')
            for dm_type in de_minimis_types:
                amount = safe_decimal(request.POST.get(f'{prefix}demiminis_{dm_type.id}', '0'))
                if amount > 0:
                    DeMinimisEntry.objects.create(payout=payout, de_minimis_type=dm_type, amount=amount)
                    total_de_minimis += amount

            # ── Dynamic Deduction entries ──────────────────────────────────
            deduction_types          = DeductionType.objects.filter(is_active=True)
            total_dynamic_deductions = Decimal('0.00')
            total_govt_deductions    = Decimal('0.00')
            for ded_type in deduction_types:
                amount = safe_decimal(request.POST.get(f'{prefix}deduction_{ded_type.id}', '0'))
                if amount > 0:
                    DeductionEntry.objects.create(payout=payout, deduction_type=ded_type, amount=amount)
                    total_dynamic_deductions += amount
                    if ded_type.is_government:
                        total_govt_deductions += amount

            # Auto-assign SSS / PhilHealth / Pag-IBIG
            for ded_type in deduction_types:
                entry = DeductionEntry.objects.filter(payout=payout, deduction_type=ded_type).first()
                if entry and ded_type.is_government:
                    if ded_type.code == 'SSS':
                        detail.sss_contribution = entry.amount
                    elif ded_type.code == 'PHILHEALTH':
                        detail.philhealth_contribution = entry.amount
                    elif ded_type.code == 'PAGIBIG':
                        detail.pagibig_contribution = entry.amount

            detail.total_de_minimis           = total_de_minimis
            detail.total_dynamic_deductions   = total_dynamic_deductions
            detail.total_government_deductions = total_govt_deductions + withholding_tax
            detail.save()

            success_count += 1

        except Exception as e:
            error_count += 1
            import traceback
            print(f"❌ Error processing employee {emp_id}: {e}")
            print(traceback.format_exc())

    if success_count > 0:
        # Mark the payroll record as finalized
        payroll_record.finalized = True
        # Get the current user from session-based auth
        current_user = get_current_user(request)
        if current_user:
            payroll_record.finalized_by = current_user
        payroll_record.finalized_at = timezone.now()
        payroll_record.save()
        
        messages.success(
            request,
            f'Batch payroll finalized: {success_count} employee(s) saved.'
            + (f' {error_count} failed.' if error_count else '')
        )
    else:
        messages.error(request, f'No payroll records saved. {error_count} error(s) occurred.')

    return redirect('human_resource:payroll_history_list')


# ════════════════════════════════════════════════════════════
# Individual Payroll — selection page
# ════════════════════════════════════════════════════════════
@login_required
def individual_payroll(request):
    months = [
        (1,'January'),(2,'February'),(3,'March'),(4,'April'),
        (5,'May'),(6,'June'),(7,'July'),(8,'August'),
        (9,'September'),(10,'October'),(11,'November'),(12,'December'),
    ]
    current_month, current_year, current_cutoff, _, _, _ = get_current_payroll_period()
    employees  = Staff.objects.filter(status='active')
    year_range = range(current_year - 3, current_year + 2)

    return render(request, 'hr/default/payroll/individual_payroll.html', {
        'employees':     employees,
        'months':        months,
        'current_month': current_month,
        'current_year':  current_year,
        'current_cutoff':current_cutoff,
        'year_range':    year_range,
    })


# ════════════════════════════════════════════════════════════
# Individual Payroll Preview
# ════════════════════════════════════════════════════════════
@login_required
def individual_payroll_preview(request):
    # Handle both POST (initial form) and GET (date filter apply)
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        month       = int(request.POST.get('month',  date.today().month))
        year        = int(request.POST.get('year',   date.today().year))
        cutoff      = request.POST.get('cutoff', '1')
        reprocess   = request.POST.get('reprocess') == 'true'
    elif request.method == 'GET':
        # Get from GET parameters for date filter
        employee_id = request.GET.get('employee')
        month       = int(request.GET.get('month',  date.today().month))
        year        = int(request.GET.get('year',   date.today().year))
        cutoff      = request.GET.get('cutoff', '1')
        reprocess   = request.GET.get('reprocess') == 'true'
    else:
        return redirect('human_resource:individual_payroll')

    if not employee_id:
        return redirect('human_resource:individual_payroll')
    
    # Check for custom date range from GET parameters
    custom_start_date = request.GET.get('start_date')
    custom_end_date = request.GET.get('end_date')

    try:
        employee = Staff.objects.get(pk=employee_id)
    except Staff.DoesNotExist:
        messages.error(request, 'Employee not found')
        return redirect('human_resource:individual_payroll')

    existing_payout = Payout.objects.filter(employee=employee, month=month, year=year, cutoff=cutoff).first()
    if existing_payout and not reprocess:
        messages.warning(request,
            f'Payroll already exists for {employee.first_name} {employee.last_name}. '
            f'Check the Payout List or use Reprocess Mode.')

    start_date, end_date, working_days = calculate_cutoff_dates(month, year, cutoff)
    
    # Use custom dates if provided (for date range filter)
    custom_start_date = request.GET.get('start_date')
    custom_end_date = request.GET.get('end_date')
    if custom_start_date and custom_end_date:
        try:
            start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').date()
            # Calculate working days for custom range
            from datetime import timedelta
            working_days = 0
            current = start_date
            while current <= end_date:
                if current.weekday() < 5:  # Monday-Friday
                    working_days += 1
                current += timedelta(days=1)
        except ValueError:
            pass  # Keep original dates if parsing fails

    salary_per_cutoff = Decimal('0.00')
    work_schedule     = '9.5H'
    tier              = None
    try:
        from .payroll_settings_models import EmployeeSalarySetting, TierThresholdSetting
        salary_setting    = EmployeeSalarySetting.objects.get(employee=employee, is_active=True, effective_start_date__lte=end_date)
        salary_per_cutoff = salary_setting.salary_per_cutoff
        work_schedule     = salary_setting.work_schedule
        if salary_setting.tier_id:
            tier = TierThresholdSetting.objects.get(pk=salary_setting.tier_id, is_active=True)
    except Exception:
        monthly_salary = getattr(employee, 'monthly_salary', Decimal('0'))
        if monthly_salary:
            salary_per_cutoff = (monthly_salary / Decimal('2')).quantize(ROUND)

    from .models import Attendance
    from .payroll_settings_models import DeMinimisType, DeductionType
    attendance_records = Attendance.objects.filter(employee=employee, date__range=(start_date, end_date))
    
    # Calculate attendance statistics
    attendance_present = attendance_records.filter(status='present').count()
    attendance_absent = attendance_records.filter(status='absent').count()
    attendance_late = attendance_records.filter(status='late').count()
    attendance_half_day = attendance_records.filter(status='half_day').count() if attendance_records.filter(status='half_day').exists() else 0
    
    # Calculate late minutes
    total_late_minutes = sum(
        (record.late_minutes or 0) for record in attendance_records
    )
    
    de_minimis_types   = DeMinimisType.objects.filter(is_active=True).order_by('display_order')
    deduction_types    = DeductionType.objects.filter(is_active=True).order_by('display_order')
    
    # Calculate loan deduction from approved loans
    from .payroll_models import Loan
    loans = Loan.objects.filter(employee=employee, status='approved')
    loan_deduction = sum([l.per_cutoff or Decimal('0.00') for l in loans], Decimal('0.00'))
    
    return render(request, 'hr/default/payroll/individual_payroll_preview_enhanced.html', {
        'employee':              employee,
        'month':                 month,
        'year':                  year,
        'cutoff':                cutoff,
        'start_date':            start_date,
        'end_date':              end_date,
        'working_days':          working_days,
        'salary_per_cutoff':     salary_per_cutoff,
        'work_schedule':         work_schedule,
        'tier':                  tier,
        'attendance_records':    attendance_records,
        'attendance_present':    attendance_present,
        'attendance_absent':     attendance_absent,
        'attendance_late':       attendance_late,
        'attendance_half_day':   attendance_half_day,
        'total_late_minutes':    total_late_minutes,
        'overtime_hours':        Decimal('0.00'),
        'nsd_hours':             Decimal('0.00'),
        'tips_others':           Decimal('0.00'),
        'lodging_allowance':     Decimal('0.00'),
        'holiday_hours':         Decimal('0.00'),
        'regular_holiday_hours': Decimal('0.00'),
        'incentives':            Decimal('0.00'),
        'leave_days_paid':       Decimal('0.00'),
        'leave_days_unpaid':     Decimal('0.00'),
        'days_absent':           Decimal('0.00'),
        'tax_amount':            Decimal('0.00'),
        'other_deductions':      Decimal('0.00'),
        'loan_deduction':        loan_deduction,
        'de_minimis_types':      de_minimis_types,
        'deduction_types':       deduction_types,
        'reprocess':             reprocess,
        'existing_payout':       existing_payout,
    })


# ════════════════════════════════════════════════════════════
# Individual Payroll Finalize  ← KEY FIX HERE
# ════════════════════════════════════════════════════════════
@login_required
def individual_payroll_finalize(request):
    """
    Save individual payroll.

    ALL hours and pay amounts come from the HTML form (HR-entered visible
    inputs whose values JS copied to hidden fields).  We never overwrite
    them from attendance records or the LeaveRequest table.
    """
    if request.method != 'POST':
        messages.success(request, 'Individual payroll finalized')
        return redirect('human_resource:payout_list')

    try:
        from .payroll_models import PayoutDetail
        from .models import Attendance

        employee_id = request.POST.get('employee_id')
        month       = int(request.POST.get('month',  date.today().month))
        year        = int(request.POST.get('year',   date.today().year))
        cutoff      = request.POST.get('cutoff', '1')

        employee     = get_object_or_404(Staff, pk=employee_id)
        bank_account = BankAccount.objects.filter(employee=employee, is_primary=True).first()
        reprocess    = request.POST.get('reprocess') == 'true'

        start_date, end_date, working_days = calculate_cutoff_dates(month, year, cutoff)

        # ── Reprocess guard ────────────────────────────────────────────────
        existing_payout = Payout.objects.filter(
            employee=employee, month=month, year=year, cutoff=cutoff
        ).first()

        if existing_payout and not reprocess:
            messages.error(request,
                f'Payroll already exists for {employee.first_name} {employee.last_name}. '
                f'Use Reprocess Mode to overwrite.')
            return redirect('human_resource:individual_payroll')

        if existing_payout and reprocess:
            PayoutDetail.objects.filter(payout=existing_payout).delete()
            existing_payout.delete()

        # ── Salary setting ─────────────────────────────────────────────────
        salary_per_cutoff = Decimal('0.00')
        work_schedule     = '9.5H'
        try:
            from .payroll_settings_models import EmployeeSalarySetting
            salary_setting    = EmployeeSalarySetting.objects.get(employee=employee, is_active=True, effective_start_date__lte=end_date)
            salary_per_cutoff = safe_decimal(salary_setting.salary_per_cutoff, '0')
            work_schedule     = salary_setting.work_schedule
        except Exception:
            monthly_salary    = safe_decimal(getattr(employee, 'monthly_salary', '0'), '0')
            salary_per_cutoff = (monthly_salary / Decimal('2')).quantize(ROUND)

        # ── Attendance — only for days_present count ───────────────────────
        attendance_records = Attendance.objects.filter(employee=employee, date__range=(start_date, end_date))
        days_present       = Decimal(str(sum(1 for a in attendance_records if a.clock_in and a.clock_out)))

        # ── Rate calculation (for server-side fallback only) ───────────────
        daily_rate  = (salary_per_cutoff / Decimal(str(working_days))).quantize(ROUND) if working_days else Decimal('0.00')
        is_flex     = work_schedule == 'FLEX'
        try:
            from .payroll_computation import get_hours_per_day, compute_hourly_rate
            hours_per_day = get_hours_per_day(work_schedule)
            hourly_rate   = compute_hourly_rate(daily_rate, hours_per_day) or Decimal('0.00')
        except Exception:
            hourly_rate = Decimal('0.00')

        # ════════════════════════════════════════════════════════════════
        # ✅ ALL values come from POST (HR-entered + JS-computed hidden fields)
        # ════════════════════════════════════════════════════════════════

        # Hours (from HR visible inputs, synced to hidden h_* fields by JS)
        ot_hours          = safe_decimal(request.POST.get('overtime_hours',        '0'))
        nsd_hours         = safe_decimal(request.POST.get('nsd_hours',             '0'))
        holiday_hours     = safe_decimal(request.POST.get('holiday_hours',         '0'))
        reg_holiday_hours = safe_decimal(request.POST.get('regular_holiday_hours', '0'))
        incentives        = safe_decimal(request.POST.get('incentives',            '0'))
        tips_others       = safe_decimal(request.POST.get('tips_others',           '0'))
        lodging_allowance = safe_decimal(request.POST.get('lodging_allowance',     '0'))

        # ✅ Leave days — from HR inputs (no LeaveRequest loop)
        leave_days_paid   = safe_decimal(request.POST.get('leave_days_paid',   '0'))
        leave_days_unpaid = safe_decimal(request.POST.get('leave_days_unpaid', '0'))
        days_absent       = safe_decimal(request.POST.get('days_absent',       '0'))

        # Computed pay amounts (from JS-computed hidden fields)
        overtime_amount      = safe_decimal(request.POST.get('overtime_amount',    '0'))
        nsd_amount           = safe_decimal(request.POST.get('nsd_amount',         '0'))
        holiday_pay          = safe_decimal(request.POST.get('holiday_pay',        '0'))
        regular_holiday_pay  = safe_decimal(request.POST.get('regular_holiday_pay','0'))

        # Server-side fallback: recompute if JS hidden fields were zero but hours > 0
        if not is_flex:
            if overtime_amount     == 0 and ot_hours > 0:
                overtime_amount    = (ot_hours          * hourly_rate * Decimal('1.25')).quantize(ROUND)
            if nsd_amount          == 0 and nsd_hours > 0:
                nsd_amount         = (nsd_hours         * hourly_rate * Decimal('1.10')).quantize(ROUND)
            if holiday_pay         == 0 and holiday_hours > 0:
                holiday_pay        = (holiday_hours     * hourly_rate * Decimal('1.30')).quantize(ROUND)
            if regular_holiday_pay == 0 and reg_holiday_hours > 0:
                regular_holiday_pay= (reg_holiday_hours * hourly_rate * Decimal('2.00')).quantize(ROUND)

        # ✅ Leave amounts computed from HR-entered days
        leave_addition  = (leave_days_paid   * daily_rate).quantize(ROUND)
        leave_deduction = (leave_days_unpaid * daily_rate).quantize(ROUND)
        absence_deduction = safe_decimal(request.POST.get('absence_deduction', '0'))
        if absence_deduction == 0 and days_absent > 0:
            absence_deduction = (days_absent * daily_rate).quantize(ROUND)

        # Late deduction
        late_minutes          = safe_decimal(request.POST.get('late_minutes',          '0'))
        late_hours_equivalent = safe_decimal(request.POST.get('late_hours_equivalent', '0'))
        late_deduction_amount = safe_decimal(request.POST.get('late_deduction',        '0'))
        if late_deduction_amount == 0 and late_hours_equivalent > 0 and not is_flex:
            late_deduction_amount = (late_hours_equivalent * hourly_rate).quantize(ROUND)

        # Tax & other
        tax_amount       = safe_decimal(request.POST.get('tax',              '0'))
        other_deductions = safe_decimal(request.POST.get('other_deductions', '0'))
        note             = request.POST.get('note', '')

        # Loan deductions
        loans          = Loan.objects.filter(employee=employee, status='approved')
        loan_deduction = sum([l.per_cutoff for l in loans], Decimal('0.00'))

        # ── Totals ─────────────────────────────────────────────────────────
        gross = (
            salary_per_cutoff + overtime_amount + nsd_amount +
            holiday_pay + regular_holiday_pay + incentives +
            tips_others + lodging_allowance + leave_addition
        ).quantize(ROUND)

        # Use the submitted total_deductions from the form (calculated by JavaScript)
        # Then add loan_deduction which is calculated server-side from approved loans
        submitted_total_deductions = safe_decimal(request.POST.get('total_deductions', '0'))
        
        # Start with submitted total (includes tax, late, absence, leave, other, dynamic deductions)
        if submitted_total_deductions > 0:
            total_deductions = submitted_total_deductions + loan_deduction
        else:
            # Fallback: calculate everything including loan
            total_deductions = (
                tax_amount + late_deduction_amount + leave_deduction +
                absence_deduction + loan_deduction + other_deductions
            ).quantize(ROUND)
        
        total_deductions = total_deductions.quantize(ROUND)

        net = (gross - total_deductions).quantize(ROUND)

        # Get the current user from session-based auth
        current_user = get_current_user(request)
        
        # ── Payroll record ─────────────────────────────────────────────────
        payroll_record, _ = PayrollRecord.objects.get_or_create(
            month=month, year=year, cutoff=cutoff,
            defaults={'created_by': current_user}
        )

        # ── Payout ────────────────────────────────────────────────────────
        payout = Payout.objects.create(
            payroll_record=payroll_record,
            employee=employee,
            bank_account=bank_account,
            gross=gross,
            total_additions=(
                overtime_amount + nsd_amount + holiday_pay + regular_holiday_pay +
                incentives + tips_others + lodging_allowance + leave_addition
            ).quantize(ROUND),
            total_deductions=total_deductions,
            net=net,
            cutoff=cutoff,
            month=month,
            year=year,
        )

        # ── PayoutDetail ───────────────────────────────────────────────────
        detail = PayoutDetail.objects.create(
            payout=payout,
            basic_salary=salary_per_cutoff,
            housing_allowance=Decimal('0.00'),
            transportation_allowance=Decimal('0.00'),
            meal_allowance=Decimal('0.00'),
            medical_allowance=Decimal('0.00'),
            other_allowances=Decimal('0.00'),

            overtime_hours=ot_hours,
            overtime_pay=overtime_amount,
            nsd_hours=nsd_hours,
            night_differential=nsd_amount,

            holiday_hours=holiday_hours,
            holiday_pay=holiday_pay,
            regular_holiday_hours=reg_holiday_hours,
            regular_holiday_pay=regular_holiday_pay,

            incentives=incentives,
            tips_others=tips_others,
            lodging_allowance=lodging_allowance,

            # ✅ Leave — HR-entered values saved correctly
            leave_days_paid=leave_days_paid,
            leave_days_unpaid=leave_days_unpaid,

            working_days=working_days,
            days_present=days_present,
            days_absent=days_absent,

            late_minutes=late_minutes,
            late_hours_equivalent=late_hours_equivalent,
            late_deduction=late_deduction_amount,
            late_occurrences=0,

            absence_deduction=absence_deduction,
            loan_deduction=loan_deduction,
            other_deductions=other_deductions,

            sss_contribution=Decimal('0.00'),
            philhealth_contribution=Decimal('0.00'),
            pagibig_contribution=Decimal('0.00'),

            taxable_income=gross,
            tax_bracket='',
            withholding_tax=tax_amount,

            note=note,
        )

        # ── De Minimis entries ─────────────────────────────────────────────
        from .payroll_settings_models import DeMinimisEntry, DeMinimisType, DeductionType, DeductionEntry

        de_minimis_types = DeMinimisType.objects.filter(is_active=True)
        total_de_minimis = Decimal('0.00')
        for dm_type in de_minimis_types:
            amount = safe_decimal(request.POST.get(f'demiminis_{dm_type.id}'), '0')
            if amount > 0:
                DeMinimisEntry.objects.create(payout=payout, de_minimis_type=dm_type, amount=amount)
                total_de_minimis += amount

        # ── Dynamic Deduction entries ──────────────────────────────────────
        deduction_types          = DeductionType.objects.filter(is_active=True)
        total_dynamic_deductions = Decimal('0.00')
        total_govt_deductions    = Decimal('0.00')
        for ded_type in deduction_types:
            amount = safe_decimal(request.POST.get(f'deduction_{ded_type.id}'), '0')
            if amount > 0:
                DeductionEntry.objects.create(payout=payout, deduction_type=ded_type, amount=amount)
                total_dynamic_deductions += amount
                if ded_type.is_government:
                    total_govt_deductions += amount

        # Auto-assign SSS / PhilHealth / Pag-IBIG
        for ded_type in deduction_types:
            entry = DeductionEntry.objects.filter(payout=payout, deduction_type=ded_type).first()
            if entry and ded_type.is_government:
                if ded_type.code == 'SSS':
                    detail.sss_contribution = entry.amount
                elif ded_type.code == 'PHILHEALTH':
                    detail.philhealth_contribution = entry.amount
                elif ded_type.code == 'PAGIBIG':
                    detail.pagibig_contribution = entry.amount

        detail.total_de_minimis           = total_de_minimis
        detail.total_dynamic_deductions   = total_dynamic_deductions
        detail.total_government_deductions = total_govt_deductions + tax_amount
        detail.save()

        # Update payout net to include de minimis
        # Note: total_deductions already includes dynamic deductions from submitted form
        # (JavaScript includes dynDed in totalDeductions)
        payout.total_deductions = total_deductions.quantize(ROUND)
        payout.net              = (gross + total_de_minimis - payout.total_deductions).quantize(ROUND)
        payout.save()
        
        # Mark the payroll record as finalized
        payroll_record.finalized = True
        # Get the current user from session-based auth
        current_user = get_current_user(request)
        if current_user:
            payroll_record.finalized_by = current_user
        payroll_record.finalized_at = timezone.now()
        payroll_record.save()
        
        messages.success(request, f'Payroll finalized for {employee.first_name} {employee.last_name}')
        return redirect('human_resource:payroll_history_list')

    except Exception as e:
        import traceback
        messages.error(request, f'Error processing payroll: {str(e)}')
        print(traceback.format_exc())
        return redirect('human_resource:individual_payroll')


# ════════════════════════════════════════════════════════════
# API: Employee Info
# ════════════════════════════════════════════════════════════
@login_required
def api_employee_info(request, employee_id):
    from django.http import JsonResponse
    try:
        employee    = Staff.objects.get(pk=employee_id)
        bank_account = BankAccount.objects.filter(employee=employee, is_primary=True).select_related('bank').first()
        bank_info   = None
        if bank_account and bank_account.bank:
            bank_info = {'name': bank_account.bank.name, 'account_number': bank_account.account_number}
        return JsonResponse({'id': employee.id, 'name': f"{employee.first_name} {employee.last_name}", 'bank': bank_info})
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)


# API: Get Attendance Data (for AJAX)
# ════════════════════════════════════════════════════════════
@login_required
def api_attendance_data(request):
    from django.http import JsonResponse
    from .models import Attendance, LeaveCredit
    
    employee_id = request.GET.get('employee_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if not employee_id or not start_date_str or not end_date_str:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    try:
        employee = Staff.objects.get(pk=employee_id)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get attendance records for the date range
        attendance_records = Attendance.objects.filter(
            employee=employee, 
            date__range=(start_date, end_date)
        )
        
        # Calculate statistics
        present_count = attendance_records.filter(status='present').count()
        absent_count = attendance_records.filter(status='absent').count()
        late_count = attendance_records.filter(status='late').count()
        half_day_count = 0
        try:
            half_day_count = attendance_records.filter(status='half_day').count()
        except:
            pass
        
        # Calculate total late minutes
        total_late_minutes = sum(
            (record.late_minutes or 0) for record in attendance_records
        )
        
        # Convert late minutes to hours and minutes
        late_hours = total_late_minutes // 60
        late_mins = total_late_minutes % 60
        
        # Get leave credits
        current_year = date.today().year
        vl_credit = LeaveCredit.objects.filter(employee=employee, leave_type='vl', year=current_year).first()
        sl_credit = LeaveCredit.objects.filter(employee=employee, leave_type='sl', year=current_year).first()
        
        return JsonResponse({
            'employee': {
                'id': employee.id,
                'name': f"{employee.first_name} {employee.last_name}",
                'employee_number': employee.employee_number,
                'department': employee.departmentlink.department_name if employee.departmentlink else '-',
                'position': employee.positionlink.position_name if employee.positionlink else '-',
            },
            'date_range': {
                'start': start_date.strftime('%b %d, %Y'),
                'end': end_date.strftime('%b %d, %Y'),
            },
            'attendance': {
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'half_day': half_day_count,
                'total_late_minutes': total_late_minutes,
                'late_hours': late_hours,
                'late_minutes': late_mins,
            },
            'leave_credits': {
                'vacation': {
                    'remaining': float(vl_credit.remaining) if vl_credit else 0,
                    'total': float(vl_credit.total) if vl_credit else 0,
                },
                'sick': {
                    'remaining': float(sl_credit.remaining) if sl_credit else 0,
                    'total': float(sl_credit.total) if sl_credit else 0,
                },
            }
        })
    except Staff.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ════════════════════════════════════════════════════════════
# HR Self-Service
# ════════════════════════════════════════════════════════════
@login_required
def hr_self_service(request):
    return render(request, 'hr/default/payroll/self_service.html', {})


# ════════════════════════════════════════════════════════════
# Payout Edit
# ════════════════════════════════════════════════════════════
@login_required
def payout_edit(request, pk):
    from .payroll_models import PayoutDetail

    payout = get_object_or_404(Payout, pk=pk)

    if payout.payroll_record.finalized:
        messages.warning(request, 'Cannot edit a finalized payout.')
        return redirect('human_resource:payout_detail', pk=payout.id)

    detail, _ = PayoutDetail.objects.get_or_create(payout=payout, defaults={'basic_salary': payout.gross})

    if request.method == 'POST':
        payout.gross            = safe_decimal(request.POST.get('gross'),            '0')
        payout.total_deductions = safe_decimal(request.POST.get('total_deductions'), '0')
        payout.net              = safe_decimal(request.POST.get('net'),              '0')
        payout.save()

        detail.basic_salary            = safe_decimal(request.POST.get('basic_salary'),            '0')
        detail.overtime_pay            = safe_decimal(request.POST.get('overtime_pay'),            '0')
        detail.overtime_hours          = safe_decimal(request.POST.get('overtime_hours'),          '0')
        detail.night_differential      = safe_decimal(request.POST.get('night_differential'),      '0')
        detail.nsd_hours               = safe_decimal(request.POST.get('nsd_hours'),               '0')
        detail.holiday_pay             = safe_decimal(request.POST.get('holiday_pay'),             '0')
        detail.holiday_hours           = safe_decimal(request.POST.get('holiday_hours'),           '0')
        detail.regular_holiday_pay     = safe_decimal(request.POST.get('regular_holiday_pay'),     '0')
        detail.regular_holiday_hours   = safe_decimal(request.POST.get('regular_holiday_hours'),   '0')
        detail.incentives              = safe_decimal(request.POST.get('incentives'),              '0')
        detail.tips_others             = safe_decimal(request.POST.get('tips_others'),             '0')
        detail.lodging_allowance       = safe_decimal(request.POST.get('lodging_allowance'),       '0')
        detail.absence_deduction       = safe_decimal(request.POST.get('absence_deduction'),       '0')
        detail.late_deduction          = safe_decimal(request.POST.get('late_deduction'),          '0')
        detail.loan_deduction          = safe_decimal(request.POST.get('loan_deduction'),          '0')
        detail.other_deductions        = safe_decimal(request.POST.get('other_deductions'),        '0')
        detail.sss_contribution        = safe_decimal(request.POST.get('sss_contribution'),        '0')
        detail.philhealth_contribution = safe_decimal(request.POST.get('philhealth_contribution'), '0')
        detail.pagibig_contribution    = safe_decimal(request.POST.get('pagibig_contribution'),    '0')
        detail.withholding_tax         = safe_decimal(request.POST.get('withholding_tax'),         '0')
        # Fix: Use safe_decimal then convert to int to handle decimal values like '0.00'
        detail.working_days            = int(float(safe_decimal(request.POST.get('working_days', '0'))))
        detail.days_present            = int(float(safe_decimal(request.POST.get('days_present', '0'))))
        detail.days_absent             = int(float(safe_decimal(request.POST.get('days_absent',  '0'))))
        detail.late_minutes            = int(float(safe_decimal(request.POST.get('late_minutes', '0'))))
        # ✅ Leave days editable
        detail.leave_days_paid         = safe_decimal(request.POST.get('leave_days_paid',   '0'))
        detail.leave_days_unpaid       = safe_decimal(request.POST.get('leave_days_unpaid', '0'))
        detail.note                    = request.POST.get('note', '')
        detail.save()

        messages.success(request, 'Payout updated successfully.')
        return redirect('human_resource:payout_detail', pk=payout.id)

    return render(request, 'hr/default/payout/payout_edit.html', {'payout': payout, 'details': detail})


# ════════════════════════════════════════════════════════════
# Payout Delete / Unfinalize
# ════════════════════════════════════════════════════════════
@login_required
def payout_delete(request, pk):
    payout = get_object_or_404(Payout, pk=pk)
    
    # Show confirmation page for GET request
    if request.method == 'GET':
        return render(request, 'hr/default/payout/payout_delete.html', {'payout': payout})
    
    # Process deletion for POST request
    if request.method == 'POST':
        payout.delete()
        messages.success(request, 'Payout deleted')
        return redirect('human_resource:payout_list')
    
    return redirect('human_resource:payout_list')


@login_required
def payout_unfinalize(request, pk):
    payout = get_object_or_404(Payout, pk=pk)
    
    # Show confirmation page for GET request
    if request.method == 'GET':
        return render(request, 'hr/default/payout/payout_unfinalize_confirm.html', {'payout': payout})
    
    # Process unfinalization for POST request
    if request.method == 'POST':
        payout.payroll_record.finalized = False
        payout.payroll_record.save()
        messages.success(request, 'Payout unfinalized')
        return redirect('human_resource:payout_detail', pk=payout.pk)
    
    return redirect('human_resource:payout_detail', pk=payout.pk)


# ════════════════════════════════════════════════════════════
# Loan helpers
# ════════════════════════════════════════════════════════════
@login_required
def loan_update_status(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    messages.success(request, 'Loan status updated')
    return redirect('human_resource:loan_detail', pk=loan.pk)


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    
    # Get PayoutDetail records for this employee with loan deductions
    from .payroll_models import PayoutDetail
    payout_details = PayoutDetail.objects.filter(
        payout__employee=loan.employee,
        loan_deduction__gt=0
    ).select_related('payout').order_by('-payout__year', '-payout__month', '-payout__cutoff')[:24]  # Last 24 records
    
    # Format payout details for template
    payroll_data = []
    for p in payout_details:
        cutoff_val = p.payout.cutoff if p.payout else '1'
        year_val = p.payout.year if p.payout else 0
        month_val = p.payout.month if p.payout else 0
        payroll_data.append({
            'year': year_val,
            'month': month_val,
            'cutoff': cutoff_val,
            'amount': p.loan_deduction,
            'date': f"{year_val}-{month_val:02d}-{cutoff_val}"
        })
    
    return render(request, 'hr/default/payroll_loans/loan_detail.html', {
        'loan': loan,
        'payroll_records': payroll_data
    })


# ════════════════════════════════════════════════════════════
# Bank Type CRUD
# ════════════════════════════════════════════════════════════
@login_required
def banktype_list(request):
    from .models import BankType
    return render(request, 'hr/default/banktype/banktype_list.html', {'bank_types': BankType.objects.all()})


@login_required
def banktype_form(request, pk=None):
    from .models import BankType
    bank_type = BankType.objects.get(pk=pk) if pk else None

    if request.method == 'POST':
        name      = request.POST.get('name')
        code      = request.POST.get('code')
        is_active = 'is_active' in request.POST
        if bank_type:
            bank_type.name = name; bank_type.code = code; bank_type.is_active = is_active; bank_type.save()
            messages.success(request, f'Bank type "{name}" updated successfully.')
        else:
            BankType.objects.create(name=name, code=code, is_active=is_active)
            messages.success(request, 'Bank type created successfully.')
        return redirect('human_resource:banktype_list')

    return render(request, 'hr/default/banktype/banktype_form.html', {'bank_type': bank_type})


@login_required
def banktype_delete(request, pk):
    from .models import BankType
    get_object_or_404(BankType, pk=pk).delete()
    messages.success(request, 'Bank type deleted')
    return redirect('human_resource:banktype_list')


# ════════════════════════════════════════════════════════════
# Payroll History
# ════════════════════════════════════════════════════════════
@login_required
def payroll_history_list(request):
    from .payroll_models import PayrollRecord
    from django.db.models import Sum, Count
    
    # Get filter parameters
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')
    
    # Get all finalized payroll records with aggregated data
    payroll_records = PayrollRecord.objects.annotate(
        payout_count=Count('payouts__id'),
        total_gross=Sum('payouts__gross'),
        total_deductions=Sum('payouts__total_deductions'),
        total_net=Sum('payouts__net')
    ).filter(finalized=True)
    
    # Apply filters
    if selected_year:
        payroll_records = payroll_records.filter(year=int(selected_year))
    if selected_month:
        payroll_records = payroll_records.filter(month=int(selected_month))
    
    payroll_records = payroll_records.order_by('-year', '-month', '-cutoff')
    
    # Group by month/year for combined view
    from collections import defaultdict
    grouped_data = defaultdict(lambda: {'cutoffs': [], 'total_gross': 0, 'total_deductions': 0, 'total_net': 0, 'total_employees': 0})
    
    for pr in payroll_records:
        key = (pr.year, pr.month)
        grouped_data[key]['cutoffs'].append({
            'id': pr.id,
            'cutoff': pr.cutoff,
            'payout_count': pr.payout_count or 0,
            'total_gross': pr.total_gross or 0,
            'total_deductions': pr.total_deductions or 0,
            'total_net': pr.total_net or 0,
            'created_at': pr.created_at,
        })
        grouped_data[key]['total_gross'] += pr.total_gross or 0
        grouped_data[key]['total_deductions'] += pr.total_deductions or 0
        grouped_data[key]['total_net'] += pr.total_net or 0
        grouped_data[key]['total_employees'] += pr.payout_count or 0
    
    # Convert to list sorted by year/month
    history_list = []
    for (year, month), data in sorted(grouped_data.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True):
        history_list.append({
            'year': year,
            'month': month,
            'cutoffs': data['cutoffs'],
            'total_gross': data['total_gross'],
            'total_deductions': data['total_deductions'],
            'total_net': data['total_net'],
            'total_employees': data['total_employees'],
        })
    
    # Calculate overall totals
    total_gross = sum([h['total_gross'] for h in history_list], 0)
    total_net = sum([h['total_net'] for h in history_list], 0)
    
    # Get years and months for filter
    current_year = date.today().year
    years = range(current_year - 3, current_year + 3)
    months = [
        (1,'January'),(2,'February'),(3,'March'),(4,'April'),
        (5,'May'),(6,'June'),(7,'July'),(8,'August'),
        (9,'September'),(10,'October'),(11,'November'),(12,'December'),
    ]
    
    return render(request, 'hr/default/payroll/history_list.html', {
        'history': history_list,
        'total_gross': total_gross,
        'total_net': total_net,
        'years': years,
        'months': months,
        'selected_year': int(selected_year) if selected_year else None,
        'selected_month': int(selected_month) if selected_month else None,
    })


@login_required
def payroll_history_detail(request, pk):
    from .payroll_models import PayrollRecord, Payout
    from .payroll_settings_models import DeMinimisEntry, DeductionEntry
    
    payroll_record = get_object_or_404(PayrollRecord, pk=pk, finalized=True)
    payouts = payroll_record.payouts.select_related('employee', 'bank_account', 'details')
    
    # Get summary data
    total_gross = sum([p.gross for p in payouts], Decimal('0.00'))
    total_deductions = sum([p.total_deductions for p in payouts], Decimal('0.00'))
    total_net = sum([p.net for p in payouts], Decimal('0.00'))
    
    # Get years and months for filter
    current_year = date.today().year
    years = range(current_year - 3, current_year + 3)
    months = [
        (1,'January'),(2,'February'),(3,'March'),(4,'April'),
        (5,'May'),(6,'July'),(7,'July'),(8,'August'),
        (9,'September'),(10,'October'),(11,'November'),(12,'December'),
    ]
    
    return render(request, 'hr/default/payroll_settings/history_detail.html', {
        'payroll_record': payroll_record,
        'payouts': payouts,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net': total_net,
        'years': years,
        'months': months,
    })


# ════════════════════════════════════════════════════════════
# Utility: Count Working Days
# ════════════════════════════════════════════════════════════
def count_working_days(start_date, end_date):
    """Count Mon–Fri working days between start_date and end_date (inclusive). Minimum 1."""
    if start_date > end_date:
        return 1
    count   = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return max(count, 1)


# ════════════════════════════════════════════════════════════
# Utility: Current Payroll Period
# ════════════════════════════════════════════════════════════
def get_current_payroll_period():
    """Return (month, year, cutoff, start_date, end_date, working_days) for today."""
    today = date.today()
    month = today.month
    year  = today.year

    if today.day <= 15:
        cutoff     = '1'
        start_date = date(year, month, 1)
        end_date   = date(year, month, 15)
    else:
        cutoff    = '2'
        last_day  = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 16)
        end_date   = date(year, month, last_day)

    working_days = count_working_days(start_date, end_date)
    return month, year, cutoff, start_date, end_date, working_days


# ════════════════════════════════════════════════════════════
# Utility: Calculate Cutoff Dates
# ════════════════════════════════════════════════════════════
def calculate_cutoff_dates(month, year, cutoff):
    """Return (start_date, end_date, working_days) for any month/year/cutoff."""
    if cutoff == '1':
        start_date = date(year, month, 1)
        end_date   = date(year, month, 15)
    else:
        last_day   = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 16)
        end_date   = date(year, month, last_day)

    working_days = count_working_days(start_date, end_date)
    return start_date, end_date, working_days
