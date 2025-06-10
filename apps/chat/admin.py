from django.contrib import admin
from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'is_active']
    list_filter = ['created_at', 'is_active']
    search_fields = ['participants']
    date_hierarchy = 'created_at'
    list_editable = ['is_active']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_room')