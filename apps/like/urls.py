from django.urls import path
from . import views

app_name = 'like'

urlpatterns = [
    path('like/', views.like_object, name='like_object'),
    path('status/', views.get_like_status, name='get_like_status'),
]