from django.shortcuts import render, redirect
from django.contrib import messages
from users.models import Staff
from .models import UserAccount
from django.contrib.auth.hashers import make_password
from .decorators import login_required



def logout_view(request):
    request.session.flush()  # Clears all session data
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


# ------------------------
# Signup
# ------------------------
def signup(request):
    if request.method == "POST":
        emp_num = request.POST.get("employee_number", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # 1. Check if employee exists
        try:
            emp = Staff.objects.select_related("role").get(employee_number=emp_num)
        except Staff.DoesNotExist:
            messages.error(request, "Employee Number not found in Master Employee list.")
            return redirect("signup")

        # 2. Validate email only
        if emp.email_address.lower() != email:
            messages.error(request, "Email does not match our records.")
            return redirect("signup")

        # 3. Confirm password
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        # 4. Prevent duplicate accounts
        if UserAccount.objects.filter(employee=emp).exists():
            messages.error(request, "Account already exists for this employee.")
            return redirect("signup")

        # 5. Check role dynamically (optional)
        role_name = emp.role.role_name
        allowed_roles = ["Admin", "Sales", "Developer", "Master"]
        if role_name not in allowed_roles:
            messages.error(request, f"Role '{role_name}' is not allowed to register.")
            return redirect("signup")

        # 6. Create user account
        UserAccount.objects.create(
            employee=emp,
            password=make_password(password)
        )

        messages.success(request, "Account created successfully. Please login.")
        return redirect("login")

    return render(request, "authentication/signup.html")


# ------------------------
# Login
# ------------------------
def login_view(request):
    if request.method == "POST":
        emp_num = request.POST.get("employee_number", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        # 1️⃣ Fetch Staff with role
        try:
            emp = Staff.objects.select_related("role").get(
                employee_number=emp_num,
                email_address__iexact=email
            )
        except Staff.DoesNotExist:
            messages.error(request, "Invalid employee number or email.")
            return redirect("login")

        # 2️⃣ Check if UserAccount exists
        try:
            user = UserAccount.objects.get(employee=emp)
        except UserAccount.DoesNotExist:
            messages.error(request, "User account not found. Please signup first.")
            return redirect("login")

        # 3️⃣ Check password
        if not user.check_password(password):
            messages.error(request, "Invalid password.")
            return redirect("login")

        # 4️⃣ Determine role dynamically
        role_name = emp.role.role_name

        # 5️⃣ Redirect based on role
        if role_name in ["Master", "Developer"]:
            # Save employee_number in session to use in select_department
            request.session['employee_number'] = emp.employee_number
            return redirect("select_department")

        elif role_name == "Admin":
            request.session['employee_number'] = emp.employee_number
            return redirect("/admin_dashboard/")

        elif role_name == "Sales":
            request.session['employee_number'] = emp.employee_number
            return redirect("/sales_dashboard/")

        else:
            return redirect("unauthorized")

    return render(request, "authentication/login.html")


# ------------------------
# Select Department (Master/Developer)
# ------------------------



@login_required
def select_department(request):
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
        all_departments = ["Admin", "Sales","Compliance"]
        departments = all_departments  # Exclude Master/Developer
    else:
        # Single-role employees only have their own department
        departments = [role_name]

    # 4️⃣ Handle POST (department selection)
    if request.method == "POST":
        selected_dept = request.POST.get("department")

        if selected_dept == "All" and role_name in ["Master", "Developer"]:
            # Master/Developer full access
            return redirect("master_dashboard")
        elif selected_dept in departments:
            request.session['current_dept'] = selected_dept

            # Redirect to department dashboard dynamically
            if selected_dept == "Admin":
                return redirect("/admin_dashboard/")
            elif selected_dept == "Sales":
                return redirect("/sales_dashboard/")
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


