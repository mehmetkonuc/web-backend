"""
Güvenlik için utility fonksiyonları
"""
import re
import requests
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Şüpheli email domain'leri
SUSPICIOUS_EMAIL_DOMAINS = [
    'tempmail.org', 'guerrillamail.com', '10minutemail.com', 'temp-mail.org',
    'mailinator.com', 'throwaway.email', 'getnada.com', 'mohmal.com',
    'sharklasers.com', 'yopmail.com', 'fakemailgenerator.com',
    'tempemailaddress.com', 'trashmail.com', 'dispostable.com'
]

# Yasaklı kelimeler (username, email vb. için)
BANNED_KEYWORDS = [
    'admin', 'test', 'bot', 'spam', 'fake', 'temp', 'trash',
    'kampuslu', 'kampüslü', 'kampus', 'university', 'college'
]


def is_suspicious_email_domain(email):
    """Email domain'i şüpheli mi kontrol eder"""
    domain = email.split('@')[1].lower()
    return domain in SUSPICIOUS_EMAIL_DOMAINS


def is_disposable_email(email):
    """
    Disposable email servisi kontrolü
    Çeşitli API'ler kullanarak kontrol edilebilir
    """
    domain = email.split('@')[1].lower()
    
    # Basit domain kontrolü
    if is_suspicious_email_domain(email):
        return True
    
    # Cache'den kontrol et
    cache_key = f"disposable_email_{domain}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Disposable email API kontrolü (opsiyonel)
    try:
        # Ücretsiz API servisi kullanabilirsiniz
        # response = requests.get(f"https://api.disposable-emails.com/v1/domain/{domain}")
        # is_disposable = response.json().get('disposable', False)
        
        # Şimdilik sadece bilinen domain'leri kontrol edelim
        is_disposable = domain in SUSPICIOUS_EMAIL_DOMAINS
        
        # Sonucu 1 saat cache'le
        cache.set(cache_key, is_disposable, 3600)
        return is_disposable
    except:
        # API hatası durumunda sadece bilinen domain'leri kontrol et
        return domain in SUSPICIOUS_EMAIL_DOMAINS


def contains_banned_keywords(text):
    """Metin yasaklı kelime içeriyor mu kontrol eder"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in BANNED_KEYWORDS)


def is_valid_university_email(email):
    """
    Üniversite email'i mi kontrol eder
    .edu, .edu.tr gibi domain'leri kabul eder
    """
    domain = email.split('@')[1].lower()
    # Üniversite domain pattern'leri
    university_patterns = [
        r'\.edu$',           # .edu
        r'\.edu\.tr$',       # .edu.tr
        r'\.ac\.tr$',        # .ac.tr
        r'\.universities\.', # universities içeren
    ]
    
    return any(re.search(pattern, domain) for pattern in university_patterns)


def check_registration_rate_limit(ip_address, email=None):
    """
    Kayıt hız limitini kontrol eder
    """
    now = timezone.now()
    
    # IP bazlı rate limit (1 saatte en fazla 3 kayıt)
    ip_key = f"registration_rate_ip_{ip_address}"
    ip_count = cache.get(ip_key, 0)
    if ip_count >= 3:
        return False, "Bu IP adresinden çok fazla kayıt denemesi yapıldı. Lütfen 1 saat sonra tekrar deneyin."
    
    # Email bazlı rate limit (eğer email verilmişse)
    if email:
        email_key = f"registration_rate_email_{email}"
        email_count = cache.get(email_key, 0)
        if email_count >= 1:
            return False, "Bu email adresi ile zaten kayıt denenmiş. Lütfen 1 saat sonra tekrar deneyin."
    
    return True, None


def increment_registration_attempt(ip_address, email=None):
    """
    Kayıt denemesi sayacını artırır
    """
    # IP sayacını artır (1 saat)
    ip_key = f"registration_rate_ip_{ip_address}"
    current_count = cache.get(ip_key, 0)
    cache.set(ip_key, current_count + 1, 3600)
    
    # Email sayacını artır (eğer email verilmişse)
    if email:
        email_key = f"registration_rate_email_{email}"
        cache.set(email_key, 1, 3600)


def is_honeypot_filled(honeypot_field):
    """
    Honeypot field dolu mu kontrol eder
    Bot'lar genelde tüm field'ları doldurur
    """
    return bool(honeypot_field and honeypot_field.strip())


def validate_registration_data(data, ip_address):
    """
    Kayıt verilerini toplu olarak güvenlik açısından kontrol eder
    """
    errors = []
    
    email = data.get('email', '')
    username = data.get('username', '')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    honeypot = data.get('website', '')  # Honeypot field
    
    # Dynamic reCAPTCHA kontrolü
    from django.core.cache import cache
    auto_recaptcha = cache.get('auto_recaptcha_required', False)
    if auto_recaptcha and not data.get('recaptcha'):
        errors.append("Güvenlik doğrulaması gerekli. Lütfen reCAPTCHA'yı tamamlayın.")
    
    # Honeypot kontrolü
    if is_honeypot_filled(honeypot):
        errors.append("Spam kayıt tespit edildi.")
    
    # Email kontrolleri
    if is_disposable_email(email):
        errors.append("Geçici email adresleri kabul edilmemektedir.")
    
    # Yasaklı kelime kontrolleri
    if contains_banned_keywords(username):
        errors.append("Kullanıcı adı uygun olmayan kelimeler içeriyor.")
    
    if contains_banned_keywords(first_name) or contains_banned_keywords(last_name):
        errors.append("Ad ve soyad uygun olmayan kelimeler içeriyor.")
    
    # Rate limit kontrolü
    is_allowed, rate_limit_error = check_registration_rate_limit(ip_address, email)
    if not is_allowed:
        errors.append(rate_limit_error)
    
    # Kullanıcı adı pattern kontrolü (sadece harf, rakam, _, - izin ver)
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        errors.append("Kullanıcı adı sadece harf, rakam, alt çizgi ve tire içerebilir.")
    
    # Çok benzer kullanıcı adı kontrolü
    similar_usernames = User.objects.filter(
        username__icontains=username[:5]
    ).count()
    if similar_usernames > 10:  # Çok benzer kullanıcı adı varsa şüpheli
        errors.append("Bu kullanıcı adı çok benzer kayıtlar tespit edildi.")
    
    return errors


def log_suspicious_activity(ip_address, email, reason, additional_data=None):
    """
    Şüpheli aktiviteleri loglar
    """
    logger.warning(f"Şüpheli kayıt aktivitesi: IP={ip_address}, Email={email}, Sebep={reason}, Data={additional_data}")
