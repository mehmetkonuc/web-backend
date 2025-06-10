from django.db import models
from django.contrib.auth.models import User
from apps.dataset.models import University, Department, GraduationStatus
import os
from datetime import datetime
from apps.notifications.services import NotificationService
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

def avatar_upload_path(instance, filename):
    # Dosyanın yükleneceği yolu yıl/ay formatında ayarla
    now = datetime.now()
    path = os.path.join('avatars', str(now.year), str(now.month).zfill(2))
    # Dosya adını korumak için
    return os.path.join(path, filename)

# Create your models here.
class Profile(models.Model):
    # Mesaj gizlilik seçenekleri
    MESSAGE_PRIVACY_CHOICES = [
        ('none', 'Hiç Kimse'),
        ('followers', 'Sadece Takipçilerim'),
        ('everyone', 'Herkes'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Kullanıcı")
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True, verbose_name="Profil Fotoğrafı")
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
def delete_avatar_on_profile_delete(sender, instance, **kwargs):
    """Profil silindiğinde avatar dosyasını da sil"""
    if instance.avatar and hasattr(instance.avatar, 'path'):
        if os.path.isfile(instance.avatar.path):
            os.remove(instance.avatar.path)

@receiver(pre_save, sender=Profile)
def delete_old_avatar_on_change(sender, instance, **kwargs):
    """Avatar değiştirildiğinde veya silindiğinde eski dosyayı sil"""
    if not instance.pk:
        return  # Yeni kayıt ise hiçbir şey yapma

    try:
        old_instance = Profile.objects.get(pk=instance.pk)
        old_avatar = old_instance.avatar
        new_avatar = instance.avatar
        
        # Eğer avatar değişmişse veya silinmişse eski dosyayı sil
        if old_avatar and old_avatar != new_avatar:
            if hasattr(old_avatar, 'path') and os.path.isfile(old_avatar.path):
                os.remove(old_avatar.path)
    except Profile.DoesNotExist:
        pass  # Profil mevcut değilse hiçbir şey yapma
