from django.shortcuts import render
from .decorators import login_required
# Create your views here.
@login_required
def sales_dashboard(request):
    # add context if needed
    context = {}
    return render(request, 'dashboard/sales_dashboard.html', context)
