# authentication/decorators.py
from django.shortcuts import redirect
from django.contrib import messages

def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('employee_number'):
            messages.error(request, "Please login to access this page.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper

