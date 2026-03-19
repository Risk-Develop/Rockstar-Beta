# Rockstar HR System - User Guide

---

## LOGIN SYSTEM

### How to Login

1. Open the system in your browser
2. Enter your username in the first box
3. Enter your password in the second box
4. Click the Login button
5. If you have multiple departments, select your department and click Continue

### Forgot Password

If you forget your password:
1. Click "Forgot Password" on the login page
2. Enter your email address
3. Check your email for the reset link
4. Click the link and create a new password

Or contact your administrator to reset it for you.

---

## REGISTRATION / NEW ACCOUNT

### How to Get a New Account

**Option 1 - Self-Register:**
1. Go to login page
2. Click "Sign Up" 
3. Fill in your Employee Number, Email, Password
4. Submit and wait for approval

**Option 2 - Ask Admin:**
1. Contact your HR or IT admin
2. They will create your account
3. You will receive login details via email

---

## DASHBOARDS

### What is HR Dashboard?

This is where HR staff manage employees, attendance, payroll, and leave. You can find it at `/hr_dashboard/`

**Main things you can do here:**
- View and manage all employees
- Process payroll (calculate salaries)
- Check attendance records
- Approve or reject leave requests
- Manage loans and bank accounts

### What is Master Dashboard?

This is for higher-level administrators who oversee everything across all departments. You can find it at `/master_dashboard/`

---

## EMPLOYEE MANAGEMENT

### How to View Employee List

1. Go to HR Dashboard
2. Click "Employees" in the menu
3. You will see a list of all employees with their names, departments, and positions

### How to Add New Employee

1. Go to HR Dashboard
2. Click "User Management"
3. Click "Add User" or "Add Employee"
4. Fill in the details:
   - Employee Number (like EMP-001-2024)
   - First Name and Last Name
   - Email Address
   - Department
   - Position
   - Create username and password
5. Assign a role (Admin, HR, or Employee)
6. Click Save

---

## ATTENDANCE

### How to View Attendance Records

1. Go to HR Dashboard
2. Click "Attendance" 
3. Click "Attendance View"
4. Use filters to find what you need:
   - Select date range (From - To)
   - Select department
   - Select status (Present, Absent, Late, etc.)
5. Click Search or Apply

**Attendance Statuses:**
- **Present** = Employee came to work on time
- **Absent** = Employee did not come to work
- **Late** = Employee came after scheduled time
- **On Leave** = Employee has approved leave
- **Failed to Clock Out** = Employee forgot to clock out

### How to Clock In / Clock Out

1. Go to HR Dashboard
2. Click "Attendance"
3. Click "Clock"
4. Click "Clock In" when you arrive
5. Click "Clock Out" when you leave

### How to Mark Employee as Absent

1. Go to HR Dashboard
2. Click "Attendance"
3. Click "Mark Absent"
4. Select the employee
5. Select the date
6. Add notes if needed
7. Click "Mark Absent"

---

## LEAVE MANAGEMENT

### How to View Leave Requests

1. Go to HR Dashboard
2. Click "Leave Requests"

**You will see:**
- Pending requests (yellow) - waiting for approval
- Approved requests (green) - already approved
- Disapproved requests (red) - rejected

### How to Approve or Reject Leave

1. Go to HR Dashboard
2. Click "Leave Requests"
3. Find the pending request
4. Click "Approve" (checkmark) or "Disapprove" (X)
5. The status will change

### How to View Leave Credits

1. Go to HR Dashboard
2. Click "Leave Credits"
3. See how many leave days each employee has remaining

**Leave Types:**
- **VL** = Vacation Leave
- **SL** = Sick Leave

**Alerts:**
- Yellow = Less than 2 days remaining
- Red = No days remaining

---

## PAYROLL

### What is Payroll?

Payroll is the process of calculating employee salaries for a specific period (cutoff). 

**The system calculates:**
- **Gross Pay** = Total earnings before deductions
- **Deductions** = Tax, SSS, PhilHealth, Pag-IBIG, late fees, absent fees
- **Net Pay** = What the employee takes home (Gross - Deductions)

### How to Process Individual Payroll (One Employee)

