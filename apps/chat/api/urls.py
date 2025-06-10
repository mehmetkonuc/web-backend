from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, MessageViewSet, UserSearchAPIView

# Create a router for ChatRoom
router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet, basename='chat-room')

# Define URL patterns
urlpatterns = [
    # User search for starting conversations
    path('users/search/', UserSearchAPIView.as_view(), name='user-search'),
    
    # Messages API - manually defined without nested router
    path('rooms/<int:chat_room_pk>/messages/', MessageViewSet.as_view({'get': 'list', 'post': 'create'}), name='chat-messages-list'),
    path('rooms/<int:chat_room_pk>/messages/<int:pk>/', MessageViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='chat-messages-detail'),
    path('rooms/<int:chat_room_pk>/messages/<int:pk>/mark_as_read/', MessageViewSet.as_view({'post': 'mark_as_read'}), name='chat-messages-mark-read'),
    
    # Router URLs for chat rooms
    path('', include(router.urls)),
]
