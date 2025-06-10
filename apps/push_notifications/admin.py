from django.contrib import admin
from .models import PushToken


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'device_name')
    search_fields = ('user__username', 'user__email', 'expo_token', 'device_name')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Kullanıcı Bilgileri', {
            'fields': ('user', 'device_name')
        }),
        ('Token Bilgileri', {
            'fields': ('expo_token', 'is_active')
        }),
        ('Tarih Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
