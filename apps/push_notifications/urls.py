from django.urls import path, include

urlpatterns = [
    path('', include('apps.push_notifications.api.urls')),
]
