from django.urls import path
from django.views.decorators.http import require_POST
from . import views

urlpatterns = [
    
    path("signup/", views.signup, name="signup"),
    path("", views.login_view, name="login"),
    path("select_department/", views.select_department, name="select_department"),
    path("unauthorized/", views.unauthorized, name="unauthorized"),
    path("logout/", require_POST(views.logout_view), name="logout"),  
    path("extend_session/", require_POST(views.extend_session), name="extend_session"),
    path("session_refresh/", views.session_refresh, name="session_refresh"),
]
