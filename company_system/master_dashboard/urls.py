# master_dashboard/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('sales/', include('sales.urls')),
    path('human_resource/', include('human_resource.urls')),
    path("", views.master_dashboard, name="master_dashboard"),
]
