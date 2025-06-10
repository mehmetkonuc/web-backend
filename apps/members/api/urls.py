from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import MemberListAPIView, FilterOptionsAPIView, UserFilterPreferencesViewSet

router = DefaultRouter()
router.register(r'filter-preferences', UserFilterPreferencesViewSet, basename='member-filter-preferences')

urlpatterns = [
    path('', MemberListAPIView.as_view(), name='member-list'),
    path('filter-options/', FilterOptionsAPIView.as_view(), name='filter-options'),
    path('', include(router.urls)),
]