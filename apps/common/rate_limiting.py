"""
Global Rate Limiting Middleware
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from apps.common.security import log_suspicious_activity
import time
import json


class GlobalRateLimitMiddleware(MiddlewareMixin):
    """
    Tüm POST request'ler için global rate limiting
    """
    
    def process_request(self, request):
        # Sadece POST request'leri kontrol et
        if request.method != 'POST':
            return None
            
        # Admin ve staff kullanıcıları hariç tut
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return None
        
        # Rate limiting ayarlarını al
        rate_limits = getattr(settings, 'GLOBAL_RATE_LIMITS', {})
        
        # API path'ine göre farklı limitler
        path = request.path
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Path kategorilerini belirle
        if path.startswith('/api/guest/') or path.startswith('/api/v1/auth/'):
            # Guest API'ler için özel kurallar (zaten mevcut)
            return None
        elif path.startswith('/api/v1/posts/') or path.startswith('/post/'):
            limit_key = 'post_creation'
        elif path.startswith('/api/v1/comments/') or path.startswith('/comment/'):
            limit_key = 'comment_creation'
        elif path.startswith('/api/v1/likes/') or path.startswith('/like/'):
            limit_key = 'like_action'
        elif path.startswith('/api/v1/confessions/') or path.startswith('/confession/'):
            limit_key = 'confession_creation'
        elif path.startswith('/api/v1/bookmark/'):
            limit_key = 'bookmark_action'
        elif '/api/' in path:
            limit_key = 'general_api'
        else:
            # Web form'lar için
            limit_key = 'web_forms'
        
        # Limit ayarlarını al
        limit_config = rate_limits.get(limit_key, {
            'requests': 10,
            'window': 300,  # 5 dakika
            'block_duration': 900  # 15 dakika block
        })
        
        # Cache key oluştur
        cache_key = f"rate_limit_{limit_key}_{ip_address}"
        
        # Mevcut request sayısını al
        request_data = cache.get(cache_key, {'count': 0, 'first_request': time.time()})
        
        current_time = time.time()
        window_start = request_data['first_request']
        
        # Zaman penceresi kontrolü
        if current_time - window_start > limit_config['window']:
            # Yeni pencere başlat
            request_data = {'count': 1, 'first_request': current_time}
        else:
            # Mevcut pencerede sayacı artır
            request_data['count'] += 1
        
        # Cache'i güncelle
        cache.set(cache_key, request_data, limit_config['window'])
        
        # Limit kontrolü
        if request_data['count'] > limit_config['requests']:
            # Rate limit aşıldı - block süresini ayarla
            block_key = f"blocked_{limit_key}_{ip_address}"
            cache.set(block_key, True, limit_config['block_duration'])
            
            # Şüpheli aktiviteyi logla
            log_suspicious_activity(
                ip_address=ip_address,
                email=getattr(request.user, 'email', '') if hasattr(request, 'user') and request.user.is_authenticated else '',
                reason=f"Rate limit exceeded for {limit_key}",
                additional_data={
                    'path': path,
                    'requests_in_window': request_data['count'],
                    'limit': limit_config['requests'],
                    'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
                }
            )
            
            return JsonResponse({
                'error': 'Çok fazla istek gönderdiniz. Lütfen biraz bekleyip tekrar deneyin.',
                'retry_after': limit_config['block_duration']
            }, status=429)
        
        # Block kontrolü (önceden block edilmiş mi?)
        block_key = f"blocked_{limit_key}_{ip_address}"
        if cache.get(block_key):
            return JsonResponse({
                'error': 'Geçici olarak engellendiniz. Lütfen daha sonra tekrar deneyin.',
                'retry_after': limit_config['block_duration']
            }, status=429)
        
        return None


class ContentSpamMiddleware(MiddlewareMixin):
    """
    İçerik spam'ı için özel kontroller
    """
    
    def process_request(self, request):
        if request.method != 'POST':
            return None
            
        # Content creation endpoint'leri
        content_paths = [
            '/api/v1/posts/',     # API v1 post endpoints
            '/api/v1/comments/',  # API v1 comment endpoints  
            '/api/v1/confessions/', # API v1 confession endpoints
            '/post/',             # Web post endpoints
            '/comment/',          # Web comment endpoints
            '/confession/'        # Web confession endpoints
        ]
        
        if not any(request.path.startswith(path) for path in content_paths):
            return None
        
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        user_id = None
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Yeni hesap kontrolü (24 saatten yeni hesaplar sınırlı)
            account_age = (timezone.now() - request.user.date_joined).total_seconds() / 3600  # hours
            min_account_age = getattr(settings, 'MINIMUM_ACCOUNT_AGE_HOURS', 24)
            
            if account_age < min_account_age:
                # Yeni hesaplar için daha sıkı limitler
                cache_key = f"new_user_content_{user_id}"
                content_count = cache.get(cache_key, 0)
                
                if content_count >= 3:  # Yeni hesaplar günde max 3 içerik
                    log_suspicious_activity(
                        ip_address=ip_address,
                        email=request.user.email,
                        reason="New account excessive content creation",
                        additional_data={'account_age_hours': account_age, 'content_count': content_count}
                    )
                    
                    return JsonResponse({
                        'error': 'Yeni hesaplar günlük içerik paylaşım sınırına ulaştı.',
                        'detail': 'Hesabınız 24 saatten yeni olduğu için sınırlı içerik paylaşabilirsiniz.'
                    }, status=429)
                
                # Sayacı artır (24 saat)
                cache.set(cache_key, content_count + 1, 86400)
        
        return None
