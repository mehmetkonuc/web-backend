from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # Genel chat listesi ve header bilgileri için
    path('ws/chat/', consumers.ChatConsumer.as_asgi()),
    
    # Belirli bir chat odası için
    path('ws/chat/<int:room_id>/', consumers.ChatConsumer.as_asgi()),
]