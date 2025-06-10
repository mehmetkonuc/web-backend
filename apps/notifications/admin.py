from django.contrib import admin
from .models import Notification, NotificationType

class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description', 'icon_class')
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'sender', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('title', 'text', 'recipient__username', 'sender__username')
    raw_id_fields = ('recipient', 'sender')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

admin.site.register(NotificationType, NotificationTypeAdmin)
admin.site.register(Notification, NotificationAdmin)
