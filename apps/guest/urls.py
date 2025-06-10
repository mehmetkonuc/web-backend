from django.urls import path
from . import views

app_name = "guest"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset-confirm/<str:uidb64>/<str:token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("check-username/", views.check_username_availability, name="check_username"),
]