from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Notification, NotificationType

@login_required
def notification_list(request):
    """Kullanıcının bildirimlerini listeler"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Filtre parametreleri
    notification_type = request.GET.get('type')
    is_read = request.GET.get('is_read')
    
    # Filtrele
    if notification_type:
        notifications = notifications.filter(notification_type__code=notification_type)
    
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        notifications = notifications.filter(is_read=is_read_bool)
    
    # Sayfalandırma
    paginator = Paginator(notifications, 20)  # Her sayfada 20 bildirim
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Bildirim türlerini getir (filtreleme için)
    notification_types = NotificationType.objects.all()
    
    context = {
        'page_obj': page_obj,
        'notification_types': notification_types,
        'current_type': notification_type,
        'current_is_read': is_read,
        'page_title': 'Bildirimler',
    }
    
    return render(request, 'notifications/list.html', context)

@login_required
def notification_detail(request, notification_id):
    """Bildirim detayını gösterir ve okundu olarak işaretler"""
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        recipient=request.user
    )
    
    # Bildirimi okundu olarak işaretle
    notification.mark_as_read()
    
    # Eğer bildirimde URL varsa o sayfaya yönlendir
    if notification.url:
        return redirect(notification.url)
    
    # URL yoksa bildirim detay sayfasını göster
    return render(request, 'notifications/detail.html', {'notification': notification})

@login_required
def mark_as_read(request, notification_id):
    """Belirli bir bildirimi okundu olarak işaretler"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Sadece POST isteği kabul edilir'}, status=405)
    
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        recipient=request.user
    )
    
    notification.mark_as_read()
    
    return JsonResponse({
        'success': True,
        'notification_id': notification.id,
        'is_read': True,
        'read_at': notification.read_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@login_required
def mark_all_as_read(request):
    """Tüm okunmamış bildirimleri okundu olarak işaretler"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Sadece POST isteği kabul edilir'}, status=405)
    
    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    )
    
    count = unread_notifications.count()
    now = timezone.now()
    
    # Toplu güncelleme
    unread_notifications.update(is_read=True, read_at=now)
    
    return JsonResponse({
        'success': True,
        'count': count,
        'message': f'{count} bildirim okundu olarak işaretlendi.'
    })

@login_required
def get_unread_count(request):
    """Okunmamış bildirim sayısını döndürür"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'count': count
    })

@login_required
def notifications_dropdown(request):
    """Bildirim dropdown içeriğini render eder (AJAX için)"""
    # Son 5 bildirimi getir
    notifications = Notification.objects.filter(
        recipient=request.user,
    ).order_by('-created_at')[:5]
    
    # Okunmamış bildirim sayısı
    unread_count = Notification.objects.filter(
        recipient=request.user,
    ).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    
    return render(request, 'notifications/dropdown.html', context)
