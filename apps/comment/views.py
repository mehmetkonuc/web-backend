from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from .models import Comment, CommentImage
from apps.notifications.services import NotificationService
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# Create your views here.

@login_required
def create_comment(request, app_name, model_name, object_id):
    """
    Generic view to create a comment for any model
    """
    if request.method == 'POST':
        body = request.POST.get('body')
        parent_id = request.POST.get('parent_id')
        
        if not body:
            messages.error(request, 'Yorum içeriği boş olamaz.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        try:
            content_type = ContentType.objects.get(app_label=app_name, model=model_name.lower())
            content_object = content_type.model_class().objects.get(id=object_id)
            
            # Create the comment
            comment = Comment(
                user=request.user,
                content_type=content_type,
                object_id=object_id,
                body=body
            )

            # If this is a reply to another comment
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)
                comment.parent = parent_comment
                
            comment.save()
            images = request.FILES.getlist('images')

            print(images)
            # Save each image
            for i, image_file in enumerate(images):
                CommentImage.objects.create(
                    comment=comment,
                    image=image_file,
                    order=i
                )
            messages.success(request, 'Yorumunuz başarıyla eklendi.')
            
            # Bildirim gönderme işlemleri
            # Eğer bu bir yanıt ise, orijinal yorum sahibine bildirim gönder
            if parent_id and comment.parent and comment.parent.user != request.user:
                NotificationService.create_comment_reply_notification(
                    user=request.user,
                    comment=comment,
                    parent_comment=comment.parent
                )
            # İçerik sahibine bildirim gönder (kullanıcı kendi içeriğine yorum yapmıyorsa)
            elif hasattr(content_object, 'user') and content_object.user != request.user:
                NotificationService.create_comment_notification(
                    user=request.user,
                    comment=comment
                )
            
            # If this is a reply, redirect to the comment detail page
            if parent_id:
                return redirect('comment:comment_detail', comment_id=parent_id)
                
        except Exception as e:
            messages.error(request, f'Bir hata oluştu: {str(e)}')
        
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    return redirect('/')

@login_required
def delete_comment(request, comment_id):
    """
    Delete a comment
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Security check - only comment owner can delete
    if request.user != comment.user:
        messages.error(request, 'Bu yorumu silme yetkiniz yok.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    comment.delete()
    messages.success(request, 'Yorum başarıyla silindi.')
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def edit_comment(request, comment_id):
    """
    Edit a comment
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Security check - only comment owner can edit
    if request.user != comment.user:
        messages.error(request, 'Bu yorumu düzenleme yetkiniz yok.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    if request.method == 'POST':
        body = request.POST.get('body')
        
        if not body:
            messages.error(request, 'Yorum içeriği boş olamaz.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        comment.body = body
        comment.save()
        messages.success(request, 'Yorum başarıyla güncellendi.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    
    return redirect('/')


@login_required
def comment_detail(request, comment_id):
    """
    Display a single comment with its replies
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Get the original content object (post, article, etc.)
    content_object = comment.content_object
    # Get all replies to this comment
    all_replies = comment.get_replies()
    
    # Pagination for replies
    replies_per_page = 20  # Sayfa başına gösterilecek yanıt sayısı
    page = request.GET.get('page', 1)
    paginator = Paginator(all_replies, replies_per_page)
    
    try:
        replies = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        replies = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        replies = paginator.page(paginator.num_pages)
    
    # Get the app_name and model_name for the comment form
    app_name = comment.content_type.app_label
    model_name = comment.content_type.model
    
    context = {
        'comment': comment,
        'replies': replies,
        'paginator': paginator,  # Paginator nesnesini de context'e ekledik
        'object': content_object,
        'app_name': app_name,
        'model_name': model_name,
        'page_title' : 'Yorum Detayı',

    }
    
    return render(request, 'comment/comment_detail.html', context)
