# SYSTEM DOCUMENTATION REPORT
# Rockstar Beta Company System

---

## 1. INTRODUCTION

### 1.1 System Overview

The **Rockstar Beta Company System** is a comprehensive web-based Human Resource Management System (HRMS) designed to automate and manage various HR processes within an organization. This system serves as a centralized platform for managing employee information, tracking attendance, processing leave requests, calculating and distributing payroll, managing employee loans, and handling bank account information for salary disbursement.

The system is built using the **Django framework**, which is a high-level Python web framework that encourages rapid development and clean, pragmatic design. Django provides a robust foundation for handling database operations, user authentication, and web interface rendering. The system uses **PostgreSQL** as its database backend, which is a powerful, open-source object-relational database system known for its reliability, feature robustness, and performance.

### 1.2 Purpose

The primary purpose of this document is to provide a complete technical and functional documentation of the Rockstar Beta Company System. This documentation serves multiple stakeholders including:

- **System Administrators** - For understanding system architecture and configuration
- **HR Personnel** - For understanding functional capabilities and workflows
- **IT Support** - For troubleshooting and maintenance
- **Management** - For understanding system capabilities and processes
- **Developers** - For future enhancements and modifications

This document describes the complete system architecture, all database models with their field definitions, the various functional modules, user interface structures, and operational procedures.

### 1.3 Technology Stack

The Rockstar Beta Company System is built using modern, industry-standard technologies that ensure reliability, scalability, and maintainability:

| Component | Technology | Description |
|-----------|------------|-------------|
| Backend Framework | Django | Python-based web framework for server-side logic |
| Database | PostgreSQL | Advanced open-source relational database |
| Frontend | HTML, CSS, JavaScript | Standard web technologies for user interface |
| Styling | Tailwind CSS | Utility-first CSS framework for responsive design |
| Deployment Platform | Render/Heroku | Cloud platform for hosting web applications |

**Why Django?**
Django was chosen as the backend framework because it provides:
- Built-in authentication system
- Admin interface for data management
- Object-relational mapping (ORM) for database operations
- Security features against common web vulnerabilities
- Scalability for growing user base

**Why PostgreSQL?**
PostgreSQL was selected as the database because it offers:
- ACID compliance for data integrity
- Support for complex queries
- Foreign key constraints for data relationships
- Extensibility for custom functions
- Excellent performance with large datasets

---

## 2. SYSTEM ARCHITECTURE

### 2.1 Application Structure

The Rockstar Beta Company System is organized as a multi-application Django project. Each application (module) handles specific functionality and can be developed, tested, and maintained independently. The application structure is as follows:

```
Rockstar Beta System
├── authentication/          # User authentication and authorization module
│   ├── models.py            # UserAccount, LoginHistory, Role models
│   ├── views.py            # Login, logout, registration views
│   ├── forms.py            # Authentication forms
│   ├── urls.py             # URL routing
│   └── templates/           # Login, signup templates
│
├── human_resource/          # Core HR and payroll functionality
│   ├── models.py           # Attendance, LeaveRequest models
│   ├── views.py            # HR operations views
│   ├── forms.py            # HR forms
│   ├── urls.py             # HR URL routing
│   ├── payroll_models.py   # Payout, Loan models
│   ├── payroll_settings_models.py # Salary, deduction settings
│   ├── payroll_computation.py # Salary calculation logic
│   └── templates/           # HR interface templates
│
├── employees/              # Employee management module
│   ├── models.py           # Additional employee models
│   ├── views.py            # Employee views
│   └── templates/           # Employee interface templates
│
├── master_dashboard/       # Master/administrative dashboard
│   ├── models.py           # Dashboard models
│   ├── views.py            # Dashboard views
│   └── templates/           # Dashboard templates
│
├── finance/                # Finance module (placeholder for future use)
│   └── (structure to be defined)
│
├── users/                  # User and Staff core models
│   ├── models.py           # Staff, Department, Position models
│   ├── forms.py            # User forms
│   └── admin.py            # Django admin configuration
│
├── templates/              # Base templates and includes
│   ├── base.html          # Main base template
│   ├── includes/          # Reusable components (navbar, sidebar)
│   └── authentication/    # Auth-related templates
│
└── theme/                  # Styling and theme configuration
    ├── tailwind.config.js # Tailwind CSS configuration
    └── static/            # Static files (CSS, JS, images)
```

### 2.2 Database Models Overview

The system uses a relational database design with multiple interconnected models. Each model represents a specific entity in the HR system, and relationships between models allow for complex data management.

**Main Database Models:**

1. **Staff** - The central employee master data table containing all personnel information
2. **UserAccount** - Stores system login credentials and authentication data
3. **Role** - Defines user roles and their permission levels
4. **Department** - Organizational department definitions
5. **Position** - Job position/title definitions
6. **Attendance** - Daily attendance records for each employee
7. **LeaveRequest** - Leave applications submitted by employees
8. **LeaveCredit** - Leave balance tracking for each employee
9. **EmployeeProfileSettings** - Employee-specific HR settings
10. **Payout** - Salary payment records for each pay period
11. **PayrollRecord** - Batch payroll records for each period
12. **PayoutDetail** - Detailed breakdown of salary calculations
13. **Loan** - Employee loan records with amortization schedules
14. **BankAccount** - Employee bank account information
15. **BankType** - Approved bank list for salary disbursement
16. **EmployeeSalarySetting** - Individual salary configurations
17. **TierThresholdSetting** - Performance tier definitions
18. **DeductionType** - Types of payroll deductions
19. **DeMinimisType** - Tax-exempt benefit types
20. **GovernmentContributionRate** - SSS, PhilHealth, Pag-IBIG rates
21. **LoginHistory** - Security audit trail for logins
22. **StaffHistory** - Audit trail for employee record changes

---

## 3. CORE MODULES

### 3.1 Authentication Module

