from django.contrib import admin
from .models import Comment, CommentImage


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_object', 'created_at', 'is_active']
    list_filter = ['created_at', 'is_active']
    search_fields = ['body', 'user__username']
    date_hierarchy = 'created_at'
    raw_id_fields = ['user', 'parent']
    list_editable = ['is_active']

@admin.register(CommentImage)
class CommentImageAdmin(admin.ModelAdmin):
    list_display = ('comment', 'order', 'image')