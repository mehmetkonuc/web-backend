from django.urls import path
from . import views

app_name = 'comment'

urlpatterns = [
    path('create/<str:app_name>/<str:model_name>/<int:object_id>/', views.create_comment, name='create_comment'),
    path('delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('edit/<int:comment_id>/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/', views.comment_detail, name='comment_detail'),
]