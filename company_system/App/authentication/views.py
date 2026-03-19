from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from App.users.models import Staff
from .models import UserAccount, LoginHistory
from django.contrib.auth.hashers import make_password, check_password
from .decorators import login_required
from .forms import SignupForm


# ============================================
# SESSION REFRESH - Keep session alive
# ============================================
def session_refresh(request):
    """Refresh session activity timestamp to prevent idle timeout"""
    if request.session.get('employee_number'):
        request.session['last_activity'] = timezone.now().isoformat()
        request.session.modified = True
        return HttpResponse('OK')
    return HttpResponse('NOT_LOGGED_IN', status=401)


# ============================================
# HELPER FUNCTION: Log login attempt
# ============================================
def log_login_attempt(request, employee, employee_number, status, failure_reason=''):
    """Log login attempt to history"""
    # Get IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Get user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    
    LoginHistory.objects.create(
        employee=employee,
        employee_number=employee_number,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        failure_reason=failure_reason
    )


# ============================================
# RATE LIMITING SETTINGS
# ============================================
MAX_LOGIN_ATTEMPTS = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)  # Lock after 5 failed attempts
LOCKOUT_DURATION = getattr(settings, 'LOCKOUT_DURATION', 900)  # 15 minutes lockout


def check_rate_limit(request, employee_number):
    """Check if user is rate limited using server-side cache"""
    from django.core.cache import cache
    import time
    
    # Check if locked in cache (server-side, not session-based)
    lock_key = f'login_locked_{employee_number}'
    locked_until = cache.get(lock_key)
    
    if locked_until:
        remaining = int(locked_until - time.time())
        if remaining > 0:
            minutes = remaining // 60
            seconds = remaining % 60
            if minutes > 0:
                return True, remaining, f"Account locked. Try again in {minutes} minute(s)."
            return True, remaining, f"Account locked. Try again in {seconds} second(s)."
        else:
            # Lock expired, delete it
            cache.delete(lock_key)
    
    return False, 0, ""


def increment_failed_attempt(request, employee_number):
    """Increment failed attempt counter using server-side cache"""
    from django.core.cache import cache
    import time
    
    attempt_key = f'login_attempts_{employee_number}'
    attempts = cache.get(attempt_key, 0) + 1
    
    # Store in cache for 15 minutes (same as lockout duration)
    cache.set(attempt_key, attempts, LOCKOUT_DURATION)
    
    if attempts >= MAX_LOGIN_ATTEMPTS:
        # Lock the account in cache
        lock_key = f'login_locked_{employee_number}'
        cache.set(lock_key, time.time() + LOCKOUT_DURATION, LOCKOUT_DURATION)
        # Reset attempts
        cache.set(attempt_key, 0, LOCKOUT_DURATION)
        return True
    
    return False


def clear_failed_attempts(request, employee_number):
    """Clear failed attempts on successful login"""
    from django.core.cache import cache
    
    attempt_key = f'login_attempts_{employee_number}'
    cache.delete(attempt_key)


# ============================================
# HELPER FUNCTION: Get current employee
# ============================================
class OwnerPlaceholder:
    """Placeholder object for owner when bypassing login"""
    def __init__(self):
        self.id = 0
        self.employee_number = 'OWNER'
        self.first_name = 'OWNER'
        self.last_name = ''
        self.email_address = ''
        self.role = None

def get_current_employee(request):
    """
    Returns the current Staff object or a placeholder if owner/special user.
    Use this instead of directly querying Staff.objects.get()
    """
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    if is_owner or emp_num == 'OWNER':
        return OwnerPlaceholder()
    
    if emp_num:
        try:
            return Staff.objects.get(employee_number=emp_num)
        except Staff.DoesNotExist:
            return None
    return None


