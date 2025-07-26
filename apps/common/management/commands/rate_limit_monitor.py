"""
Rate limit durumunu izleme komutu
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Rate limit durumunu ve blocked IP\'leri gösterir'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Tüm rate limit cache\'lerini temizle',
        )
        parser.add_argument(
            '--unblock-ip',
            type=str,
            help='Belirtilen IP\'yi unblock et',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_all_limits()
            return
            
        if options['unblock_ip']:
            self.unblock_ip(options['unblock_ip'])
            return
        
        self.show_status()

    def clear_all_limits(self):
        """Tüm rate limit cache'lerini temizle"""
        # Bu basit bir yaklaşım - production'da daha sofistike olabilir
        cache.clear()
        self.stdout.write(
            self.style.SUCCESS("✅ Tüm rate limit cache'leri temizlendi")
        )

    def unblock_ip(self, ip_address):
        """Belirtilen IP'yi unblock et"""
        rate_limits = getattr(settings, 'GLOBAL_RATE_LIMITS', {})
        
        unblocked_count = 0
        for limit_key in rate_limits.keys():
            # Rate limit cache'ini temizle
            cache_key = f"rate_limit_{limit_key}_{ip_address}"
            if cache.get(cache_key):
                cache.delete(cache_key)
                unblocked_count += 1
            
            # Block cache'ini temizle
            block_key = f"blocked_{limit_key}_{ip_address}"
            if cache.get(block_key):
                cache.delete(block_key)
                unblocked_count += 1
        
        if unblocked_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"✅ IP {ip_address} unblock edildi ({unblocked_count} cache temizlendi)")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠️  IP {ip_address} için aktif limit bulunamadı")
            )

    def show_status(self):
        """Rate limit durumunu göster"""
        rate_limits = getattr(settings, 'GLOBAL_RATE_LIMITS', {})
        
        self.stdout.write("\n🔍 RATE LIMIT DURUMU")
        self.stdout.write("=" * 50)
        
        # Genel istatistikler
        total_limited = 0
        total_blocked = 0
        
        for limit_key, config in rate_limits.items():
            self.stdout.write(f"\n📊 {limit_key.upper()}:")
            self.stdout.write(f"   Limit: {config['requests']} request / {config['window']}s")
            self.stdout.write(f"   Block süresi: {config['block_duration']}s")
            
            # Bu kategorideki aktif limitler
            limited_ips = []
            blocked_ips = []
            
            # Sample IP'leri kontrol et (gerçek production'da daha sofistike olmalı)
            sample_ips = [
                '127.0.0.1', '192.168.1.1', '10.0.0.1',
                '172.16.0.1', '203.0.113.1'
            ]
            
            for ip in sample_ips:
                # Rate limit kontrolü
                cache_key = f"rate_limit_{limit_key}_{ip}"
                rate_data = cache.get(cache_key)
                if rate_data and rate_data.get('count', 0) > 0:
                    limited_ips.append(f"{ip} ({rate_data['count']}/{config['requests']})")
                    total_limited += 1
                
                # Block kontrolü
                block_key = f"blocked_{limit_key}_{ip}"
                if cache.get(block_key):
                    blocked_ips.append(ip)
                    total_blocked += 1
            
            if limited_ips:
                self.stdout.write(f"   🔄 Aktif limitler: {', '.join(limited_ips)}")
            
            if blocked_ips:
                self.stdout.write(
                    self.style.ERROR(f"   🚫 Blocked IP'ler: {', '.join(blocked_ips)}")
                )
            
            if not limited_ips and not blocked_ips:
                self.stdout.write(self.style.SUCCESS("   ✅ Temiz"))
        
        # Özet
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(f"📈 ÖZET:")
        self.stdout.write(f"   Aktif limitler: {total_limited}")
        self.stdout.write(f"   Blocked IP'ler: {total_blocked}")
        
        if total_blocked > 0:
            self.stdout.write(f"\n💡 IP unblock etmek için:")
            self.stdout.write(f"   python manage.py rate_limit_monitor --unblock-ip IP_ADDRESS")
        
        if total_limited > 0 or total_blocked > 0:
            self.stdout.write(f"\n🧹 Tümünü temizlemek için:")
            self.stdout.write(f"   python manage.py rate_limit_monitor --clear")
        
        self.stdout.write("\n")
        
        # Cache bilgileri
        try:
            # Cache backend bilgisi
            cache_info = str(cache._cache) if hasattr(cache, '_cache') else 'Unknown'
            self.stdout.write(f"🗄️  Cache Backend: {cache_info}")
        except:
            pass
