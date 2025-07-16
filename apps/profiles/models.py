from django.db import models
from django.contrib.auth.models import User
from apps.dataset.models import University, Department, GraduationStatus
import os
from datetime import datetime
from apps.notifications.services import NotificationService
from django.db.models.signals import post_delete, pre_save, post_save
from django.dispatch import receiver

def avatar_upload_path(instance, filename):
    """Upload path for profile avatars organized by date and user ID"""
    # Hibrit yaklaşım: Tarih bazında ana klasörleme + user ID klasörü + dosyalar
    now = datetime.now()
    user_id = instance.user.id if hasattr(instance, 'user') and instance.user else 'temp'
    
    # Format: avatars/2025/07/15/100/user_100_avatar.webp
    path = os.path.join(
        'avatars',
        str(now.year),
        str(now.month).zfill(2),
        str(now.day).zfill(2),
        str(user_id),
        f'user_{user_id}_{filename}'
    )
    return path

# Create your models here.
class Profile(models.Model):
    # Mesaj gizlilik seçenekleri
    MESSAGE_PRIVACY_CHOICES = [
        ('none', 'Hiç Kimse'),
        ('followers', 'Sadece Takipçilerim'),
        ('everyone', 'Herkes'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Kullanıcı")
    
    # Avatar images - multiple sizes için
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True, max_length=255, verbose_name="Profil Fotoğrafı (Orijinal)")
    avatar_thumbnail = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True, max_length=255, verbose_name="Avatar Thumbnail (150x150)")
    avatar_medium = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True, max_length=255, verbose_name="Avatar Medium (300x300)")
    
    # Avatar metadata
    avatar_processed = models.BooleanField(default=False, verbose_name="Avatar İşlenmiş", help_text="Avatar backend tarafından işlendi mi?")
    
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Üniversite")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bölüm")
    graduation_status = models.ForeignKey(GraduationStatus, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mezuniyet Durumu")
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True, verbose_name="Takip Edilenler")
    blocked = models.ManyToManyField('self', symmetrical=False, related_name='blocked_by', blank=True, verbose_name="Engellenenler")
    is_private = models.BooleanField(default=False, verbose_name="Gizli Profil")
    is_verified = models.BooleanField(default=False, verbose_name="Doğrulanmış Hesap")
    bio = models.TextField(max_length=400, blank=True, null=True, verbose_name="Hakkında")
    message_privacy = models.CharField(
        max_length=10, 
        choices=MESSAGE_PRIVACY_CHOICES, 
        default='everyone', 
        verbose_name="Mesaj Gizliliği"
    )
    email_verified = models.BooleanField(default=False, verbose_name="E-posta Doğrulandı")
    email_verification_token = models.UUIDField(null=True, blank=True, verbose_name="E-posta Doğrulama Kodu")
    email_verification_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="E-posta Doğrulama Gönderim Zamanı")

    def __str__(self):
        return self.user.username

    def follow(self, profile):
        """Belirtilen profili takip et"""
        if self != profile and profile not in self.following.all():
            # Engellediğimiz veya bizi engellemiş kişiyi takip edemeyiz
            if self.is_blocked(profile) or self.is_blocked_by(profile):
                return False
                
            # Hedef profil gizli ise, takip yerine takip isteği gönder
            if profile.is_private:
                # Zaten bir istek varsa tekrar gönderme
                if FollowRequest.objects.filter(from_user=self, to_user=profile, status='pending').exists():
                    return False
                
                # Yeni takip isteği oluştur
                follow_request = FollowRequest.objects.create(from_user=self, to_user=profile)

                # Takip isteği bildirimi gönder
                try:
                    NotificationService.create_follow_request_notification(self.user, profile.user)
                except Exception as e:
                    print(f"Takip isteği bildirimi gönderilemedi: {e}")
                
                return "requested"
            
            # Normal takip (profil gizli değilse)
            self.following.add(profile)
            
            # Takip bildirimi gönder
            try:
                NotificationService.create_follow_notification(self.user, profile.user)
            except Exception as e:
                print(f"Takip bildirimi gönderilemedi: {e}")
                
            return True
        return False
        
    def unfollow(self, profile):
        """Belirtilen profili takipten çık"""
        if profile in self.following.all():
            self.following.remove(profile)
            
            # İlişkili takip bildirimlerini sil
            try:
                # Yeni servis sınıfı ile silme işlemi
                NotificationService.delete_notification(
                    sender=self.user,
                    recipient=profile.user,
                    code="follow"
                )
                
                NotificationService.delete_notification(
                    sender=profile.user,
                    recipient=self.user,
                    code="follow_accepted"
                )
            except Exception as e:
                print(f"Bildirimleri silerken hata: {e}")
            
            # Takip isteği kayıtlarını tamamen sil (reddedilen dahil)
            try:
                # Kullanıcının gönderdiği istekleri sil
                FollowRequest.objects.filter(
                    from_user=self, 
                    to_user=profile
                ).delete()
                
                # Kullanıcının aldığı istekleri sil
                FollowRequest.objects.filter(
                    from_user=profile, 
                    to_user=self
                ).delete()
                
            except Exception as e:
                print(f"Takip isteklerini silerken hata: {e}")
            
            return True
        return False
        
    def is_following(self, profile):
        """Belirtilen profili takip ediyor mu?"""
        return profile in self.following.all()
        
    def has_pending_follow_request(self, profile):
        """Belirtilen profile bekleyen takip isteği var mı?"""
        return FollowRequest.objects.filter(
            from_user=self, 
            to_user=profile, 
            status='pending'
        ).exists()
        
    def get_following_count(self):
        """Takip edilen kişi sayısı"""
        return self.following.count()
        
    def get_followers_count(self):
        """Takipçi sayısı"""
        return self.followers.count()
        
    def get_pending_follow_requests(self):
        """Kullanıcının aldığı bekleyen takip istekleri"""
        return FollowRequest.objects.filter(to_user=self, status='pending')
        
    def get_pending_follow_requests_count(self):
        """Kullanıcının aldığı bekleyen takip istekleri sayısı"""
        return self.get_pending_follow_requests().count()
        
    def block(self, profile):
        """Belirtilen profili engelle"""
        if self != profile and profile not in self.blocked.all():
            # Engellenecek kişiyi önce takipten çıkar
            if self.is_following(profile):
                self.unfollow(profile)
            # Engellenen kişi bizi takip ediyorsa, onu takipçilerden çıkar
            if profile.is_following(self):
                profile.unfollow(self)
            
            # İki yönlü takip bildirimlerini temizle
            try:
                # Kullanıcının gönderdiği takip bildirimleri
                NotificationService.delete_notification(
                    sender=self.user,
                    recipient=profile.user,
                    code="follow"
                )
                
                NotificationService.delete_notification(
                    sender=self.user,
                    recipient=profile.user,
                    code="follow_request"
                )
                
                # Kullanıcının aldığı takip bildirimleri
                NotificationService.delete_notification(
                    sender=profile.user,
                    recipient=self.user,
                    code="follow"
                )
                
                NotificationService.delete_notification(
                    sender=profile.user,
                    recipient=self.user,
                    code="follow_request"
                )
                
                NotificationService.delete_notification(
                    sender=profile.user,
                    recipient=self.user,
                    code="follow_accepted"
                )
            except Exception as e:
                print(f"Bildirimleri silerken hata: {e}")
            
            # Bekleyen takip isteklerini iptal et
            FollowRequest.objects.filter(from_user=self, to_user=profile).update(status='rejected')
            FollowRequest.objects.filter(from_user=profile, to_user=self).update(status='rejected')
            
            self.blocked.add(profile)
            return True
        return False
        
    def unblock(self, profile):
        """Belirtilen profilin engelini kaldır"""
        if profile in self.blocked.all():
            self.blocked.remove(profile)
            return True
        return False
    
    def is_blocked(self, profile):
        """Belirtilen profil engellenmiş mi?"""
        return profile in self.blocked.all()
    
    def is_blocked_by(self, profile):
        """Belirtilen profil tarafından engellenmiş mi?"""
        return self in profile.blocked.all()
    
    def can_receive_message_from(self, sender_profile):
        """Belirtilen profilin kullanıcı mesaj gönderebilir mi?"""
        # Kullanıcı kendisine her zaman mesaj gönderebilir
        if self == sender_profile:
            return True
        
        # Kullanıcı engellenmişse mesaj gönderemez
        if self.is_blocked(sender_profile) or self.is_blocked_by(sender_profile):
            return False
            
        # Mesaj gizlilik kontrolü
        if self.message_privacy == 'none':
            return False
        elif self.message_privacy == 'followers':
            # Sadece takipçilere mesaj izni
            return sender_profile in self.followers.all()
        else:  # 'everyone'
            return True
    
    def get_avatar_url(self, size='medium'):
        """
        En uygun avatar URL'ini döndür.
        
        Args:
            size: 'thumbnail', 'medium', 'original'
        """
        if size == 'thumbnail' and self.avatar_thumbnail:
            return self.avatar_thumbnail.url
        elif size == 'medium' and self.avatar_medium:
            return self.avatar_medium.url
        elif size == 'original' and self.avatar:
            return self.avatar.url
        else:
            # Fallback: En yakın boyutu döndür
            if self.avatar_medium:
                return self.avatar_medium.url
            elif self.avatar_thumbnail:
                return self.avatar_thumbnail.url
            elif self.avatar:
                return self.avatar.url
            return None
    
    def get_all_avatar_sizes(self):
        """Mevcut tüm avatar boyutlarını döndür"""
        sizes = {}
        if self.avatar_thumbnail:
            sizes['thumbnail'] = self.avatar_thumbnail.url
        if self.avatar_medium:
            sizes['medium'] = self.avatar_medium.url
        if self.avatar:
            sizes['original'] = self.avatar.url
        return sizes
    
    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"