1. Go to HR Dashboard
2. Click "Payroll"
3. Click "Individual Payroll"
4. Select the employee
5. Select the month and year
6. Select cutoff (1st = days 1-15, 2nd = days 16-end)
7. The system will show attendance summary
8. You can adjust earnings if needed
9. Click "Preview" to see the calculation
10. Click "Finalize" to lock the record

### How to Process Batch Payroll (Many Employees)

1. Go to HR Dashboard
2. Click "Payroll"
3. Click "Batch Payroll"
4. Select department (or leave blank for all)
5. Select cutoff period
6. Click "Preview"
7. Review all employees
8. Make adjustments if needed
9. Click "Finalize All"

### How to View Payroll History

1. Go to HR Dashboard
2. Click "Payroll Settings"
3. Click "Payroll History"
4. Select year and month
5. See the summary of past payrolls

### How to Release / Pay Employees

1. Go to HR Dashboard
2. Click "Payouts"
3. Find the finalized payroll
4. Click "Release" to mark as paid

### How to Generate Payslip (PDF)

1. Go to HR Dashboard
2. Click "Payouts"
3. Click on a specific employee payout
4. Click "Download PDF"

---

## LOANS

### How to Add a New Loan

1. Go to HR Dashboard
2. Click "Loans"
3. Click "Add Loan"
4. Select the employee
5. Enter the loan amount (Principal)
6. Enter interest rate (if any)
7. Enter term in months (how many months to pay)
8. Enter start date
9. Click Save

**Loan Status:**
- **Pending** (Yellow) = Waiting for approval
- **Approved** (Green) = Loan granted
- **Disapproved** (Red) = Rejected
- **Closed** (Gray) = Fully paid

### How to Approve a Loan

1. Go to HR Dashboard
2. Click "Loans"
3. Find the pending loan
4. Change status to "Approved"
5. The system will automatically calculate monthly payments

---

## BANK ACCOUNTS

### How to Add Employee Bank Account

1. Go to HR Dashboard
2. Click "Bank Accounts"
3. Click "Add Bank Account"
4. Select the employee
5. Select the bank
6. Enter account number
7. Select account type (Savings or Checking)
8. Click Save

---

## USER MANAGEMENT

### How to Manage Users

1. Go to HR Dashboard
2. Click "User Management"

**You can:**
- Add new user
- Edit user details
- Delete user
- Change user role

### User Roles

| Role | What they can do |
|------|-----------------|
| **Admin** | Everything - full system access |
| **HR** | HR functions - payroll, attendance, leave, employees |
| **Employee** | Self-service only - own profile, clock in/out, request leave |

---

## SETTINGS

### Where to Configure Payroll Settings

1. Go to HR Dashboard
2. Click "Payroll Settings"

**You can configure:**
- Salary settings for employees
- Deduction types (SSS, PhilHealth, Pag-IBIG, etc.)
- De minimis benefits
- Tier thresholds

---

## REPORTS

### How to Generate Reports

**For Payroll Reports:**
1. Go to Payroll History
2. Select month/year
3. See totals for gross, deductions, net

**For Attendance Reports:**
1. Go to Attendance View
2. Select date range
3. See present, absent, late counts

**For Leave Reports:**
1. Go to Leave Requests
2. Filter by status

### How to Export Data

**To Export to CSV:**
1. Go to any list page (Attendance, Payouts, etc.)
2. Apply your filters
3. Click "Export CSV" button
4. File will download

**To Print:**
1. Go to any list page
2. Click "Print Report"

---

## KEY URLS

| Feature | URL |
|---------|-----|
| Login | /login/ |
| HR Dashboard | /hr_dashboard/ |
| Master Dashboard | /master_dashboard/ |
| Employees | /hr_dashboard/employees/ |
| Attendance | /hr_dashboard/attendance/ |
| Leave Requests | /hr_dashboard/leave-requests/ |
| Individual Payroll | /hr_dashboard/payroll/individual/ |
| Batch Payroll | /hr_dashboard/payroll/batch-preview/ |
| Payouts | /hr_dashboard/payout/ |
| Payroll History | /hr_dashboard/payroll-settings/history/ |
| Loans | /hr_dashboard/loans/ |
| Bank Accounts | /hr_dashboard/bank-accounts/ |
| User Management | /hr_dashboard/user-management/ |

---

*End of Guide*
