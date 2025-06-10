from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# app_name = "notifications_api"

router = DefaultRouter()
router.register(r'list', views.NotificationViewSet, basename='notification')
router.register(r'notification-types', views.NotificationTypeViewSet, basename='notification-type')

urlpatterns = [
    path('', include(router.urls)),
]