from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.profile_redirect_view, name="profile_redirect"),
    path("upload-avatar/", views.upload_avatar_view, name="upload_avatar"),
    path("reset-avatar/", views.reset_avatar_view, name="reset_avatar"),
    path("follow-requests/", views.follow_requests_view, name="follow_requests"),
    path("follow-requests/<int:request_id>/accept/", views.accept_follow_request_view, name="accept_follow_request"),
    path("follow-requests/<int:request_id>/reject/", views.reject_follow_request_view, name="reject_follow_request"),
    path("blocked-users/", views.blocked_users_view, name="blocked_users"),
    path("privacy-toggle/", views.toggle_profile_privacy_view, name="toggle_privacy"),
    path("settings/", views.profile_settings_view, name="settings"),
    path("settings/privacy/", views.privacy_settings_view, name="privacy_settings"),
    path("settings/password/", views.password_change_view, name="password_change"),
    path("settings/delete-account/", views.delete_account_view, name="delete_account"),
    path("verify-email/<uuid:token>/", views.verify_email_view, name="verify_email"),
    path("resend-verification-email/", views.resend_verification_email_view, name="resend_verification_email"),
    path("<str:username>/", views.profile_view, name="profile"),
    path("<str:username>/follow/", views.follow_toggle_view, name="follow_toggle"),
    path("<str:username>/followers/", views.followers_view, name="followers"),
    path("<str:username>/following/", views.following_view, name="following"),
    path("<str:username>/block/", views.block_toggle_view, name="block_toggle"),

]