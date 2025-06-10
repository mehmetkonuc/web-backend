from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# app_name = "bookmarks"

router = DefaultRouter()
router.register(r'', views.BookmarkViewSet, basename='bookmark')

urlpatterns = [
    path('content-types/', views.get_content_types, name='content-types'),
    path('', include(router.urls)),

]