The Authentication Module is responsible for managing user access to the system. This module handles user registration, login, logout, password management, and access control. It ensures that only authorized users can access the system and tracks user activities for security purposes.

#### 3.1.1 UserAccount Model

The UserAccount model is the core of the authentication system. It stores the login credentials for each user and links the credentials to the employee record. Each employee who needs system access must have a corresponding UserAccount record.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | This is a reference to the Staff model. It creates a one-to-one relationship with the employee, meaning each user account is linked to exactly one employee record. This allows the system to associate system access with personnel data. |
| password | CharField | This field stores the user's password in a hashed format. Hashing is a security practice where the actual password is converted into a fixed-length string of characters using a one-way mathematical function. Django's built-in password hasher is used, making it virtually impossible to reverse-engineer the original password from the stored hash. |
| is_active | Boolean | This boolean field indicates whether the user account is active or inactive. When set to False, the user cannot log into the system. This is useful for temporarily suspending access without deleting the account, such as during an employee's leave of absence. |
| created_at | DateTime | This automatically populated timestamp records when the user account was created. The value is set automatically when the record is first saved using Django's auto_now_add feature. |
| last_login | DateTime | This field tracks the most recent successful login timestamp. It is updated automatically each time the user successfully logs into the system. HR administrators can use this information to identify inactive accounts or monitor user activity. |

**Key Features Explained:**

*Password Hashing:* 
The system uses Django's make_password() function to hash passwords before storing them. When a user attempts to login, the system uses check_password() to compare the entered password with the stored hash. This ensures that even if the database is compromised, actual passwords cannot be retrieved.

*Account Activation:*
The is_active field allows administrators to deactivate user accounts without deleting them. This preserves all historical data associated with the account while preventing the user from accessing the system.

#### 3.1.2 LoginHistory Model

The LoginHistory model provides a security audit trail by recording every attempt to log into the system. This is crucial for security monitoring, troubleshooting login issues, and detecting unauthorized access attempts.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | This optional reference links the login attempt to a Staff record, if the employee was successfully identified. For failed attempts where the username doesn't exist, this may be null. |
| employee_number | CharField | This stores the username (employee number) that was entered during the login attempt. This is stored separately from the employee foreign key so that even failed attempts can be recorded with the attempted username. |
| login_time | DateTime | This timestamp records exactly when the login attempt occurred. The automatic_now_add=True ensures accuracy without requiring manual input. |
| ip_address | GenericIPAddressField | This records the IP address of the computer attempting to login. This is important for security audits and can help identify suspicious login patterns, such as attempts from different geographic locations in a short time. |
| user_agent | CharField | This stores the web browser and operating system information sent by the client's browser. This data helps administrators understand what devices and browsers are being used to access the system. |
| status | CharField | This field indicates whether the login attempt was successful or failed. The values are 'success' or 'failed'. This is the primary field for security monitoring. |
| failure_reason | CharField | When a login fails, this field stores the reason, such as "invalid password" or "account disabled". This helps users understand why they couldn't log in and helps IT troubleshoot issues. |

**Browser Detection Functions:**
The LoginHistory model includes methods to parse the user_agent string and extract:
- Browser name (Chrome, Firefox, Safari, Edge, Opera, Internet Explorer)
- Operating system name

This parsed information makes it easier for administrators to generate reports on browser usage patterns.

#### 3.1.3 Role Model

The Role model defines different levels of access within the system. Roles determine what features and data each user can access and modify.

| Role | Description |
|------|-------------|
| Admin | Users with this role have complete, unrestricted access to all system features. They can manage other user accounts, access all data, modify system settings, and perform any operation. This role should be assigned sparingly due to its extensive privileges. |
| HR | Users with this role have access to all HR-related functions including employee management, attendance tracking, leave management, and payroll processing. They cannot access system configuration or manage other user roles. |
| Employee | This is the most restricted role. Users can only access their own information through the self-service portal. They can clock in/out, view their own attendance records, submit leave requests, and view their own payslips. |

**Role-Based Access Control (RBAC):**
The system implements RBAC by assigning roles to users. When a user attempts to access a particular function, the system checks if the user's role permits that action. This approach provides:
- Clear separation of duties
- Simplified permission management
- Audit trail for accountability
- Easy role modification when job functions change

---

### 3.2 Employee Management Module

The Employee Management Module is the foundation of the entire HR system. It stores and manages all employee-related information, from basic personal details to employment history and government identification numbers. This module serves as the single source of truth for all employee data.

#### 3.2.1 Staff Model

The Staff model is the most important model in the entire system. It contains the complete employee master data and serves as the primary reference for almost every other module in the system. Every employee record in this table represents a person employed by the organization.

**Employment Status Explained:**

The status field indicates the current employment state of each employee:

| Value | Description | Use Case |
|-------|-------------|----------|
| active | The employee is currently employed and actively working | Default for all current employees |
| inactive | The employee is not currently active but employment relationship may resume | Employees on indefinite leave or temporarily laid off |
| on_leave | The employee is on extended leave (maternity, sabbatical, etc.) | Long-term leave tracking |
| terminated | The employment has ended | Former employees, useful for historical records |

**Employment Type Explained:**

The type field categorizes the employment arrangement:

| Value | Description |
|-------|-------------|
| regular | Full-time employee with permanent status |
| probationary | Employee completing probation period |
| contractual | Employee hired under a fixed-term contract |
| consultant | External consultant hired for specific work |
| part_time | Employee working less than full-time hours |
| freelance | Independent worker engaged on project basis |
| defined | Employee with specifically defined employment terms |

**Department Structure:**

The organization is divided into the following departments, each represented by a code:

