from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from .models import Like

# Create your views here.

@login_required
def like_object(request):
    """
    Generic view to like any content object
    Returns JSON response with like status
    """
    if request.method == 'POST':
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
            
            # Check if already liked
            like_exists = Like.objects.filter(
                user=request.user,
                content_type=content_type,
                object_id=object_id
            ).exists()
            
            if like_exists:
                # Unlike: Remove the like
                Like.objects.filter(
                    user=request.user,
                    content_type=content_type,
                    object_id=object_id
                ).delete()
                liked = False
                message = 'Beğeni kaldırıldı'
            else:
                # Like: Create the like
                Like.objects.create(
                    user=request.user,
                    content_type=content_type,
                    object_id=object_id
                )
                liked = True
                message = 'Beğenildi'
            
            # Get updated like count
            like_count = Like.objects.filter(
                content_type=content_type,
                object_id=object_id
            ).count()
            
            return JsonResponse({
                'status': 'success',
                'liked': liked,
                'like_count': like_count,
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
def get_like_status(request):
    """
    Check if user has liked an object and get total like count
    Returns JSON with like status and count
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
        
        # Check if user has liked this object
        liked = Like.objects.filter(
            user=request.user,
            content_type=content_type,
            object_id=object_id
        ).exists()
        
        # Get total like count
        like_count = Like.objects.filter(
            content_type=content_type,
            object_id=object_id
        ).count()
        
        return JsonResponse({
            'status': 'success',
            'liked': liked,
            'like_count': like_count
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
