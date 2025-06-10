from django.contrib import admin
from .models import Post, PostImage, UserPostFilter

class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1
    max_num = 4

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_content', 'created_at', 'image_count')
    list_filter = ('created_at',)
    search_fields = ('content', 'user__username')
    date_hierarchy = 'created_at'
    inlines = [PostImageInline]
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = 'İçerik'
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Resim Sayısı'

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'order', 'image')
    list_filter = ('post__user',)

@admin.register(UserPostFilter)
class UserPostFilterAdmin(admin.ModelAdmin):
    list_display = ('user', 'posts_type', 'university', 'department')
    list_filter = ('posts_type', 'university', 'department')
    search_fields = ('user__username',)