# master_dashboard/views.py
from django.shortcuts import render
from authentication.models import MasterEmployee

def master_dashboard(request):
    # Example: fetch all department data (replace with real queries)
    departments = {
        "Admin": {"users_count": 25, "active_projects": 10},
        "Sales": {"users_count": 40, "active_deals": 15},
        "Finance": {"users_count": 10, "pending_reports": 5},
    }

    return render(request, "master_dashboard/dashboard.html", {"departments": departments})