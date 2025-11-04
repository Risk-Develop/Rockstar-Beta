from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('edit-employee/<int:id>/', views.edit_employee, name='edit_employee'),
    path('delete-employee/<int:id>/', views.delete_employee, name='delete_employee'),
    path('export/', views.export_employees, name='export_employees'),
]
