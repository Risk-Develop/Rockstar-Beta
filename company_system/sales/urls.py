from django.urls import path
from . import views

app_name = "sales"  # important for namespacing

urlpatterns = [
    path('', views.sales_dashboard, name='sales_dashboard'),
]