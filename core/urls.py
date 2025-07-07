"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# 404 handler import
from apps.guest.views import custom_404_view

# 404 handler tanımlaması
handler404 = custom_404_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.guest.urls')),
    path('profile/', include('apps.profiles.urls')),
    path('members/', include('apps.members.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('chat/', include('apps.chat.urls')),
    path('post/', include('apps.post.urls')),
    path('comment/', include('apps.comment.urls')),
    path('like/', include('apps.like.urls')),
    path('bookmark/', include('apps.bookmark.urls')),

    # REST Framework browsable API
    path('api-auth/', include('rest_framework.urls')),
    
    # JWT Endpoints
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # API Endpoints
    path('api/v1/auth/', include('apps.guest.api.urls')),
    path('api/v1/profiles/', include('apps.profiles.api.urls')),
    path('api/v1/members/', include('apps.members.api.urls')),
    path('api/v1/posts/', include('apps.post.api.urls')),
    path('api/v1/comments/', include('apps.comment.api.urls')),
    path('api/v1/likes/', include('apps.like.api.urls')),
    path('api/v1/bookmark/', include('apps.bookmark.api.urls')),
    path('api/v1/notifications/', include('apps.notifications.api.urls')),
    path('api/v1/chat/', include('apps.chat.api.urls')),
    path('api/v1/push-notifications/', include('apps.push_notifications.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Media dosyaları için URL yapılandırması
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
