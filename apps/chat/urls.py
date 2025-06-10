from django.urls import path, include
from .views import (
    ChatView, 
    ChatDetailView, 
    MessageListView, 
    ChatDeleteView,
    UserSearchView,
    ChatRoomCreateView,
    upload_attachments
)

app_name = 'chat'

urlpatterns = [
    # Web views
    path('', ChatView.as_view(), name='chat_list'),
    path('<int:chat_room_id>/', ChatDetailView.as_view(), name='chat_detail'),
    
    # Message actions
    path('<int:chat_room_id>/messages/', MessageListView.as_view(), name='message_list'),
    path('<int:chat_room_id>/delete/', ChatDeleteView.as_view(), name='delete_chat'),
    path('upload-attachments/', upload_attachments, name='upload_attachments'),
    
    # User search and chat creation
    path('users/search/', UserSearchView.as_view(), name='user_search'),
    path('rooms/', ChatRoomCreateView.as_view(), name='create_room'),
    
    # API endpoints
    # path('api/', include('apps.chat.api.urls')),
]