# master_dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.master_dashboard, name="aaaaaaamaster_dashboard"),
]