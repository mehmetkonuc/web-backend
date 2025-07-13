from django.urls import path
from . import views

urlpatterns = [
    path('register-token/', views.register_fcm_token, name='register_fcm_token'),
    path('remove-token/', views.remove_fcm_token, name='remove_fcm_token'),
    path('send-test/', views.send_test_notification, name='send_test_notification'),
    path('user-tokens/', views.get_user_tokens, name='get_user_tokens'),
]
