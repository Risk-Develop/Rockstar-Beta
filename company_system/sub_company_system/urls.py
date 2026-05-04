"""
URL configuration for company_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', include('App.employees.urls')),
    path('', include('App.authentication.urls')),
    path('user_management/', include('App.users.urls')),
    path('sales_dashboard/', include('App.sales.urls')),
    path('hr_dashboard/', include('App.human_resource.urls')),
    path('human_resource/', include('App.human_resource.urls')),  # Direct human_resource access
    path("auth/", include("App.authentication.urls")),
    path("master_dashboard/", include("App.master_dashboard.urls")),
    path('task/', include('App.task_management.urls')),
    # django-allauth URLs
    path('accounts/', include('allauth.urls')),
]