def get_current_user(request):
    """
    Returns the Django User object for the currently logged-in user.
    This bridges the custom session-based auth with Django's User model.
    Returns None if no user is logged in.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    emp_num = request.session.get('employee_number')
    is_owner = request.session.get('is_owner', False)
    
    # For owner login, try to get or create an owner user
    if is_owner or emp_num == 'OWNER':
        try:
            # Try to get or create a superuser for owner
            user, created = User.objects.get_or_create(
                username='owner',
                defaults={
                    'is_superuser': True,
                    'is_staff': True,
                    'first_name': 'Owner',
                    'last_name': 'Account',
                }
            )
            return user
        except Exception:
            return None
    
    if emp_num:
        try:
            staff = Staff.objects.get(employee_number=emp_num)
            # Get the UserAccount linked to this employee
            user_account = UserAccount.objects.get(employee=staff)
            return user_account.user
        except (Staff.DoesNotExist, UserAccount.DoesNotExist, Exception):
            return None
    return None


def logout_view(request):
    request.session.flush()  # Clears all session data
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


# ------------------------
# Signup
# ------------------------
def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        
        if form.is_valid():
            emp_num = form.cleaned_data['employee_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # 1. Check if employee exists
            try:
                emp = Staff.objects.select_related("role").get(employee_number=emp_num)
            except Staff.DoesNotExist:
                messages.error(request, "Employee Number not found in Master Employee list.")
                return render(request, "authentication/signup.html", {'form': form})

            # 2. Validate email only
            if emp.email_address.lower() != email:
                messages.error(request, "Email does not match our records.")
                return render(request, "authentication/signup.html", {'form': form})

            # 3. Prevent duplicate accounts
            if UserAccount.objects.filter(employee=emp).exists():
                messages.error(request, "Account already exists for this employee.")
                return render(request, "authentication/signup.html", {'form': form})

            # 4. Check if employee has a role assigned
            if emp.role is None:
                messages.error(request, "Your account has no role assigned. Please contact your admin or HR to assign your role before registering.")
                return render(request, "authentication/signup.html", {'form': form})

            # 5. Check role dynamically
            role_name = emp.role.role_name
            allowed_roles = ["Admin", "Sales", "Developer", "Master", "Human Resource"]
            if role_name not in allowed_roles:
                messages.error(request, f"Role '{role_name}' is not allowed to register.")
                return render(request, "authentication/signup.html", {'form': form})

            # 5. Create user account
            UserAccount.objects.create(
                employee=emp,
                password=make_password(password)
            )

            messages.success(request, "Account created successfully. Please login.")
            return redirect("login")
        else:
            # Form validation errors (password requirements, password mismatch)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return render(request, "authentication/signup.html", {'form': form})

    return render(request, "authentication/signup.html", {'form': SignupForm()})


# ------------------------
# Login
# ------------------------
def login_view(request):
    # Check for timeout message
    if request.GET.get('timeout') == 'true':
        messages.warning(request, "Your session has expired due to inactivity. Please login again.")
    
    if request.method == "POST":
        emp_num = request.POST.get("employee_number", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        # === RATE LIMITING CHECK ===
        is_locked, remaining, lock_message = check_rate_limit(request, emp_num)
        if is_locked:
            messages.error(request, lock_message)
            # Log the locked attempt
            log_login_attempt(request, None, emp_num, 'failed', f'Account locked due to too many attempts ({remaining}s remaining)')
            return redirect("login")

        # === OWNER BYPASS LOGIN ===
        # Use check_password for secure password verification
        if emp_num == settings.OWNER_LOGIN_ID and check_password(password, settings.OWNER_PASSWORD_HASH):
            request.session['employee_number'] = 'OWNER'
            request.session['employee_id'] = 0
            request.session['is_owner'] = True
            request.session['last_activity'] = timezone.now().isoformat()
            messages.success(request, "Welcome, Owner!")
            # Log owner login
            log_login_attempt(request, None, 'OWNER', 'success')
            return redirect("select_department")

        # === NORMAL EMPLOYEE LOGIN ===
        # 1️⃣ Fetch Staff with role
        try:
            emp = Staff.objects.select_related("role").get(
                employee_number=emp_num,
                email_address__iexact=email
            )
        except Staff.DoesNotExist:
            # Increment failed attempts
            increment_failed_attempt(request, emp_num)
            messages.error(request, "Invalid employee number or email.")
            # Log failed attempt
            log_login_attempt(request, None, emp_num, 'failed', 'Invalid employee number or email')
            return redirect("login")

        # 2️⃣ Check if UserAccount exists
        try:
            user = UserAccount.objects.get(employee=emp)
        except UserAccount.DoesNotExist:
            # Increment failed attempts
            increment_failed_attempt(request, emp_num)
            messages.error(request, "User account not found. Please signup first.")
            # Log failed attempt
            log_login_attempt(request, emp, emp_num, 'failed', 'User account not found')
            return redirect("login")

        # 2a️⃣ Check if account is active (UserAccount)
        if not user.is_active:
            # Increment failed attempts
            increment_failed_attempt(request, emp_num)
            messages.error(request, "Your account has been deactivated. Please contact admin for assistance.")
            # Log failed attempt
            log_login_attempt(request, emp, emp_num, 'failed', 'Account deactivated')
            return redirect("login")

        # 2b️⃣ Check if employee status is active
        if emp.status == 'inactive':
            messages.error(request, "Your employee record is marked as inactive. Please contact admin for assistance.")
            log_login_attempt(request, emp, emp_num, 'failed', 'Employee status inactive')
            return redirect("login")

        if emp.status == 'terminated':
            messages.error(request, "Your employment has been terminated. Access denied.")
            log_login_attempt(request, emp, emp_num, 'failed', 'Employee terminated')
            return redirect("login")

        # 3️⃣ Check password
        if not user.check_password(password):
            # Increment failed attempts
            is_locked = increment_failed_attempt(request, emp_num)
            
            if is_locked:
                messages.error(request, f"Too many failed attempts. Account locked for 15 minutes.")
                log_login_attempt(request, emp, emp_num, 'failed', 'Account locked due to too many failed attempts')
            else:
                attempts_left = MAX_LOGIN_ATTEMPTS - request.session.get(f'login_attempts_{emp_num}', 0)
                messages.error(request, f"Invalid password. {attempts_left} attempt(s) remaining.")
                log_login_attempt(request, emp, emp_num, 'failed', 'Invalid password')
            return redirect("login")

        # 4️⃣ Update last_login timestamp
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Clear failed attempts on successful login
        clear_failed_attempts(request, emp_num)
        
        # Log successful login
        log_login_attempt(request, emp, emp_num, 'success')

        # 5️⃣ Reset idle timer on login
        request.session['last_activity'] = timezone.now().isoformat()
        
        # 6️⃣ Handle Remember Me
        remember_me = request.POST.get('remember_me')
        if remember_me:
            # Session expires in 7 days
            request.session.set_expiry(60 * 60 * 24 * 7)
        else:
            # Session expires on browser close (default)
            request.session.set_expiry(0)

        # 6️⃣ Determine role dynamically
        role_name = emp.role.role_name

        # 5️⃣ Redirect based on role
        if role_name in ["Master", "Developer"]:
            # Save employee_number in session to use in select_department
            request.session['employee_number'] = emp.employee_number
            request.session['employee_id'] = emp.id  # Store employee ID for later use
            return redirect("select_department")

        elif role_name == "Admin":
            request.session['employee_number'] = emp.employee_number
            request.session['employee_id'] = emp.id
            return redirect("/admin_dashboard/")

        elif role_name == "Sales":
            request.session['employee_number'] = emp.employee_number
            request.session['employee_id'] = emp.id
            return redirect("/sales_dashboard/")

        elif role_name == "Human Resource":
            request.session['employee_number'] = emp.employee_number
            request.session['employee_id'] = emp.id
            return redirect("/hr_dashboard/")

        else:
            return redirect("unauthorized")

    return render(request, "authentication/login.html")


# ------------------------
# Select Department (Master/Developer)
# ------------------------



@login_required
def select_department(request):
    # 1️⃣ Check if owner
    is_owner = request.session.get('is_owner', False)
    
    if is_owner:
        # Owner gets access to all departments
        departments = ["Admin", "Sales", "Human Resource", "Compliance", "All"]
        
        # 2️⃣ Handle POST (department selection)
        if request.method == "POST":
            selected_dept = request.POST.get("department")
            
            if selected_dept == "All":
                request.session['current_dept'] = "All"
                return redirect("master_dashboard:master_dashboard")
            elif selected_dept in ["Admin", "Sales", "Human Resource", "Compliance"]:
                request.session['current_dept'] = selected_dept
                
                if selected_dept == "Admin":
                    return redirect("/admin_dashboard/")
                elif selected_dept == "Sales":
                    return redirect("/sales_dashboard/")
                elif selected_dept == "Human Resource":
                    return redirect("/hr_dashboard/")
                elif selected_dept == "Compliance":
                    return redirect("/sales_dashboard/")
            else:
                messages.error(request, "Selected department is invalid.")
                return redirect("select_department")
        
        return render(request, "authentication/select_department.html", {"departments": departments})
    
    # === Normal Employee Flow ===
    # 1️⃣ Ensure user is logged in
    emp_num = request.session.get('employee_number')
    if not emp_num:
        messages.error(request, "Please login first.")
        return redirect("login")

    # 2️⃣ Fetch staff with related role
    try:
        emp = Staff.objects.select_related("role").get(employee_number=emp_num)
    except Staff.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect("login")

    # 3️⃣ Determine available departments
    role_name = emp.role.role_name

    # Master/Developer can select other departments
    if role_name in ["Master", "Developer"]:
        # Example: assume these are all possible departments
        all_departments = ["Admin", "Sales", "Human Resource", "Compliance"]
        departments = all_departments  # Exclude Master/Developer
    else:
        # Single-role employees only have their own department
        departments = [role_name]

    # 4️⃣ Handle POST (department selection)
    if request.method == "POST":
        selected_dept = request.POST.get("department")

        if selected_dept == "All" and role_name in ["Master", "Developer"]:
            # Master/Developer full access
            return redirect("master_dashboard:master_dashboard")
        elif selected_dept in departments:
            request.session['current_dept'] = selected_dept
            request.session['employee_id'] = emp.id

            # Redirect to department dashboard dynamically
            if selected_dept == "Admin":
                return redirect("/admin_dashboard/")
            elif selected_dept == "Sales":
                return redirect("/sales_dashboard/")
            elif selected_dept == "Human Resource":
                return redirect("/hr_dashboard/")
            elif selected_dept == "Compliance":
                return redirect("/sales_dashboard/")
            else:
                return redirect("unauthorized")
        else:
            messages.error(request, "Selected department is invalid.")
            return redirect("select_department")

    # 5️⃣ Render template with departments list
    return render(request, "authentication/select_department.html", {"departments": departments})


# ------------------------
# Unauthorized page
# ------------------------
def unauthorized(request):
    return render(request, "authentication/unauthorized.html")


# ------------------------
# Extend Session (AJAX)
# ------------------------
@require_POST
def extend_session(request):
    """Extend session when user clicks Stay Logged In"""
    if request.session.get('employee_number'):
        # Reset last activity
        request.session['last_activity'] = timezone.now().isoformat()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=401)



