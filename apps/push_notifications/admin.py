from django.contrib import admin
from .models import FCMToken, NotificationLog


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'device_name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('platform', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__email', 'fcm_token', 'device_name', 'platform')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Kullanıcı Bilgileri', {
            'fields': ('user', 'device_name')
        }),
        ('Token Bilgileri', {
            'fields': ('fcm_token', 'platform', 'device_info', 'is_active')
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Düzenleme modunda
            return list(self.readonly_fields) + ['fcm_token']
        return self.readonly_fields


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'status', 'sent_at')
    list_filter = ('status', 'sent_at')
    search_fields = ('user__username', 'title', 'body')
    readonly_fields = ('sent_at',)
    ordering = ('-sent_at',)
    
    fieldsets = (
        ('Kullanıcı ve Durum', {
            'fields': ('user', 'fcm_token', 'status')
        }),
        ('Bildirim İçeriği', {
            'fields': ('title', 'body', 'data')
        }),
        ('Hata ve Zaman', {
            'fields': ('error_message', 'sent_at')
        }),
    )
