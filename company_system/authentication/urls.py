from django.urls import path
from . import views

urlpatterns = [
    
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("select_department/", views.select_department, name="select_department"),
    path("unauthorized/", views.unauthorized, name="unauthorized"),
    path("logout/", views.logout_view, name="logout"),  
]