| Value | Display Name | Function |
|-------|--------------|----------|
| top_management | Top Management | Executive leadership |
| compliance | Compliance | Regulatory adherence |
| sales_and_marketing | Sales and Marketing | Sales and marketing activities |
| sales_operation_processes | Sales Operations Processes | Sales support and operations |
| finance | Finance | Financial management |
| human_resource | Human Resource | HR management |
| marketing | Marketing | Marketing activities |
| sales_production | Sales Production | Product sales |
| client_success_management | Client Success Management | Client relations |
| administrative | Administrative | Administrative support |
| design_and_technical | Design and Technical | Technical and design work |

**Rank/Level Structure:**

The rank field indicates the employee's position level in the organizational hierarchy:

| Value | Description |
|-------|-------------|
| rank_and_file | Regular employees without supervisory responsibilities |
| supervisory | Employees who supervise others but are not managers |
| managerial | Managers with decision-making authority |
| director | Directors leading major departments |
| top-management | Executive-level positions |

**Job Titles:**

The job_title field stores the specific position held by the employee:

| Value | Description |
|-------|-------------|
| ceo | Chief Executive Officer - highest-ranking executive |
| cto | Chief Technology Officer - technology leadership |
| hr_manager | Human Resource Manager - HR department head |
| auditor | Auditor - financial/compliance reviewer |
| sales_rep | Sales Representative - sales activities |
| designer | Designer - creative/technical design work |

**Shift Schedule:**

The shift field indicates the employee's work schedule:

| Value | Description |
|-------|-------------|
| morning | Morning Shift - typically starts around 8AM |
| afternoon | Afternoon Shift - typically starts around 1-2PM |
| night | Night Shift - typically starts around 9-10PM |
| flexible | Flexible/Others - non-standard schedule |

**Staff Fields - Detailed Explanation:**

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| first_name | CharField | The employee's given name. This is a required field (blank=False) and is used throughout the system for display purposes. Maximum length is 100 characters. |
| middle_name | CharField | The employee's middle name. This is a required field and is used for official documents and identification. |
| last_name | CharField | The employee's family name or surname. This is a required field and is used for official documentation. |
| birthdate | DateField | The employee's date of birth. This is optional and used for age verification and birthday celebrations. |
| age | IntegerField | The calculated age of the employee. This is optional and can be auto-calculated from birthdate. |
| sex | CharField | The employee's gender. Options include male, female, other, and prefer_not_to_say. This is optional to respect employee privacy. |
| employee_number | CharField | A unique identifier assigned to each employee. This is used as the username for system login and is the primary key for employee identification in external systems. Format typically follows patterns like EMP-001-2024. |
| status | CharField | Current employment status as explained above (active, inactive, on_leave, terminated). |
| job_title | CharField | The specific position held by the employee, selected from predefined choices. |
| type | CharField | The employment arrangement type (regular, probationary, contractual, etc.). |
| department | CharField | The department code indicating which part of the organization the employee belongs to. |
| rank | CharField | The employee's level in the organizational hierarchy. |
| shift | CharField | The work schedule assignment. |
| start_date | DateField | The date when the employee started working for the organization. This is used to calculate tenure. |
| tenure_active | CharField | Automatically calculated field showing how long the employee has been with the organization in years, months, and days format. |
| role | ForeignKey | Links to the Role model, defining what system access the user has. |
| departmentlink | ForeignKey | Alternative reference to Department model for more detailed department information. |
| positionlink | ForeignKey | Links to Position model for detailed position information. |
| sss_number | CharField | Social Security System identification number - required for Philippine employees for government benefits. |
| pagibig_number | CharField | Pag-IBIG Fund (HDMF) identification number - required for housing savings. |
| philhealth_number | CharField | PhilHealth identification number - required for health insurance. |
| email_address | EmailField | Employee's email address for official communications. |
| phone_number | CharField | Contact number for the employee. |
| emergency_contact_name | CharField | Name of person to contact in case of emergency. |
| emergency_contact_number | CharField | Phone number of emergency contact. |
| created_at | DateTime | Timestamp when the employee record was first created. |
| updated_at | DateTime | Timestamp of the most recent update to this record. |

**Tenure Calculation:**
The tenure_active field is automatically calculated using the start_date. The system computes the difference between today's date and the start_date, expressed in years, months, and days. This is updated automatically each time the record is saved.

#### 3.2.2 Department Model

The Department model defines the organizational structure of the company. Each department represents a distinct functional area.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| name | CharField | The official name of the department as it should appear in reports and interfaces. |
| code | CharField | A short code used to identify the department in dropdowns and references. |
| description | TextField | A detailed description of the department's function and responsibilities. |
| is_active | Boolean | Indicates whether the department is currently active. Inactive departments are hidden from new assignments but historical data is preserved. |

#### 3.2.3 Position Model

The Position model defines the job titles or roles within the organization.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| position_name | CharField | The full name of the position (e.g., "Senior Software Engineer"). |
| position_code | CharField | A short code for the position (e.g., "SSE"). |
| is_active | Boolean | Indicates whether this position is available for new assignments. |

#### 3.2.4 StaffHistory Model

The StaffHistory model provides an immutable audit trail of all changes made to employee records. Every time a staff member's information is modified, a new history record is created.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| staff | ForeignKey | Reference to the Staff record that was changed. |
| field_name | CharField | The name of the field that was modified (e.g., "department", "salary", "status"). |
| old_value | TextField | The value of the field before the change. Stored as text to accommodate any data type. |
| new_value | TextField | The new value after the change. |
| changed_at | DateTime | Timestamp when the change was made. |
| changed_by | ForeignKey | Reference to the UserAccount who made the change, enabling accountability. |

**Importance of Audit Trail:**
The StaffHistory model serves several critical functions:
- **Compliance** - Many industries require detailed employment records
- **Troubleshooting** - Helps identify when and how data was changed
- **Security** - Enables investigation of unauthorized changes
- **Reporting** - Provides historical context for employment decisions

---

### 3.3 Attendance Module

The Attendance Module is responsible for tracking employee daily attendance, including clock-in times, clock-out times, lunch breaks, overtime, and lateness. This module integrates with the payroll system to calculate deductions and additional earnings based on attendance.