class FollowRequest(models.Model):
    """Takip isteği modeli"""
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('accepted', 'Kabul Edildi'),
        ('rejected', 'Reddedildi'),
    ]
    
    from_user = models.ForeignKey(Profile, related_name='sent_follow_requests', on_delete=models.CASCADE, verbose_name="İsteği Gönderen")
    to_user = models.ForeignKey(Profile, related_name='received_follow_requests', on_delete=models.CASCADE, verbose_name="İsteği Alan")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Durum")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Zamanı")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Zamanı")
    
    def accept(self):
        """Takip isteğini kabul et"""
        if self.status == 'pending':
            # Durumu güncelle
            self.status = 'accepted'
            self.save()
            
            # Takipçi ilişkisini kur
            self.to_user.followers.add(self.from_user)
            
            # Takip bildirimini sil ve yerine kabul edildi bildirimi gönder
            try:
                # Eski takip isteği bildirimini sil
                NotificationService.delete_notification(
                    sender=self.from_user.user,
                    recipient=self.to_user.user,
                    code="follow_request"
                )
                
                # Kabul edildi bildirimi gönder
                NotificationService.create_follow_accepted_notification(
                    self.to_user.user, 
                    self.from_user.user
                )
            except Exception as e:
                print(f"Takip kabul bildirimi gönderilemedi: {e}")
                
            return True
        return False
    
    def reject(self):
        """Takip isteğini reddet"""
        if self.status == 'pending':
            # Takip isteği bildirimini sil
            try:
                NotificationService.delete_notification(
                    sender=self.from_user.user,
                    recipient=self.to_user.user,
                    code="follow_request"
                )
            except Exception as e:
                print(f"Bildirim silinirken hata: {e}")
            
            # İsteği tamamen sil - durumu güncellemek yerine veritabanından kaldır
            # Böylece aynı kullanıcı tekrar istek gönderebilir
            self.delete()
            
            return True
        return False
    
    def cancel(self):
        """Takip isteğini iptal et (gönderen tarafından)"""
        if self.status == 'pending':
            # Takip isteği bildirimini sil
            try:
                NotificationService.delete_notification(
                    sender=self.from_user.user,
                    recipient=self.to_user.user,
                    code="follow_request"
                )
            except Exception as e:
                print(f"Bildirim silinirken hata: {e}")
            
            # İsteği tamamen sil
            self.delete()
            
            return True
        return False
    
    class Meta:
        verbose_name = "Takip İsteği"
        verbose_name_plural = "Takip İstekleri"
        unique_together = ('from_user', 'to_user')  # Bir kullanıcı aynı kişiye birden fazla istek gönderemez


