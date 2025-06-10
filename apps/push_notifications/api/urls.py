from django.urls import path
from . import views

urlpatterns = [
    # Push token yönetimi
    path('register-token/', views.register_push_token, name='register_push_token'),
    path('get-token/', views.get_user_push_token, name='get_user_push_token'),
    path('delete-token/', views.delete_push_token, name='delete_push_token'),
    
    # Test endpoint'leri
    path('send-test-notification/', views.send_test_notification, name='send_test_notification'),
    path('send-test-chat/', views.send_test_chat_notification, name='send_test_chat_notification'),
    path('test-notification-push/', views.test_notification_push, name='test_notification_push'),
]
