from django import template
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from apps.post.models import Post
from apps.like.models import Like

register = template.Library()

@register.simple_tag
def get_like_count(obj):
    """
    Returns the number of likes for an object
    Usage: {% get_like_count post %}
    """
    if not obj:
        return 0
        
    content_type = ContentType.objects.get_for_model(obj)
    return Like.objects.filter(content_type=content_type, object_id=obj.id).count()

@register.simple_tag
def has_user_liked(obj, user):
    """
    Checks if a user has liked an object
    Usage: {% has_user_liked post request.user as liked %}
    """
    if not obj or not user or not user.is_authenticated:
        return False
        
    content_type = ContentType.objects.get_for_model(obj)
    return Like.objects.filter(
        content_type=content_type, 
        object_id=obj.id,
        user=user
    ).exists()

@register.simple_tag
def get_user_liked_posts(user):
    """
    Get all posts that the user has liked.
    Usage: {% get_user_liked_posts user as liked_posts %}
    """
    if not user.is_authenticated:
        return []
    
    # Get content type for posts
    post_content_type = ContentType.objects.get_for_model(Post)
    
    # Get all likes by this user for this content type
    likes = Like.objects.filter(
        content_type=post_content_type,
        user=user
    ).values_list('object_id', flat=True)
    
    # Get the actual posts
    posts = Post.objects.filter(id__in=likes).order_by('-created_at')
    
    return posts

@register.inclusion_tag('like/like_button.html')
def like_button(obj, user):
    """
    Renders a like button for the given object
    Usage: {% like_button post request.user %}
    """
    if not obj or not user or not user.is_authenticated:
        return {
            'show_button': False
        }
    
    content_type = ContentType.objects.get_for_model(obj)
    user_liked = Like.objects.filter(
        content_type=content_type, 
        object_id=obj.id,
        user=user
    ).exists()
    
    like_count = Like.objects.filter(
        content_type=content_type, 
        object_id=obj.id
    ).count()
    
    return {
        'show_button': True,
        'object': obj,
        'app_name': content_type.app_label,
        'model_name': content_type.model,
        'object_id': obj.id,
        'user_liked': user_liked,
        'like_count': like_count
    }