#### 3.3.1 Attendance Model

The Attendance model stores one record for each employee for each day. It captures the complete attendance picture including arrival, departure, breaks, and calculated metrics.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | Reference to the Staff model, identifying who this attendance record belongs to. Each employee has their own attendance record. |
| date | DateField | The calendar date for this attendance record. Automatically set to the current date when created. |
| clock_in | TimeField | The time when the employee arrived and logged in. May be null if the employee didn't clock in. |
| clock_out | TimeField | The time when the employee left work. May be null if the employee hasn't clocked out yet or forgot to clock out. |
| status | CharField | The primary attendance status for the day. This is a legacy field maintained for backward compatibility. |
| statuses | CharField | A multi-select field that can hold multiple status values separated by commas. This allows tracking of complex situations like being both "late" and "on leave" on the same day. |
| lunch_in | TimeField | The time when the employee started their lunch break. This helps track lunch duration. |
| lunch_out | TimeField | The time when the employee ended their lunch break and returned to work. |
| hours_worked | DecimalField | The total number of hours worked for the day, calculated from clock_in and clock_out times (excluding lunch duration). |
| late_minutes | PositiveIntegerField | The number of minutes the employee arrived late beyond their scheduled start time. This is used to calculate late deductions in payroll. |
| overlunch_minutes | PositiveIntegerField | The number of minutes the employee exceeded the standard 60-minute lunch break. |
| overlunch_validated | BooleanField | A flag indicating whether HR has reviewed and approved the overlunch time. If validated, the overlunch minutes won't be deducted. |
| deduction_minutes | PositiveIntegerField | The total minutes to be deducted, calculated as late_minutes + overlunch_minutes (unless overlunch is validated). |
| ot_hours | DecimalField | Overtime hours worked beyond the regular schedule. These are paid at a higher rate. |
| nsd_hours | DecimalField | Night Shift Differential hours. Hours worked during the night shift (typically 10PM to 6AM) earn additional compensation. |
| note | TextField | HR remarks or notes about the attendance record, such as explanations for absences or special circumstances. |

**Attendance Status Choices:**

| Value | Description | Implication |
|-------|-------------|-------------|
| present | Employee was present and worked | Standard status, no deductions |
| late | Employee arrived after scheduled time | Late minutes calculated |
| absent | Employee did not report to work | Full day deduction applies |
| early_leave | Employee left before scheduled time | May have partial deduction |
| failed_to_clock_out | Employee forgot to clock out when leaving | Requires HR review |
| missing_lunch | Employee did not clock lunch | May require HR follow-up |

**How Attendance Calculates Hours:**

1. **Regular Hours Worked** = (clock_out - clock_in) - (lunch_out - lunch_in)
2. **Late Deduction** = late_minutes converted to peso value based on hourly rate
3. **Overtime** = Hours beyond scheduled shift, paid at 1.25x rate (or as configured)
4. **Night Differential** = Hours worked during night shift (10PM-6AM), paid at 1.10x rate

---

### 3.4 Leave Management Module

The Leave Management Module handles employee leave requests, approval workflows, and leave balance tracking. It ensures that leave policies are consistently applied and that accurate records are maintained for HR reporting.

#### 3.4.1 LeaveRequest Model

The LeaveRequest model stores each leave application submitted by employees. It tracks the request details and its current status in the approval process.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | Reference to the Staff model, identifying who is requesting leave. |
| leave_type | CharField | The type of leave being requested. Vacation Leave (VL) is typically for personal time off, while Sick Leave (SL) is for medical reasons. |
| start_date | DateField | The first day of the leave period. The employee will be marked as "on leave" from this date. |
| end_date | DateField | The last day of the leave period. The employee returns to work the next day. |
| total_days | DecimalField | The total number of leave days being requested. This is calculated from start_date and end_date, and may include partial days for half-day leaves. |
| purpose | TextField | The reason for the leave request. For sick leave, this may include a description of the illness. |
| status | CharField | The current state of the request: pending (awaiting review), approved (granted), or disapproved (rejected). |
| half_day | BooleanField | Indicates if this is a half-day leave request. |
| created_at | DateTime | When the request was submitted. |
| department | CharField | The employee's department at the time of request. |
| rank | CharField | The employee's rank at the time of request. |

**Leave Type Choices:**

| Value | Description | Accrual |
|-------|-------------|---------|
| vacation | Vacation Leave / Annual Leave | Typically accrued monthly or yearly |
| sick | Sick Leave | Typically accrued monthly or yearly |

**Leave Status Choices:**

| Value | Color | Description |
|-------|-------|-------------|
| pending | Yellow/Amber | The request has been submitted and is awaiting review by HR or management. |
| approved | Green | The request has been reviewed and granted. Leave credits will be deducted. |
| disapproved | Red | The request has been reviewed and denied. The employee should report to work. |

**Workflow Explanation:**

1. Employee submits leave request with dates and reason
2. System checks available leave credits
3. If sufficient credits, status = "pending"
4. HR reviews the request
5. If approved: status = "approved", credits deducted
6. If rejected: status = "disapproved", no credits deducted

#### 3.4.2 LeaveCredit Model

The LeaveCredit model tracks the leave balance for each employee. It maintains a record of how many leave days have been allocated, used, and remain available.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | Reference to the Staff member. |
| leave_type | CharField | Whether this is vacation leave or sick leave. |
| total | IntegerField | The total number of leave days allocated for the year. This is typically set at the beginning of the year or employment. |
| used | IntegerField | The number of leave days already taken. This increases as employees use their leave. |
| year | IntegerField | The calendar year for which these credits apply. Leave credits typically reset each year. |
| notes | TextField | Any additional notes about the leave credits, such as adjustments or special allocations. |

**Balance Calculation:**
```
Remaining Days = Total - Used
```

