from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'likes', views.LikeViewSet, basename='like')

urlpatterns = [
    path('', include(router.urls)),
    path('content-types/', views.get_content_types, name='content-types'),
]