# Signal fonksiyonları
@receiver(post_delete, sender=Profile)
def delete_avatar_files_on_profile_delete(sender, instance, **kwargs):
    """Profil silindiğinde tüm avatar dosyalarını sil"""
    for field_name in ['avatar', 'avatar_thumbnail', 'avatar_medium']:
        field = getattr(instance, field_name)
        if field and hasattr(field, 'path') and os.path.isfile(field.path):
            os.remove(field.path)


@receiver(pre_save, sender=Profile)
def delete_old_avatar_files_on_change(sender, instance, **kwargs):
    """Avatar değiştirildiğinde veya silindiğinde eski dosyaları sil"""
    if not instance.pk:
        return  # Yeni kayıt ise hiçbir şey yapma

    try:
        old_instance = Profile.objects.get(pk=instance.pk)
        
        # Eğer avatar değişmişse eski dosyaları sil ve processed flag'ını reset et
        if old_instance.avatar != instance.avatar:
            # Eski dosyaları sil
            for field_name in ['avatar', 'avatar_thumbnail', 'avatar_medium']:
                old_field = getattr(old_instance, field_name)
                if old_field and hasattr(old_field, 'path') and os.path.isfile(old_field.path):
                    os.remove(old_field.path)
            
            # Avatar değiştiği için processed flag'ını reset et
            if instance.avatar:  # Yeni avatar varsa
                instance.avatar_processed = False
                # Eski thumbnail/medium field'larını temizle
                instance.avatar_thumbnail = None
                instance.avatar_medium = None
                print(f"Avatar changed for user {instance.user.username}, processing will be triggered")
            
    except Profile.DoesNotExist:
        pass  # Profil mevcut değilse hiçbir şey yapma


