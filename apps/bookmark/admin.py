from django.contrib import admin
from .models import Bookmark

class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'created_at')
    list_filter = ('content_type', 'created_at')
    search_fields = ('user__username', 'object_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('content_type', 'object_id')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'content_type')

admin.site.register(Bookmark, BookmarkAdmin)
