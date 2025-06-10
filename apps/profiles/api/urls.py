from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.ProfileViewSet, basename='profile')

urlpatterns = [
    # Follow system routes (ÖNCE özel path'ler)
    path('follow-requests/', views.FollowRequestListView.as_view(), name='follow-requests-list'),
    path('follow-requests/<int:request_id>/accept/', views.AcceptFollowRequestView.as_view(), name='accept-follow-request'),
    path('follow-requests/<int:request_id>/reject/', views.RejectFollowRequestView.as_view(), name='reject-follow-request'),
    path('block/<str:username>/', views.BlockToggleView.as_view(), name='block-toggle'),
    path('block-status/<str:username>/', views.BlockStatusView.as_view(), name='block-status'),
    path('batch-block-status/', views.BatchBlockStatusView.as_view(), name='batch-block-status'),
    path('settings/update/', views.ProfileUpdateView.as_view(), name='profile-update'),
    path('settings/privacy/', views.PrivacySettingsView.as_view(), name='privacy-settings'),
    path('settings/password/', views.PasswordChangeView.as_view(), name='password-change'),
    path('settings/delete-account/', views.AccountDeleteView.as_view(), name='delete-account'),
    path('avatar/upload/', views.AvatarUploadView.as_view(), name='avatar-upload'),
    path('avatar/delete/', views.AvatarDeleteView.as_view(), name='avatar-delete'),
    path('dataset-options/', views.get_dataset_options, name='dataset-options'),
    path('resend-verification-email/', views.ResendVerificationEmailView.as_view(), name='resend-verification-email'),
    path('follow/<str:username>/', views.FollowToggleView.as_view(), name='follow-toggle'),

    # EN SONDA router
    path('', include(router.urls)),
]