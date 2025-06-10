from django.urls import path
from . import views

app_name = 'post'

urlpatterns = [
    path('', views.PostListView.as_view(), name='post_list'),
    path('<int:pk>/', views.PostDetailView.as_view(), name='post_detail'),
    path('create/', views.create_post, name='create_post'),
    path('<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('trending/', views.TrendingView.as_view(), name='trending'),
    path('hashtag/<str:hashtag>/', views.HashtagPostListView.as_view(), name='hashtag_posts'),
]