@receiver(post_save, sender=Profile)
def process_profile_avatar(sender, instance, created, **kwargs):
    """
    Profile kaydedildiğinde avatar'ı otomatik olarak işle
    """
    # Sadece avatar varsa ve henüz işlenmemişse işle
    if instance.avatar and not instance.avatar_processed:
        # Sonsuz döngüyü önlemek için update_fields kontrolü
        if 'avatar_processed' in (kwargs.get('update_fields') or []):
            return
            
        try:
            from apps.common.utils.image_processor import process_profile_image
            
            print(f"Processing avatar for user {instance.user.username}...")
            
            # Profile için convenience fonksiyonu kullan
            saved_files = process_profile_image(instance.avatar, instance.user.id)
            
            if saved_files:
                # Processed dosyaları profile field'larına ata
                if 'thumbnail' in saved_files:
                    instance.avatar_thumbnail.name = saved_files['thumbnail']
                if 'medium' in saved_files:
                    instance.avatar_medium.name = saved_files['medium']
                
                # İşleme başarılı oldu - signal handler'ı bypass et
                Profile.objects.filter(pk=instance.pk).update(
                    avatar_thumbnail=instance.avatar_thumbnail.name if instance.avatar_thumbnail else '',
                    avatar_medium=instance.avatar_medium.name if instance.avatar_medium else '',
                    avatar_processed=True
                )
                print(f"Profile avatar processed successfully for user {instance.user.username}")
            else:
                print(f"Profile avatar processing failed for user {instance.user.username}")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Profile avatar processing failed for user {instance.user.username}: {e}")
            print(f"Profile avatar processing error: {e}")
            # İşleme başarısız olursa orijinal avatar'ı kullan
