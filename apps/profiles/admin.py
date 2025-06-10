from django.contrib import admin
from .models import Profile, FollowRequest

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'department', 'graduation_status', 'is_verified', 'email_verified')
    list_filter = ('university', 'department', 'graduation_status', 'is_verified', 'email_verified')
    search_fields = ('user__username', 'user__email', 'university__name', 'department__name')
    fieldsets = (
        ('Kullanıcı Bilgileri', {
            'fields': ('user', 'avatar')
        }),
        ('Eğitim Bilgileri', {
            'fields': ('university', 'department', 'graduation_status', 'is_verified', 'email_verified')
        }),
    )

@admin.register(FollowRequest)
class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user',)
