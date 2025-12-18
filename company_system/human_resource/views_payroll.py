# human_resource/views_payroll.py
from django.shortcuts import render, redirect, get_object_or_404
from datetime import date
import calendar
from decimal import Decimal


from django.http import HttpResponse
from weasyprint import HTML


from .payroll_models import PayrollRecord, Payout, BankAccount, BankType, Loan
from .payroll_utils import compute_payroll_for_cutoff
from users.models import Staff
from .models import EmployeeShiftRule

# ============================================
# Payroll Preview (before finalizing)
# ============================================
def payroll_preview(request):
    month = int(request.GET.get('month', date.today().month))
    year = int(request.GET.get('year', date.today().year))
    cutoff = request.GET.get('cutoff', '1')

    if cutoff == '1':
        start = date(year, month, 1)
        end = date(year, month, 15)
    else:
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 16)
        end = date(year, month, last_day)

    # loop active employees
    ##employees = Staff.objects.filter(is_active=True)
    ###employees = Staff.objects.filter(is_active=True)
    employees = Staff.objects.all()
    preview_list = []

    for emp in employees:
        # optional: fetch shift_rule per employee
        try:
            shift_rule = EmployeeShiftRule.objects.get(rank=emp.rank, shift=emp.shift)
        except EmployeeShiftRule.DoesNotExist:
            shift_rule = None

        pay = compute_payroll_for_cutoff(emp, start, end, cutoff, shift_rule)
        preview_list.append({'employee': emp, 'pay': pay})

    context = {
        'preview': preview_list,
        'month': month,
        'year': year,
        'cutoff': cutoff,
    }
    return render(request, 'hr/default/payroll/preview.html', context)


# ============================================
# Payroll Finalize (creates PayrollRecord + Payouts)
# ============================================
def payroll_finalize(request):
    if request.method == 'POST':
        month = int(request.POST['month'])
        year = int(request.POST['year'])
        cutoff = request.POST['cutoff']

        if cutoff == '1':
            start = date(year, month, 1)
            end = date(year, month, 15)
        else:
            last_day = calendar.monthrange(year, month)[1]
            start = date(year, month, 16)
            end = date(year, month, last_day)

        # create PayrollRecord
        pr = PayrollRecord.objects.create(month=month, year=year, cutoff=cutoff, created_by=request.user)

        ###employees = Staff.objects.filter(is_active=True)
        employees = Staff.objects.all()
        for emp in employees:
            # optional: shift_rule
            try:
                shift_rule = EmployeeShiftRule.objects.get(rank=emp.rank, shift=emp.shift)
            except EmployeeShiftRule.DoesNotExist:
                shift_rule = None

            pay = compute_payroll_for_cutoff(emp, start, end, cutoff, shift_rule)

            # primary bank account
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
                year=year
            )

        pr.finalized = True
        pr.save()
        return redirect('human_resource:payroll_record_detail', pk=pr.pk)

    return render(request, 'hr/default/payroll/finalize_form.html', {'now': date.today()})


# ============================================
# Payroll Record Detail (view finalized payouts)
# ============================================
def payroll_record_detail(request, pk):
    payroll = get_object_or_404(PayrollRecord, pk=pk)
    payouts = payroll.payouts.select_related('employee', 'bank_account', 'bank_account__bank')

    # summarize totals
    total_gross = sum([p.gross for p in payouts], Decimal('0.00'))
    total_additions = sum([p.total_additions for p in payouts], Decimal('0.00'))
    total_deductions = sum([p.total_deductions for p in payouts], Decimal('0.00'))
    total_net = sum([p.net for p in payouts], Decimal('0.00'))

    context = {
        'payroll': payroll,
        'payouts': payouts,
        'total_gross': total_gross,
        'total_additions': total_additions,
        'total_deductions': total_deductions,
        'total_net': total_net,
    }
    return render(request, 'hr/default/payroll/record_detail.html', context)


# ============================================
# Bank Accounts
# ============================================
def bankaccount_list(request):
    accounts = BankAccount.objects.select_related('employee', 'bank')
    return render(request, 'hr/default/payroll_bank/bankaccount_list.html', {'accounts': accounts})

def bankaccount_form(request, pk=None):
    if pk:
        account = get_object_or_404(BankAccount, pk=pk)
    else:
        account = None

    if request.method == 'POST':
        employee_id = request.POST['employee']
        bank_id = request.POST['bank']
        account_number = request.POST['account_number']
        is_primary = 'is_primary' in request.POST

        emp = get_object_or_404(Staff, pk=employee_id)
        bank = get_object_or_404(BankType, pk=bank_id)

        if account:
            account.employee = emp
            account.bank = bank
            account.account_number = account_number
            account.is_primary = is_primary
            account.save()
        else:
            BankAccount.objects.create(
                employee=emp,
                bank=bank,
                account_number=account_number,
                is_primary=is_primary
            )
        return redirect('human_resource:bankaccount_list')

    employees = Staff.objects.filter(is_active=True)
    banks = BankType.objects.all()
    return render(request, 'hr/default/payroll_bank/bankaccount_form.html', {
        'account': account,
        'employees': employees,
        'banks': banks
    })


# ============================================
# Loans
# ============================================
def loan_list(request):
    loans = Loan.objects.select_related('employee')
    return render(request, 'hr/default/payroll_loans/loan_list.html', {'loans': loans})

def loan_form(request, pk=None):
    if pk:
        loan = get_object_or_404(Loan, pk=pk)
    else:
        loan = None

    if request.method == 'POST':
        employee_id = request.POST['employee']
        principal = request.POST['principal']
        interest_rate = request.POST['interest_rate']
        term_months = request.POST['term_months']
        start_date = request.POST['start_date']
        status = request.POST['status']

        emp = get_object_or_404(Staff, pk=employee_id)

        if loan:
            loan.employee = emp
            loan.principal = principal
            loan.interest_rate = interest_rate
            loan.term_months = term_months
            loan.start_date = start_date
            loan.status = status
            loan.save()
        else:
            Loan.objects.create(
                employee=emp,
                principal=principal,
                interest_rate=interest_rate,
                term_months=term_months,
                start_date=start_date,
                status=status
            )
        return redirect('human_resource:loan_list')

    employees = Staff.objects.filter(is_active=True)
    return render(request, 'hr/default/payroll_loans/loan_form.html', {
        'loan': loan,
        'employees': employees
    })

def payout_list(request):
    payouts = Payout.objects.select_related('employee', 'bank_account', 'bank_account__bank')
    return render(request, 'hr/default/payout/payout_list.html', {'payouts': payouts})

def payout_detail(request, pk):
    payout = get_object_or_404(Payout, pk=pk)
    return render(request, 'hr/default/payout/payout_detail.html', {'payout': payout})


# ============================================
# Payout DETAIL PDF
# ============================================

def payout_pdf(request, payout_id):
    payout = get_object_or_404(Payout, id=payout_id)
    html_string = render(request, 'hr/default/payroll/payout/payout_details.html', {'payout': payout}).content.decode('utf-8')
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=payslip_{payout.employee.get_full_name}_{payout.month}_{payout.year}.pdf'

    HTML(string=html_string).write_pdf(response)
    return response