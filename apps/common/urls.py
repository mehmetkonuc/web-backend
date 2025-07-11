from django.urls import path
from . import views

app_name = "common"

urlpatterns = [
    path("terms-of-service/", views.TermsOfServiceView.as_view(), name="terms_of_service"),
    path("privacy-policy/", views.PrivacyPolicyView.as_view(), name="privacy_policy"),
]