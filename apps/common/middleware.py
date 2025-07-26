"""
Güvenlik middleware'leri
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from apps.common.security import log_suspicious_activity
import logging

logger = logging.getLogger('security')


class SecurityMiddleware(MiddlewareMixin):
    """
    Güvenlik kontrolleri için middleware
    """
    
    def process_request(self, request):
        """
        İsteği işlemeden önce güvenlik kontrolleri
        """
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Şüpheli User-Agent'ları kontrol et
        suspicious_user_agents = [
            'python-requests', 'curl', 'wget', 'bot', 'crawler', 
            'spider', 'scraper', 'postman', 'httpie'
        ]
        
        if any(agent.lower() in user_agent.lower() for agent in suspicious_user_agents):
            # API request'lerinde daha esnek ol
            if not request.path.startswith('/api/'):
                log_suspicious_activity(
                    ip_address=ip_address,
                    email='',
                    reason=f"Suspicious User-Agent: {user_agent}",
                    additional_data={'path': request.path, 'method': request.method}
                )
        
        # Çok hızlı request'leri kontrol et (genel rate limiting)
        if request.path.startswith('/api/v1/auth/'):
            cache_key = f"general_rate_limit_{ip_address}"
            request_count = cache.get(cache_key, 0)
            
            if request_count > 50:  # 5 dakikada 50'den fazla request
                log_suspicious_activity(
                    ip_address=ip_address,
                    email='',
                    reason="Excessive requests detected",
                    additional_data={'request_count': request_count, 'path': request.path}
                )
                return JsonResponse({
                    'error': 'Çok fazla istek gönderildi. Lütfen biraz bekleyin.'
                }, status=429)
            
            # Request sayacını artır (5 dakika)
            cache.set(cache_key, request_count + 1, 300)
        
        return None


class HoneypotMiddleware(MiddlewareMixin):
    """
    Bot detection için honeypot middleware
    """
    
    def process_request(self, request):
        """
        Honeypot field'larını kontrol et
        """
        if request.method == 'POST' and request.path.startswith('/api/v1/auth/register'):
            # Form data'sında honeypot field'ını kontrol et
            honeypot_fields = ['website', 'url', 'homepage', 'company']
            
            for field in honeypot_fields:
                if field in request.POST and request.POST[field].strip():
                    ip_address = request.META.get('REMOTE_ADDR', 'unknown')
                    log_suspicious_activity(
                        ip_address=ip_address,
                        email=request.POST.get('email', ''),
                        reason=f"Honeypot field filled: {field}",
                        additional_data={'field_value': request.POST[field][:50]}
                    )
                    
                    return JsonResponse({
                        'error': 'Geçersiz form gönderimi tespit edildi.'
                    }, status=400)
        
        return None
