from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from .models import Bookmark

# Create your views here.

@login_required
def bookmark_object(request):
    """
    Generic view to bookmark any content object
    Returns JSON response with bookmark status
    """
    if request.method == 'POST':
        print('girdi')
        app_name = request.POST.get('app_name')
        model_name = request.POST.get('model_name')
        object_id = request.POST.get('object_id')
        
        if not all([app_name, model_name, object_id]):
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields'
            }, status=400)
        
        try:
            content_type = ContentType.objects.get(app_label=app_name, model=model_name.lower())
            content_object = content_type.model_class().objects.get(id=object_id)
            
            # Toggle bookmark status using the model method
            is_bookmarked, created = Bookmark.toggle_bookmark(request.user, content_object)
            
            # Get updated bookmark count
            bookmark_count = Bookmark.objects.filter(
                content_type=content_type,
                object_id=object_id
            ).count()
            
            if is_bookmarked:
                message = 'İçerik kaydedildi'
            else:
                message = 'İçerik kaydedilenlerden çıkarıldı'
            
            return JsonResponse({
                'status': 'success',
                'is_bookmarked': is_bookmarked,
                'bookmark_count': bookmark_count,
                'message': message
            })
            
        except (ContentType.DoesNotExist, Exception) as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required
def get_bookmark_status(request):
    """
    Check if user has bookmarked an object and get total bookmark count
    Returns JSON with bookmark status and count
    """
    app_name = request.GET.get('app_name')
    model_name = request.GET.get('model_name')
    object_id = request.GET.get('object_id')
    
    if not all([app_name, model_name, object_id]):
        return JsonResponse({
            'status': 'error',
            'message': 'Missing required fields'
        }, status=400)
    
    try:
        content_type = ContentType.objects.get(app_label=app_name, model=model_name.lower())
        
        # Check if user has bookmarked this object using the model method
        content_object = content_type.model_class().objects.get(id=object_id)
        is_bookmarked = Bookmark.is_bookmarked(request.user, content_object)
        
        # Get total bookmark count
        bookmark_count = Bookmark.objects.filter(
            content_type=content_type,
            object_id=object_id
        ).count()
        
        return JsonResponse({
            'status': 'success',
            'is_bookmarked': is_bookmarked,
            'bookmark_count': bookmark_count
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
def user_bookmarks(request):
    """
    View to display all bookmarks for the current user
    """
    bookmarks = Bookmark.objects.filter(user=request.user).select_related('content_type')
    
    return render(request, 'bookmark/user_bookmarks.html', {
        'bookmarks': bookmarks
    })
