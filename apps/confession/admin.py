from django.contrib import admin
from .models import ConfessionCategory, ConfessionModel, ConfessionImage, ConfessionFilter

@admin.register(ConfessionCategory)
class ConfessionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'confession_count', 'created_at']
    search_fields = ['name']
    readonly_fields = ['confession_count', 'created_at']
    
    def confession_count(self, obj):
        return obj.confessions.count()
    confession_count.short_description = 'İtiraf Sayısı'

class ConfessionImageInline(admin.TabularInline):
    model = ConfessionImage
    extra = 0
    readonly_fields = ['thumbnail_preview', 'original_width', 'original_height', 'file_size', 'format', 'hash', 'processed']
    fields = ['image', 'thumbnail_preview', 'order', 'processed', 'original_width', 'original_height', 'file_size', 'format']
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return f'<img src="{obj.thumbnail.url}" width="50" height="50" style="object-fit: cover;" />'
        return 'No image'
    thumbnail_preview.allow_tags = True
    thumbnail_preview.short_description = 'Önizleme'

@admin.register(ConfessionModel)
class ConfessionModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'category', 'university', 'content_preview', 'is_privacy', 'is_active', 'like_count', 'comment_count', 'created_at']
    list_filter = ['category', 'university', 'is_privacy', 'is_active', 'created_at']
    search_fields = ['content', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['like_count', 'comment_count', 'created_at', 'updated_at']
    inlines = [ConfessionImageInline]
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('user', 'category', 'university', 'content')
        }),
        ('Gizlilik ve Durum', {
            'fields': ('is_privacy', 'is_active')
        }),
        ('İstatistikler', {
            'fields': ('like_count', 'comment_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'İçerik Önizleme'
    
    def like_count(self, obj):
        return obj.likes.count()
    like_count.short_description = 'Beğeni Sayısı'
    
    def comment_count(self, obj):
        return obj.comments.count()
    comment_count.short_description = 'Yorum Sayısı'

@admin.register(ConfessionImage)
class ConfessionImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'confession', 'thumbnail_preview', 'order', 'processed', 'file_size', 'format', 'created_at']
    list_filter = ['processed', 'format', 'created_at']
    search_fields = ['confession__content', 'confession__user__username']
    readonly_fields = ['thumbnail_preview', 'original_width', 'original_height', 'file_size', 'format', 'hash', 'processed']
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return f'<img src="{obj.thumbnail.url}" width="100" height="100" style="object-fit: cover;" />'
        return 'No image'
    thumbnail_preview.allow_tags = True
    thumbnail_preview.short_description = 'Önizleme'

@admin.register(ConfessionFilter)
class ConfessionFilterAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'university', 'sort_by', 'last_used']
    list_filter = ['category', 'university', 'sort_by', 'last_used']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['last_used']
