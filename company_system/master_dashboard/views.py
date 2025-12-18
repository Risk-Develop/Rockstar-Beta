from django.shortcuts import render
from users.models import Staff, Role
from authentication.decorators import login_required

@login_required
def master_dashboard(request):
    emp_num = request.session.get('employee_number')
    emp = Staff.objects.get(employee_number=emp_num)

    # Map roles to URL names
    role_url_map = {
        "Sales": "sales:sales_dashboard",
        "Human Resource": "human_resource:hr_dashboard",
        
        # Add other roles here
    }

    # Fetch all roles except Master/Developer
    roles = Role.objects.exclude(role_name__in=["Master", "Developer"])

    departments = []
    for role in roles:
        url_name = role_url_map.get(role.role_name)
        if url_name:  # Only include roles that have dashboards
            user_count = Staff.objects.filter(role_id=role.id).count()
            description = getattr(role, "description", "")  # Fetch description from DB
            departments.append({
                "name": role.role_name,
                "url": url_name,
                "user_count": user_count,
                "description": description
            })

    context = {
        "employee": emp,
        "departments": departments,
    }

    return render(request, "master/master_dashboard.html", context)
