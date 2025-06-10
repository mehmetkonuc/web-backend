from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.comment.models import Comment

register = template.Library()

@register.inclusion_tag('comment/comments.html', takes_context=True)
def render_comments(context, obj, comments_per_page=2):
    """
    Template tag to render comments for any object with infinite scrolling
    Usage: {% render_comments object %} or {% render_comments object 5 %}
    """
    content_type = ContentType.objects.get_for_model(obj)
    all_comments = Comment.objects.filter(
        content_type=content_type,
        object_id=obj.id,
        parent=None,
        is_active=True
    ).order_by('-created_at')  # Tarihe göre sıralama ekledim, modelinize göre ayarlayın
    
    # Pagination
    request = context.get('request')
    page = request.GET.get('page', 1)
    paginator = Paginator(all_comments, comments_per_page)
    
    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        comments = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        comments = paginator.page(paginator.num_pages)
    
    return {
        'comments': comments,
        'paginator': paginator,
        'object': obj,
        'app_name': obj._meta.app_label,
        'model_name': obj._meta.model_name,
        'request': request,
        'comments_per_page': comments_per_page,
        'is_paginated': True  # Sonsuz kaydırma için flag
    }

@register.simple_tag
def get_comment_count(obj):
    """
    Template tag to get the comment count for any object
    Usage: {% get_comment_count object %}
    """
    content_type = ContentType.objects.get_for_model(obj)
    count = Comment.objects.filter(
        content_type=content_type,
        object_id=obj.id,
        is_active=True
    ).count()
    
    return count


@register.inclusion_tag('comment/main_comment.html', takes_context=True)
def main_comment(context, comment_id):
    """
    Template tag to render comments for any object
    Usage: {% main_comment comment_id %}
    """
    comments = Comment.objects.get(
        id=comment_id,
        is_active=True
    )
    request = context.get('request')
    
    return {
        'main_comment': comments,
        'request': request,
    }