**Alerts:**
- Yellow warning: Less than 2 days remaining
- Red alert: Zero days remaining

#### 3.4.3 EmployeeProfileSettings Model

This model stores employee-specific HR settings that customize how the system handles each employee.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | One-to-one link with the Staff model. Each employee has exactly one profile settings record. |
| rank | CharField | The employee's rank level, used for determining leave accrual rates and other policies. |
| shift | CharField | The employee's default work shift, used for attendance calculations. |
| initial_vl | IntegerField | The initial vacation leave allocation when the employee was hired or at the start of the year. Default is typically 6 days. |
| initial_sl | IntegerField | The initial sick leave allocation. Default is typically 6 days. |
| current_vl | IntegerField | The current remaining vacation leave balance. This decreases as VL is used. |
| current_sl | IntegerField | The current remaining sick leave balance. This decreases as SL is used. |

---

### 3.5 Payroll Module

The Payroll Module is the heart of the compensation system. It calculates employee salaries based on attendance, applies deductions, adds allowances and bonuses, generates payslips, and maintains historical payroll records. This module ensures accurate and timely payment of employees.

#### 3.5.1 Payout Model

The Payout model represents one employee's specific pay period. salary payment for a Each payout record contains the complete salary information for one cutoff period.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| payroll_record | ForeignKey | Links this payout to the batch PayrollRecord, grouping all employees for the same period together. |
| employee | ForeignKey | Reference to the Staff model, identifying who receives this payment. |
| bank_account | ForeignKey | Reference to the BankAccount model, indicating where this payment should be deposited. |
| gross | DecimalField | The total earnings before any deductions. This includes basic salary plus all allowances and bonuses. |
| total_additions | DecimalField | The sum of all additional earnings beyond basic salary (allowances, incentives, overtime pay, etc.). |
| total_deductions | DecimalField | The sum of all amounts subtracted from gross pay (tax, SSS, PhilHealth, Pag-IBIG, etc.). |
| net | DecimalField | The actual take-home pay. This is what the employee receives. Formula: Net = Gross - Total Deductions |
| cutoff | CharField | Indicates whether this is for the first half (days 1-15) or second half (days 16-end) of the month. |
| month | SmallIntegerField | The month (1-12) for which this payout is being made. |
| year | IntegerField | The year for which this payout is being made. |
| created_at | DateTime | When this payout record was created in the system. |
| payslip | FileField | A PDF file containing the detailed payslip, generated for the employee's records. |
| released | BooleanField | Indicates whether the payment has been disbursed to the employee's bank account. |
| released_by | ForeignKey | Reference to the UserAccount who marked this payout as released. |
| released_at | DateTime | When the payout was marked as released. |

**Cutoff Period Explained:**

In the Philippines, many companies pay employees twice per month (bi-monthly):
- **1st Cutoff**: Covers days 1-15 of the month
- **2nd Cutoff**: Covers days 16 through the end of the month

The system calculates pro-rated salaries based on which cutoff is being processed.

#### 3.5.2 PayrollRecord Model

The PayrollRecord model acts as a container or batch record for all payouts within a specific pay period. It groups together all the Payout records for the same month and cutoff.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| cutoff | CharField | 1st or 2nd cutoff indicator. |
| month | SmallIntegerField | The month (1-12) for this payroll batch. |
| year | IntegerField | The year for this payroll batch. |
| finalized | BooleanField | A critical flag indicating whether this payroll has been finalized. Once finalized, the records are locked and cannot be modified. |
| finalized_at | DateTime | Timestamp when the payroll was finalized. |
| finalized_by | ForeignKey | Reference to the UserAccount who finalized the payroll. |

**Why Finalization Matters:**

When a PayrollRecord is finalized:
- All individual Payout records become locked
- The payroll data is considered official
- Changes require special "unfinalize" permission
- The finalized data can be used for government reports

#### 3.5.3 PayoutDetail Model

The PayoutDetail model provides the complete breakdown of how the payout was calculated. It shows every component of earnings and deductions in detail.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| payout | ForeignKey | Link back to the parent Payout record. |
| basic_salary | DecimalField | The employee's base salary for this pay period (monthly salary ÷ 2 for bi-monthly). |
| tips | DecimalField | Any tips or gratuities received by the employee. |
| lodging_allowance | DecimalField | Housing or lodging allowance if provided. |
| incentives | DecimalField | Performance bonuses or incentives earned this period. |
| holiday_pay | DecimalField | Additional pay for working on holidays. |
| regular_holiday_hours | DecimalField | Number of hours worked on regular holidays. |
| overtime_pay | DecimalField | Additional pay for overtime work. Calculated as: hours × hourly rate × 1.25 |
| nsd_pay | DecimalField | Night Shift Differential pay. Calculated as: hours × hourly rate × 1.10 |
| total_earnings | DecimalField | Sum of all earnings (basic + all additions). |
| withholding_tax | DecimalField | The tax deducted at source based on the employee's taxable income. |
| late_deduction | DecimalField | Deduction for arriving late, calculated from attendance late_minutes. |
| absence_deduction | DecimalField | Deduction for days not worked, calculated from absent days × daily rate. |
| sss_contribution | DecimalField | Employee's share of SSS contribution. |
| philhealth_contribution | DecimalField | Employee's share of PhilHealth contribution. |
| pagibig_contribution | DecimalField | Employee's share of Pag-IBIG contribution. |
| total_deductions | DecimalField | Sum of all deductions. |
| net_pay | DecimalField | The final take-home pay: Total Earnings - Total Deductions. |
| days_worked | DecimalField | Number of days actually worked in this period. |
| days_absent | DecimalField | Number of days absent in this period. |
| late_minutes | IntegerField | Total late minutes for the period. |
| overtime_hours | DecimalField | Total overtime hours worked. |
| nsd_hours | DecimalField | Total night shift hours worked. |
| total_government_deductions | DecimalField | Sum of SSS, PhilHealth, and Pag-IBIG contributions. |
| total_de_minimis | DecimalField | Sum of all de minimis (tax-exempt) benefits. |

