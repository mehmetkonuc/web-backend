from django import template
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from apps.post.models import Post
from apps.bookmark.models import Bookmark

register = template.Library()

@register.simple_tag
def get_bookmark_count(obj):
    """
    Returns the number of bookmarks for an object
    Usage: {% get_bookmark_count post %}
    """
    if not obj:
        return 0
        
    content_type = ContentType.objects.get_for_model(obj)
    return Bookmark.objects.filter(content_type=content_type, object_id=obj.id).count()

@register.simple_tag
def is_object_bookmarked(obj, user):
    """
    Checks if a user has bookmarked an object
    Usage: {% is_object_bookmarked post request.user as bookmarked %}
    """
    if not obj or not user or not user.is_authenticated:
        return False
        
    return Bookmark.is_bookmarked(user, obj)

@register.simple_tag
def get_user_bookmarked_posts(user):
    """
    Get all posts that the user has bookmarked.
    Usage: {% get_user_bookmarked_posts user as bookmarked_posts %}
    """
    if not user.is_authenticated:
        return []
    
    # Get content type for posts
    post_content_type = ContentType.objects.get_for_model(Post)
    
    # Get all bookmarks by this user for this content type
    bookmarks = Bookmark.objects.filter(
        content_type=post_content_type,
        user=user
    ).values_list('object_id', flat=True)
    
    # Get the actual posts
    posts = Post.objects.filter(id__in=bookmarks).order_by('-created_at')
    
    return posts

@register.inclusion_tag('bookmark/bookmark_button.html')
def bookmark_button(obj, user):
    """
    Renders a bookmark button for the given object
    Usage: {% bookmark_button post request.user %}
    """
    if not obj or not user or not user.is_authenticated:
        return {
            'show_button': False
        }
    
    content_type = ContentType.objects.get_for_model(obj)
    is_bookmarked = Bookmark.is_bookmarked(user, obj)
    bookmark_count = Bookmark.objects.filter(
        content_type=content_type, 
        object_id=obj.id
    ).count()
    
    return {
        'show_button': True,
        'object': obj,
        'app_label': content_type.app_label,
        'model_name': content_type.model,
        'object_id': obj.id,
        'is_bookmarked': is_bookmarked,
        'bookmark_count': bookmark_count
    }

@register.simple_tag
def get_bookmark_list(user, model_name=None, limit=None):
    """
    Get all bookmarks or bookmarks of a specific model type
    Usage: {% get_bookmark_list request.user as bookmarks %}
    or: {% get_bookmark_list request.user "post" 5 as recent_bookmarked_posts %}
    """
    if not user.is_authenticated:
        return []
    
    bookmarks = Bookmark.objects.filter(user=user)
    
    if model_name:
        # Filter by model type if specified
        bookmarks = bookmarks.filter(
            content_type__model=model_name.lower()
        )
    
    # Apply ordering
    bookmarks = bookmarks.select_related('content_type').order_by('-created_at')
    
    # Apply limit if specified
    if limit and isinstance(limit, int):
        bookmarks = bookmarks[:limit]
        
    return bookmarks
