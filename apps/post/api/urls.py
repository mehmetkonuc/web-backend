from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'posts', views.PostViewSet, basename='post')
router.register(r'filter-preferences', views.PostFilterPreferencesViewSet, basename='post-filter-preferences')

urlpatterns = [
    path('hashtags/trending/', views.TrendingHashtagView.as_view(), name='trending-hashtags'),
    path('filter-options/', views.FilterOptionsAPIView.as_view(), name='post-filter-options'),
    path('', include(router.urls)),

]