**Payroll Calculation Formula:**

```
GROSS PAY = Basic Salary + Tips + Lodging + Incentives + Holiday Pay + Overtime Pay + Night Differential

TOTAL DEDUCTIONS = Withholding Tax + Late Deduction + Absence Deduction + SSS + PhilHealth + Pag-IBIG

NET PAY = GROSS PAY - TOTAL DEDUCTIONS
```

#### 3.5.4 Loan Model

The Loan model manages employee loans, tracking the principal amount, interest, payment schedule, and remaining balance.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | Reference to the Staff member who received the loan. |
| principal | DecimalField | The original loan amount borrowed by the employee. |
| interest_rate | DecimalField | The annual interest rate (expressed as a decimal, e.g., 0.05 for 5%). |
| term_months | IntegerField | The number of months over which the loan will be repaid. |
| start_date | DateField | The date when the loan was granted. |
| status | CharField | Current state of the loan: pending, approved, disapproved, or closed. |
| balance | DecimalField | The remaining amount to be paid. This decreases with each payroll deduction. |
| monthly_deduction | DecimalField | The amount deducted from the employee's salary each month. |
| per_cutoff | DecimalField | The amount deducted from each paycheck (monthly ÷ 2). |
| attachment | FileField | Scanned copy of the loan agreement or supporting documents. |
| created_at | DateTime | When the loan record was created. |

**Loan Status Choices:**

| Value | Color | Description |
|-------|-------|-------------|
| pending | Yellow | The loan application is awaiting approval. |
| approved | Green | The loan has been approved and active. Deductions are being made. |
| disapproved | Red | The loan application was rejected. |
| closed | Gray | The loan has been fully paid off. |

**Loan Calculation:**

The system automatically calculates loan repayment amounts:

```
Total with Interest = Principal + (Principal × Interest Rate)
Monthly Deduction = Total with Interest ÷ Term Months
Per Cutoff Deduction = Monthly Deduction ÷ 2
```

**Example:**
- Principal: ₱10,000
- Interest Rate: 5% per year
- Term: 10 months
- Total with Interest: ₱10,000 + (₱10,000 × 0.05) = ₱10,500
- Monthly Deduction: ₱10,500 ÷ 10 = ₱1,050
- Per Cutoff: ₱1,050 ÷ 2 = ₱525

---

### 3.6 Bank Management Module

The Bank Management Module handles employee bank account information and maintains a list of approved banks for salary disbursement.

#### 3.6.1 BankType Model

The BankType model stores the list of banks that the company uses for salary disbursement.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| name | CharField | The official name of the bank (e.g., "Bank of the Philippine Islands"). |
| code | CharField | A short code for the bank (e.g., "BPI"). |
| is_active | Boolean | Indicates whether this bank is currently used for disbursements. Inactive banks are hidden from selection but historical data is preserved. |

#### 3.6.2 BankAccount Model

The BankAccount model stores each employee's bank account information for salary disbursement.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | Reference to the Staff member who owns this bank account. |
| bank | ForeignKey | Reference to the BankType, indicating which bank the account is with. |
| account_number | CharField | The employee's bank account number. This must be accurate as salary will be deposited to this account. |
| account_type | CharField | Indicates whether this is a savings or checking account. |

---

### 3.7 Payroll Settings Module

The Payroll Settings Module contains all the configurable parameters that affect payroll calculations. This includes salary structures, deduction types, tax rates, and benefit programs.

#### 3.7.1 EmployeeSalarySetting Model

This model stores individual salary configurations for each employee, including the base salary and work schedule.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| employee | ForeignKey | Reference to the Staff member. |
| base_salary_monthly | DecimalField | The employee's full monthly basic salary before any adjustments. |
| tier | ForeignKey | Reference to the TierThresholdSetting, indicating the employee's performance tier. |
| work_schedule | CharField | The employee's work arrangement type. |
| salary_per_cutoff | DecimalField | Auto-calculated field: Monthly Salary ÷ 2. This is what the employee earns per cutoff. |
| effective_start_date | DateField | The date when this salary configuration becomes effective. |
| effective_end_date | DateField | The date when this salary configuration ends. Null means it's current/indefinite. |
| is_active | Boolean | Whether this salary setting is currently active. |
| notes | TextField | Notes about the salary, such as reasons for changes. |

**Work Schedule Choices:**

| Value | Description |
|-------|-------------|
| 8H | Standard 8-hour workday |
| 9.5H | 9.5-hour workday (common in some industries) |
| FLEX | Flexible hours - salary-based with no hourly computation |

**Why Multiple Salary Settings?**

An employee may have multiple salary settings over time. When salary changes occur, a new record is created rather than modifying the existing one. This preserves the history for:
- Audit purposes
- Back-pay calculations
- Government compliance
- Accurate historical reporting

#### 3.7.2 TierThresholdSetting Model

This model defines the performance tier system used for salary grading and potential incentives.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| tier_name | CharField | The tier identifier code (e.g., "TIER1", "NESTING"). |
| tier_label | CharField | A human-readable name (e.g., "Entry Level", "Senior"). |
| threshold_percentage | DecimalField | The minimum performance percentage required to qualify for this tier. |
| multiplier | DecimalField | A salary multiplier applied to base salary for this tier (e.g., 1.0500 for 5% increase). |
| effective_start_date | DateField | When this tier configuration becomes effective. |
| effective_end_date | DateField | When this tier configuration ends. Null means indefinite. |
| is_active | Boolean | Whether this tier is currently available. |

**Tier Structure:**

