# Güvenlik Önlemleri Kılavuzu

Bu dokümanda Django projenize eklenen güvenlik önlemleri açıklanmaktadır.

## 🚀 Hızlı Kurulum

### 1. Gerekli Paketler
```bash
pip install django-ratelimit django-recaptcha
```

### 2. Environment Variables (.env dosyası)
```env
# Güvenlik
JWT_SECRET_KEY=your-super-secret-jwt-key-here
RECAPTCHA_PUBLIC_KEY=your-recaptcha-public-key
RECAPTCHA_PRIVATE_KEY=your-recaptcha-private-key

# Rate Limiting için Redis (opsiyonel)
CACHE_BACKEND=django_redis.cache.RedisCache
CACHE_LOCATION=redis://127.0.0.1:6379/1

# Güvenlik ayarları
BLOCKED_IPS=malicious.ip.address,another.bad.ip
ALLOWED_IPS=trusted.ip.address
MINIMUM_ACCOUNT_AGE_HOURS=24
```

## 🛡️ Aktif Güvenlik Önlemleri

### 1. Rate Limiting
- **Kayıt**: IP başına saatte 3 kayıt
- **Giriş**: IP başına saatte 10 giriş
- **Post Oluşturma**: 5 dakikada 5 post (30 dakika block)
- **Yorum Yapma**: 5 dakikada 10 yorum (15 dakika block)
- **Like/Unlike**: 5 dakikada 50 işlem (10 dakika block)
- **Genel API**: 5 dakikada 30 request (15 dakika block)
- **Web Forms**: 5 dakikada 20 form (20 dakika block)

### 2. Email Güvenliği
- Disposable email adresleri engellenir
- Şüpheli email domain'leri kontrol edilir
- Üniversite email'leri (.edu.tr) desteklenir

### 3. Input Validation
- Honeypot field'ları (bot detection)
- Yasaklı kelime filtreleri
- Username pattern kontrolü
- Çok benzer kullanıcı adı tespiti

### 4. Content Spam Protection
- **Yeni Hesaplar**: 24 saatten yeni hesaplar günde max 3 içerik
- **Global POST Protection**: Tüm modüllerde otomatik koruma
- **Smart Blocking**: Path bazında farklı limitler

### 5. Monitoring & Logging
- Şüpheli aktiviteler loglanır
- Security.log dosyasında detaylı izleme
- IP bazlı takip
- Failed login attempt'ler kaydedilir

### 6. Session Security
- Şifreler session'da saklanmaz
- Hassas veriler temizlenir
- JWT token güvenliği

## 📊 Monitoring

### Rate Limit Monitoring
```bash
# Rate limit durumunu kontrol et
python manage.py rate_limit_monitor

# Tüm rate limit'leri temizle
python manage.py rate_limit_monitor --clear

# Belirli IP'yi unblock et
python manage.py rate_limit_monitor --unblock-ip 192.168.1.100
```

### Güvenlik Logları
```bash
tail -f logs/security.log
```

### Şüpheli Hesap Analizi
```bash
python manage.py clean_suspicious_accounts --dry-run
python manage.py clean_suspicious_accounts --days=7
```

## 🔧 Manuel Kontroller

### 1. Disposable Email Kontrolü
```python
from apps.common.security import is_disposable_email
is_disposable_email("test@tempmail.org")  # True
```

### 2. Rate Limit Kontrolü
```python
from apps.common.security import check_registration_rate_limit
allowed, error = check_registration_rate_limit("192.168.1.1", "user@example.com")
```

### 3. Güvenlik Validasyonu
```python
from apps.common.security import validate_registration_data
errors = validate_registration_data(form_data, ip_address)
```

## 📈 İstatistikler

### Log Analizi
```bash
# Bugünkü şüpheli aktiviteler
grep "$(date +%Y-%m-%d)" logs/security.log | wc -l

# En çok şüpheli aktivite gösteren IP'ler
grep "IP=" logs/security.log | sed 's/.*IP=\([^ ]*\).*/\1/' | sort | uniq -c | sort -nr | head -10

# Disposable email denemeleri
grep "disposable email" logs/security.log | wc -l
```

### Database Sorguları
```python
# Son 24 saatteki kayıtlar
from django.utils import timezone
from datetime import timedelta
recent_users = User.objects.filter(
    date_joined__gte=timezone.now() - timedelta(hours=24)
).count()

# Doğrulanmamış hesaplar
unverified = User.objects.filter(
    profile__email_verified=False,
    date_joined__lt=timezone.now() - timedelta(days=3)
).count()
```

## 🚨 Alarm Sistemleri

### Critical Alerts
- 1 saatte 10'dan fazla başarısız kayıt denemesi
- Aynı IP'den 50'den fazla request
- Honeypot field doldurulması

### Günlük Kontroller
```bash
# Cron job ekleyin
0 9 * * * cd /path/to/project && python manage.py clean_suspicious_accounts --dry-run --days=1
```

## 🔒 Ek Güvenlik Önerileri

### 1. Web Server Level
```nginx
# Nginx rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;

# IP blocking
deny 192.168.1.100;
allow 192.168.1.0/24;
deny all;
```

### 2. Database Level
```sql
-- PostgreSQL: Şüpheli aktiviteleri izle
CREATE OR REPLACE FUNCTION log_user_creation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO security_log (action, user_id, ip_address, created_at)
    VALUES ('user_created', NEW.id, NEW.last_login_ip, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_creation_trigger
    AFTER INSERT ON auth_user
    FOR EACH ROW
    EXECUTE FUNCTION log_user_creation();
```

### 3. Environment Variables
```env
# Production'da mutlaka değiştirin
SECRET_KEY=your-real-secret-key
JWT_SECRET_KEY=different-from-django-secret
DEBUG=False

# SSL/HTTPS
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 📞 Sorun Giderme

### Rate Limit Sorunları
```python
# Cache temizleme
from django.core.cache import cache
cache.delete("registration_rate_ip_192.168.1.1")
```

### Log Dosyası Büyüyürse
```bash
# Log rotation
logrotate -f /etc/logrotate.d/django-security
```

### False Positive'ler
```python
# Güvenilir IP'leri whitelist'e ekle
ALLOWED_IPS = ['192.168.1.100', '10.0.0.1']
```

## 🔄 Güncellemeler

Bu güvenlik sistemi sürekli geliştirilmektedir. Yeni tehditler tespit edildikçe:

1. `apps/common/security.py` dosyası güncellenir
2. Yeni kara liste domain'leri eklenir
3. Rate limit değerleri ayarlanır
4. Yeni detection algoritmaları eklenir

**Son Güncelleme**: 21 Temmuz 2025
