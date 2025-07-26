"""
Güvenlik durumunu analiz eden ve reCAPTCHA'yı otomatik aktive eden komut
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from apps.common.security import log_suspicious_activity
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Güvenlik durumunu analiz eder ve reCAPTCHA gerekliliğini değerlendirir'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Son kaç saatlık veriyi analiz et (varsayılan: 1)',
        )
        parser.add_argument(
            '--auto-captcha',
            action='store_true',
            help='Gerekirse reCAPTCHA\'yı otomatik aktive et',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        auto_captcha = options['auto_captcha']
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Son X saatteki metrikler
        recent_registrations = User.objects.filter(
            date_joined__gte=cutoff_time
        ).count()
        
        # Cache'den şüpheli aktiviteleri al
        suspicious_ips = set()
        registration_attempts = 0
        
        # Cache key'lerini kontrol et (gerçek implementasyonda daha sofistike olabilir)
        for i in range(1, 255):
            for j in range(1, 255):
                ip = f"192.168.{i}.{j}"
                cache_key = f"registration_rate_ip_{ip}"
                count = cache.get(cache_key, 0)
                if count > 0:
                    registration_attempts += count
                    if count >= 3:  # Rate limit'e takılan IP'ler
                        suspicious_ips.add(ip)
        
        # Security log dosyasından şüpheli aktiviteleri say
        security_incidents = 0
        try:
            with open('logs/security.log', 'r') as f:
                for line in f:
                    if cutoff_time.strftime('%Y-%m-%d %H') in line:
                        security_incidents += 1
        except FileNotFoundError:
            pass
        
        # Analiz sonuçları
        self.stdout.write(f"\n=== GÜVENLİK ANALİZİ (Son {hours} saat) ===")
        self.stdout.write(f"📊 Toplam kayıt: {recent_registrations}")
        self.stdout.write(f"🚨 Kayıt denemesi: {registration_attempts}")
        self.stdout.write(f"⚠️  Şüpheli IP: {len(suspicious_ips)}")
        self.stdout.write(f"🔒 Güvenlik olayı: {security_incidents}")
        
        # Risk seviyesi hesapla
        risk_score = 0
        
        if recent_registrations > 10:  # Saatte 10'dan fazla kayıt
            risk_score += 2
            self.stdout.write("⚠️  Yüksek kayıt aktivitesi tespit edildi")
        
        if len(suspicious_ips) > 3:  # 3'ten fazla şüpheli IP
            risk_score += 3
            self.stdout.write("🚨 Çoklu şüpheli IP tespit edildi")
        
        if security_incidents > 5:  # 5'ten fazla güvenlik olayı
            risk_score += 2
            self.stdout.write("🔒 Yüksek güvenlik aktivitesi")
        
        if registration_attempts > recent_registrations * 2:  # Başarısız/başarılı oran yüksek
            risk_score += 2
            self.stdout.write("⚠️  Yüksek başarısız kayıt oranı")
        
        # Risk değerlendirmesi
        if risk_score == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ GÜVENLİK DURUMU: NORMAL"))
            self.stdout.write("Mevcut güvenlik önlemleri yeterli")
            recommendation = "reCAPTCHA gerekli değil"
        elif risk_score <= 3:
            self.stdout.write(self.style.WARNING("\n⚠️  GÜVENLİK DURUMU: DİKKAT"))
            self.stdout.write("Artan şüpheli aktivite tespit edildi")
            recommendation = "reCAPTCHA aktive etmeyi düşünün"
        else:
            self.stdout.write(self.style.ERROR("\n🚨 GÜVENLİK DURUMU: YÜKSEK RİSK"))
            self.stdout.write("Bot saldırısı olabilir!")
            recommendation = "reCAPTCHA'yı hemen aktive edin"
        
        self.stdout.write(f"\n💡 ÖNERİ: {recommendation}")
        
        # Otomatik reCAPTCHA aktivasyonu
        if auto_captcha and risk_score > 3:
            # Buraya reCAPTCHA'yı aktive eden kod eklenebilir
            # Örneğin: environment variable değiştirme veya cache'e flag koyma
            cache.set('auto_recaptcha_required', True, 3600)  # 1 saat
            
            self.stdout.write(self.style.SUCCESS("\n🛡️  reCAPTCHA otomatik olarak aktive edildi (1 saat)"))
            
            # Security log'a kaydet
            log_suspicious_activity(
                ip_address='system',
                email='',
                reason=f"Auto-activated reCAPTCHA due to high risk score: {risk_score}",
                additional_data={
                    'registrations': recent_registrations,
                    'suspicious_ips': len(suspicious_ips),
                    'security_incidents': security_incidents
                }
            )
        
        # Detaylı öneriler
        self.stdout.write("\n📋 DETAYLI ÖNERİLER:")
        
        if recent_registrations > 20:
            self.stdout.write("• Rate limiting'i 3/h'den 2/h'ye düşürün")
        
        if len(suspicious_ips) > 5:
            self.stdout.write("• Şüpheli IP'leri geçici olarak engelleyin")
            for ip in list(suspicious_ips)[:5]:  # İlk 5'ini göster
                self.stdout.write(f"  - {ip}")
        
        if security_incidents > 10:
            self.stdout.write("• Honeypot field'ları artırın")
            self.stdout.write("• Email domain kara listesini güncelleyin")
        
        self.stdout.write("\n📊 Monitoring komutları:")
        self.stdout.write("• Şüpheli hesaplar: python manage.py clean_suspicious_accounts --dry-run")
        self.stdout.write("• Security log: tail -f logs/security.log")
        self.stdout.write("• Cache durumu: python manage.py shell -c \"from django.core.cache import cache; print(cache.get('auto_recaptcha_required'))\"")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Analiz tamamlandı. Risk skoru: {risk_score}/9"))
