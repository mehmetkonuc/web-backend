"""
Şüpheli hesapları temizleme komutu
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from apps.common.security import is_disposable_email, contains_banned_keywords
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Şüpheli hesapları tespit eder ve temizler'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece analiz yap, silme işlemi yapma',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Son kaç gün içindeki hesapları kontrol et (varsayılan: 7)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        
        # Son X gün içinde oluşturulan hesapları al
        cutoff_date = timezone.now() - timedelta(days=days)
        recent_users = User.objects.filter(
            date_joined__gte=cutoff_date,
            is_active=True
        ).exclude(is_staff=True)

        suspicious_users = []
        disposable_email_users = []
        banned_keyword_users = []
        unverified_users = []

        self.stdout.write(f"Son {days} gün içinde {recent_users.count()} kullanıcı kontrol ediliyor...")

        for user in recent_users:
            is_suspicious = False
            reasons = []

            # Disposable email kontrolü
            if is_disposable_email(user.email):
                disposable_email_users.append(user)
                is_suspicious = True
                reasons.append("Disposable email")

            # Yasaklı kelime kontrolü
            if (contains_banned_keywords(user.username) or 
                contains_banned_keywords(user.first_name) or 
                contains_banned_keywords(user.last_name)):
                banned_keyword_users.append(user)
                is_suspicious = True
                reasons.append("Banned keywords")

            # Email doğrulanmamış ve 3 günden eski hesaplar
            if hasattr(user, 'profile'):
                profile = user.profile
                if (not profile.email_verified and 
                    user.date_joined < timezone.now() - timedelta(days=3)):
                    unverified_users.append(user)
                    is_suspicious = True
                    reasons.append("Unverified email > 3 days")

            # Hiç aktivite göstermemiş hesaplar
            if (not hasattr(user, 'posts') and 
                not hasattr(user, 'comments') and
                user.date_joined < timezone.now() - timedelta(days=2)):
                is_suspicious = True
                reasons.append("No activity")

            if is_suspicious:
                suspicious_users.append((user, reasons))

        # Sonuçları yazdır
        self.stdout.write(self.style.WARNING(f"\n=== ŞÜPHELI HESAP ANALİZİ ==="))
        self.stdout.write(f"Disposable email: {len(disposable_email_users)} hesap")
        self.stdout.write(f"Yasaklı kelimeler: {len(banned_keyword_users)} hesap")
        self.stdout.write(f"Doğrulanmamış email: {len(unverified_users)} hesap")
        self.stdout.write(f"Toplam şüpheli: {len(suspicious_users)} hesap")

        if suspicious_users:
            self.stdout.write("\n=== ŞÜPHELI HESAPLAR ===")
            for user, reasons in suspicious_users:
                self.stdout.write(f"- {user.username} ({user.email}) - {', '.join(reasons)}")

        if not dry_run and suspicious_users:
            confirm = input(f"\n{len(suspicious_users)} şüpheli hesabı silmek istiyor musunuz? (y/N): ")
            if confirm.lower() == 'y':
                deleted_count = 0
                for user, reasons in suspicious_users:
                    try:
                        logger.warning(f"Deleting suspicious user: {user.username} ({user.email}) - {reasons}")
                        user.delete()
                        deleted_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Hata: {user.username} silinemedi - {e}")
                        )

                self.stdout.write(
                    self.style.SUCCESS(f"{deleted_count} şüpheli hesap silindi.")
                )
            else:
                self.stdout.write("İşlem iptal edildi.")
        elif dry_run:
            self.stdout.write(self.style.WARNING("\nDry-run modu: Hiçbir hesap silinmedi."))

        self.stdout.write(self.style.SUCCESS("\nAnaliz tamamlandı."))