| Tier | Label | Description |
|------|-------|-------------|
| NESTING | Nesting | Entry-level employees still learning |
| TIER1 | Tier 1 | Junior level employees |
| TIER2 | Tier 2 | Mid-level employees |
| TIER3 | Tier 3 | Senior-level employees |
| TIER4 | Tier 4 | Lead employees |
| TIER5 | Tier 5 | Expert/top performers |

#### 3.7.3 DeductionType Model

This model defines all possible types of payroll deductions.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| code | CharField | A unique identifier for the deduction (e.g., "SSS", "LATE", "ABSENT"). |
| name | CharField | The display name for the deduction type. |
| category | CharField | The category this deduction belongs to. |
| description | TextField | Detailed description of what this deduction is for. |
| is_government | Boolean | Flag indicating if this is a mandatory government deduction (SSS, PhilHealth, Pag-IBIG). |
| is_tax_applicable | Boolean | Flag indicating if this deduction reduces taxable income. |
| is_active | Boolean | Whether this deduction type is currently available for use. |

**Deduction Categories:**

| Value | Description | Examples |
|-------|-------------|----------|
| ATTENDANCE | Deductions related to attendance issues | Late, Absent, Failed Clock Out |
| GOVERNMENT | Mandatory government contributions | SSS, PhilHealth, Pag-IBIG |
| LOAN | Loan and cash advance repayments | Salary Loan, Cash Advance |
| OTHER | Miscellaneous deductions | Union dues, insurance |

#### 3.7.4 DeMinimisType Model

This model defines the types of de minimis benefits - small tax-exempt allowances provided to employees.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| name | CharField | The name of the benefit (e.g., "Rice Allowance"). |
| code | CharField | A short code for the benefit. |
| amount | DecimalField | The fixed amount per cutoff if use_percent is False. |
| use_percent | Boolean | If True, the amount is calculated as a percentage of salary. |
| percent_value | DecimalField | The percentage value if use_percent is True. |

**Common De Minimis Benefits:**
- Rice Allowance
- Uniform Allowance
- Medical Allowance
- Laundry Allowance
- Gift Benefits

These are tax-exempt up to certain limits under Philippine tax law.

#### 3.7.5 GovernmentContributionRate Model

This model stores the contribution rate tables for mandatory government programs: SSS, PhilHealth, and Pag-IBIG.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| contribution_type | CharField | Which government program: SSS, PHILHEALTH, or PAGIBIG. |
| salary_bracket_min | DecimalField | The minimum salary in this bracket. |
| salary_bracket_max | DecimalField | The maximum salary in this bracket. |
| employee_share | DecimalField | The amount the employee contributes. |
| employer_share | DecimalField | The amount the employer contributes. |

**Government Contributions Explained:**

1. **SSS (Social Security System)** - Philippine social insurance program providing retirement, disability, and death benefits.

2. **PhilHealth** - National health insurance program providing medical coverage.

3. **Pag-IBIG (HDMF)** - Home Development Mutual Fund providing housing savings and loans.

These contributions are mandatory and are split between employee and employer.

---

## 4. USER INTERFACE

### 4.1 Dashboard Systems

The system provides three main dashboard interfaces, each tailored to different user roles:

#### 4.1.1 HR Dashboard

**URL:** `/hr_dashboard/`

The HR Dashboard is the primary interface for HR personnel. It provides access to all HR functions organized in a sidebar navigation menu.

**Main Menu Structure:**

| Menu Item | URL Path | Description |
|-----------|----------|-------------|
| Dashboard Home | /hr_dashboard/ | Overview and quick stats |
| User Management | /hr_dashboard/user-management/ | Manage system users |
| Employees | /hr_dashboard/employees/ | View employee list |
| Attendance | /hr_dashboard/attendance/ | View/manage attendance |
| Leave Requests | /hr_dashboard/leave-requests/ | Process leave applications |
| Leave Credits | /hr_dashboard/leave-credits/ | View leave balances |
| Payroll | /hr_dashboard/payroll/individual/ | Process salaries |
| Payouts | /hr_dashboard/payout/ | View payment records |
| Payroll Settings | /hr_dashboard/payroll-settings/ | Configure payroll |
| Loans | /hr_dashboard/loans/ | Manage employee loans |
| Bank Accounts | /hr_dashboard/bank-accounts/ | Bank information |
| Bank Types | /hr_dashboard/bank-types/ | Bank list management |
| Shift Rules | /hr_dashboard/shift-rules/ | Work schedules |
| Departments | /hr_dashboard/department/ | Department management |
| Positions | /hr_dashboard/positions/ | Position management |

#### 4.1.2 Master Dashboard

**URL:** `/master_dashboard/`

The Master Dashboard is for top-level administrators who need visibility across all departments and system functions. It provides:
- Company-wide statistics
- Cross-department reports
- System administration features

#### 4.1.3 Employee Self-Service

**URL:** `/hr_dashboard/self-service/`

The Employee Self-Service portal allows employees to:
- View their own profile
- Clock in and out
- View their own attendance history
- Submit leave requests
- View their leave balances
- View their own payslips

### 4.2 Login System

**URL:** `/login/`

The login system provides secure access to the system:

**Features:**
1. **Username/Password Authentication** - Users enter their credentials
2. **Department Selection** - If user has access to multiple departments
3. **Password Reset** - Forgot password functionality via email
4. **Session Management** - Automatic logout after inactivity
5. **Login History** - All login attempts are recorded

### 4.3 Registration

**URL:** `/signup/` (if enabled)

New user registration may be available through self-service or must be created by administrators.

**Registration Fields:**
- Employee Number (for existing employees)
- Email Address
- Password
- Confirm Password

---

## 5. PROCESS FLOWS

### 5.1 Payroll Processing Flow

The payroll processing flow transforms attendance data into salary payments:

