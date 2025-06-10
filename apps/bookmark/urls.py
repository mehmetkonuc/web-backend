from django.urls import path
from . import views

app_name = 'bookmark'

urlpatterns = [
    path('bookmark/', views.bookmark_object, name='bookmark_object'),
    path('status/', views.get_bookmark_status, name='get_bookmark_status'),
    path('my-bookmarks/', views.user_bookmarks, name='user_bookmarks'),
]