```
1. SELECT PROCESSING METHOD
   ├── Individual Payroll - Process one employee at a time
   └── Batch Payroll - Process multiple employees at once

2. SELECT PAY PERIOD
   ├── Month: 1-12
   ├── Year: Current year
   └── Cutoff: 1st (Days 1-15) or 2nd (Days 16-End)

3. RETRIEVE ATTENDANCE DATA
   ├── Days worked in period
   ├── Late minutes accumulated
   ├── Absent days
   ├── Overtime hours worked
   └── Night shift hours worked

4. CALCULATE EARNINGS
   ├── Basic Salary (monthly ÷ 2)
   ├── + Lodging Allowance
   ├── + Incentives/Bonuses
   ├── + Holiday Pay (if worked)
   ├── + Overtime Pay (hours × rate × 1.25)
   ├── + Night Differential (hours × rate × 1.10)
   └── = TOTAL EARNINGS (GROSS)

5. CALCULATE DEDUCTIONS
   ├── Withholding Tax (based on taxable income)
   ├── Late Deduction (minutes × hourly rate)
   ├── Absence Deduction (days × daily rate)
   ├── SSS Contribution
   ├── PhilHealth Contribution
   ├── Pag-IBIG Contribution
   ├── Loan Deductions (if any)
   └── = TOTAL DEDUCTIONS

6. CALCULATE NET PAY
   └── NET = GROSS - DEDUCTIONS

7. PREVIEW AND FINALIZE
   ├── Preview all calculations
   ├── Make adjustments if needed
   └── Finalize to lock records

8. RELEASE PAYMENT
   ├── Mark as released when paid
   └── Generate PDF payslips
```

### 5.2 Leave Request Flow

```
1. EMPLOYEE SUBMITS REQUEST
   ├── Select leave type (Vacation/Sick)
   ├── Select start and end dates
   ├── Enter purpose/reason
   └── Submit request

2. SYSTEM VALIDATION
   ├── Check available leave credits
   ├── Validate date range
   └── Ensure no conflicts

3. HR REVIEW
   ├── Review request details
   ├── Check work coverage
   └── Make decision

4. APPROVE OR DISAPPROVE
   ├── APPROVE: Deduct credits, update status
   └── DISAPPROVE: Return credits, update status

5. NOTIFICATION
   ├── Employee notified of decision
   └── Attendance updated if approved
```

### 5.3 Loan Processing Flow

```
1. HR CREATES LOAN RECORD
   ├── Select employee
   ├── Enter principal amount
   ├── Set annual interest rate
   ├── Define term (months)
   ├── Set start date
   └── Save as Pending

2. SYSTEM CALCULATIONS
   ├── Calculate total with interest
   ├── Calculate monthly deduction
   ├── Calculate per-cutoff deduction
   └── Display amortization schedule

3. MANAGER APPROVAL
   ├── Review loan details
   ├── Approve or disapprove
   └── Add notes if needed

4. STATUS UPDATE
   ├── Approved: Begin payroll deductions
   ├── Disapproved: No action, notify employee
   └── Pending: Await decision

5. AUTOMATIC DEDUCTION
   ├── Each payroll: deduct per_cutoff
   ├── Update remaining balance
   └── Mark as Closed when fully paid
```

---

## 6. SECURITY FEATURES

### 6.1 Authentication Security

- **Password Hashing** - All passwords stored using Django's make_password() function
- **Login Attempt Tracking** - All login attempts (success/failure) are recorded
- **IP Address Logging** - Records the IP address of login attempts
- **Session Management** - Automatic session timeout after inactivity

### 6.2 Authorization

- **Role-Based Access Control (RBAC)** - Users can only access features allowed by their role
- **Department Filtering** - HR users typically only see their department's data
- **View-Level Permissions** - Different views for different user types

### 6.3 Audit Trail

- **Staff History** - Every change to employee records is logged
- **Login History** - All authentication attempts are recorded
- **Payroll Audit Logs** - All payroll operations are tracked
- **Change Tracking** - Who changed what and when

---

## 7. DATA EXPORT AND REPORTS

### 7.1 Export Capabilities

| Export Type | Description | Location |
|-------------|-------------|----------|
| CSV Export | Download data in spreadsheet format | Attendance, Payouts pages |
| PDF Payslip | Generate individual employee payslips | Payout Detail page |
| Print Report | Print-friendly view | All list pages |

### 7.2 Report Types

| Report | URL | Description |
|--------|-----|-------------|
| Payroll History | /hr_dashboard/payroll-settings/history/ | Monthly payroll summaries |
| Attendance Records | /hr_dashboard/attendance/ | Daily attendance details |
| Leave Requests | /hr_dashboard/leave-requests/ | Leave application status |
| Leave Credits | /hr_dashboard/leave-credits/ | Leave balance overview |
| Loan Portfolio | /hr_dashboard/loans/ | Active loans summary |

---

## 8. SYSTEM REQUIREMENTS

### 8.1 Software Requirements

| Requirement | Version | Description |
|-------------|---------|-------------|
| Python | 3.x | Programming language |
| Django | 4.x+ | Web framework |
| PostgreSQL | Latest | Database |
| HTML5 | - | Markup language |
| CSS3 | - | Styling |
| JavaScript | ES6+ | Client-side scripting |

### 8.2 Browser Compatibility

- Google Chrome (recommended)
- Mozilla Firefox
- Microsoft Edge
- Safari

---

## 9. CONCLUSION

The Rockstar Beta Company System is a comprehensive HR solution that provides end-to-end management of the employee lifecycle. From recruitment to retirement, the system streamlines HR operations through automation while maintaining accurate records for compliance and decision-making.

The modular architecture allows for easy customization and extension, while the robust security features protect sensitive employee data. The comprehensive audit trail ensures accountability and compliance with regulatory requirements.

This documentation provides the foundation for understanding and utilizing the system effectively. For additional assistance, please contact your system administrator.

---

**Document Information:**
- Document Title: System Documentation Report
- System Name: Rockstar Beta Company System
- Version: 1.0
- Date: March 2026
- Framework: Django (Python)

