from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json

class NotificationType(models.Model):
    """Bildirim türlerini tanımlayan model"""
    code = models.CharField(max_length=50, unique=True, verbose_name="Kod")
    name = models.CharField(max_length=100, verbose_name="İsim")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    icon_class = models.CharField(max_length=50, blank=True, null=True, verbose_name="İkon Sınıfı")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Bildirim Türü"
        verbose_name_plural = "Bildirim Türleri"

class Notification(models.Model):
    """Kullanıcı bildirimlerini saklayan ana model"""
    # Bildirimi alan kullanıcı
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Alıcı")
    
    # Bildirimi gönderen kullanıcı (sistem bildirimleri için boş olabilir)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                              related_name='sent_notifications', verbose_name="Gönderen")
    
    # Bildirim türü
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE, verbose_name="Bildirim Türü")
    
    # İlgili içerik (Generic Foreign Key kullanarak farklı modellere referans verebilir)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Ana içerik (Örneğin, bir yorumun hangi gönderiye ait olduğu)
    parent_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='parent_notifications')
    parent_object_id = models.PositiveIntegerField(null=True, blank=True)
    parent_content_object = GenericForeignKey('parent_content_type', 'parent_object_id')
    
    # Bildirim başlığı ve metni
    title = models.CharField(max_length=255, verbose_name="Başlık")
    text = models.TextField(verbose_name="Metin")
    
    # Bildirim URL'i (tıklandığında yönlendirilecek sayfa)
    url = models.CharField(max_length=255, blank=True, null=True, verbose_name="URL")
    
    # Bildirim durumu
    is_read = models.BooleanField(default=False, verbose_name="Okundu mu?")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Okunma Zamanı")
    
    # Zaman damgaları
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Zamanı")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Zamanı")
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        """Bildirimi okundu olarak işaretle"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def save(self, *args, **kwargs):
        """Bildirim kaydedildiğinde WebSocket üzerinden bildirim gönder"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:  # Yeni bildirim oluşturulduğunda
            self.send_notification()
    
    def send_notification(self):
        """WebSocket üzerinden bildirim gönder"""
        if self.sender.profile.avatar:
            avatar_url = self.sender.profile.avatar.url
        else:
            avatar_url = None
        channel_layer = get_channel_layer()
        
        # Django'daki timezone ayarlarını kullanarak oluşturma zamanını alıyoruz
        # Bu created_at değeri zaten Django ayarlarınızdaki TIME_ZONE='Europe/Istanbul' ayarını kullanıyor
        # ancak isoformat() metodu UTC olarak çevirebiliyor, bu yüzden astimezone() kullanıyoruz
        localized_datetime = timezone.localtime(self.created_at)

        notification_data = {
            'id': self.id,
            'title': self.title,
            'text': self.text,
            'url': self.url,
            'sender': {'id': self.sender.id if self.sender else None,
                       'username': self.sender.username if self.sender else None},
            'icon_class': self.notification_type.icon_class,
            'created_at': localized_datetime.isoformat(),  # Yerel saat dilimindeki ISO formatını kullan
            'avatar': avatar_url,
            'notification_type': {
                    'code': self.notification_type.code if self.notification_type else None,
                    'name': self.notification_type.name if self.notification_type else None,
                },
            'code': self.notification_type.code if self.notification_type else None,
        }

        if self.notification_type.code == "comment":
            data = {
                'parent_content_type_name' : self.parent_content_type.model if self.parent_content_type else None,
                'parent_object_id' : self.parent_object_id,
                'object_id' : self.object_id,
            }
            notification_data.update(data)

        elif self.notification_type.code == "comment_reply":
            from apps.comment.models import Comment
            reply = Comment.objects.get(id=self.object_id)

            data = {
                'object_id' : self.object_id,
                'reply_parent_id' : reply.parent_id if reply else None,
                'origin_object_id' : reply.object_id if reply else None,
                'content_type' : self.content_type.id if self.content_type else None,
                'origin_content_type' : reply.content_type.id if reply else None,
            }
            notification_data.update(data)

        elif self.notification_type.code == "post_like":
            data = {
                'parent_content_type_name' : self.parent_content_type.model if self.parent_content_type else None,
                'parent_object_id' : self.parent_object_id,
            }
            notification_data.update(data)

        elif self.notification_type.code == "comment_like":
            from apps.comment.models import Comment
            comment = Comment.objects.get(id=self.parent_object_id)

            data = {
                'origin_content_type_name' : comment.content_type.model if comment.content_type else None,
                'origin_object_id' : comment.object_id,
                'parent_object_id' : comment.id,
            }
            notification_data.update(data)

        elif self.notification_type.code == "reply_like":
            from apps.comment.models import Comment
            reply = Comment.objects.get(id=self.parent_object_id)

            data = {
                'parent_object_id' : reply.id,
                'reply_parent_id' : reply.parent_id if reply else None,
                'origin_object_id' : reply.object_id if reply else None,
                'parent_content_type' : self.content_type.id if self.content_type else None,
                'origin_content_type' : reply.content_type.id if reply else None,
            }
            notification_data.update(data)        # Alıcı kullanıcının bildirim kanalına mesaj gönder
        async_to_sync(channel_layer.group_send)(
            f"user_{self.recipient.id}_notifications",
            {
                'type': 'notification_message',
                'message': notification_data
            }
        )
        
        # Push notification gönder (uygulama kapalıyken için)
        self.send_push_notification()
    
    def send_push_notification(self):
        """Push notification gönder"""
        try:
            from apps.push_notifications.services import firebase_service
            
            # Kullanıcıya push notification gönder
            success = firebase_service.send_notification(
                user_id=self.recipient.id,
                title=self.title,
                body=self.text,
                data={
                    'type': 'notification',
                    'notification_id': self.id,
                    'code': self.notification_type.code if self.notification_type else None,
                    'url': self.url,
                    'sender_id': self.sender.id if self.sender else None
                }
            )
            
            if success:
                print(f"Push notification sent successfully to user {self.recipient.id}")
            else:
                print(f"Failed to send push notification to user {self.recipient.id}")
                
        except Exception as e:
            print(f"Error sending push notification: {str(e)}")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"

def get_defaults_by_code(code, sender):
    if "follow" == code:
        return {
            "defaults": {
                "name": "Takip Bildirimi",
                "description": "Bir kullanıcı sizi takip etmeye başladığında gönderilir",
                "icon_class": "tabler-user-plus"
            },
            "title": "Yeni Takipçi",
            "text": f"{sender.username} sizi takip etmeye başladı."
        }
    elif "follow_request" == code:
        return {
            "defaults": {
                "name": "Takip İsteği",
                "description": "Bir kullanıcı size takip isteği gönderdiğinde iletilir",
                "icon_class": "tabler-user-question"
            },
            "title": "Takip İsteği",
            "text": f"{sender.username} size takip isteği gönderdi."
        }
    elif "follow_accepted" == code:
        return {
            "defaults": {
                "name": "Takip İsteği Onaylandı",
                "description": "Takip isteğiniz kabul edildiğinde gönderilir",
                "icon_class": "tabler-user-check"
            },
            "title": "Takip İsteği Onaylandı",
            "text": f"{sender.username} takip isteğinizi kabul etti."
        }
    elif "post_like" == code:
        return {
            "defaults": {
                "name": "Beğeni Bildirimi",
                "description": "Bir kullanıcı içeriğinizi beğendiğinde gönderilir",
                "icon_class": "tabler-heart"
            },
            "title": "Yeni Beğeni",
            "text": f"{sender.username} paylaşımınızı beğendi."
        }
    elif "comment_like" == code:
        return {
            "defaults": {
                "name": "Yorum Beğeni Bildirimi",
                "description": "Bir kullanıcı yorumunuzu beğendiğinde gönderilir",
                "icon_class": "tabler-heart"
            },
            "title": "Yorumunuz Beğenildi",
            "text": f"{sender.username} yorumunuzu beğendi."
        }
    elif "reply_like" == code:
        return {
            "defaults": {
                "name": "Yanıt Beğeni Bildirimi",
                "description": "Bir kullanıcı yanıtınızı beğendiğinde gönderilir",
                "icon_class": "tabler-heart"
            },
            "title": "Yanıtız Beğenildi",
            "text": f"{sender.username} yanıtınızı beğendi."
        }
    elif "comment" == code:
        return {
            "defaults": {
                "name": "Yorum Bildirimi",
                "description": "Bir kullanıcı içeriğinize yorum yaptığında gönderilir",
                "icon_class": "tabler-message-circle"
            },
            "title": "Yeni Yorum",
            "text": f"{sender.username} içeriğinize yorum yaptı."
        }
    elif "comment_reply" == code:
        return {
            "defaults": {
                "name": "Yorum Yanıtı Bildirimi",
                "description": "Bir kullanıcı yorumunuza yanıt verdiğinde gönderilir",
                "icon_class": "tabler-message-circle-2"
            },
            "title": "Yorumuza Yanıt Verildi",
            "text": f"{sender.username} yorumunuza yanıt verdi."
        }

# Önceden tanımlanmış bildirim türleri için yardımcı fonksiyonlar
def create_notifications(sender, recipient, code, content_object=None, parent_content_object=None, parent_content=None):
    """Bildirim oluşturur
    
    Parameters:
    -----------
    sender : User
        Bildirimi gönderen kullanıcı
    recipient : User
        Bildirimi alan kullanıcı
    code : str
        Bildirim türü kodu
    content_object : Model instance, optional
        Bildirime konu olan nesne (örn: yorum, beğeni)
    parent_content_object : Model instance, optional
        Bildirime konu olan nesnenin ana içeriği (örn: post, etkinlik)
    """
    notification_info = get_defaults_by_code(code, sender)

    notification_type, _ = NotificationType.objects.get_or_create(
        code=code,
        defaults= notification_info['defaults']
    )
    
    # URL yolunu bildirim türüne göre belirle
    url_path = f"/profile/{sender.username}/" 
    
    # Takip isteği için farklı URL
    if code == "follow_request":
        url_path = "/profile/follow-requests/"
    # Yorum bildirimleri için URL yapılandırması
    elif code in ["comment", "comment_reply"] and content_object:
        if hasattr(content_object, 'get_absolute_url'):
            url_path = f"/comment/comment/{content_object.id}/" #content_object.get_absolute_url()
        elif hasattr(content_object, 'content_object') and hasattr(content_object.content_object, 'get_absolute_url'):
            # Eğer yorum ise, yorumun bağlı olduğu içeriğin URL'sine yönlendir
            url_path = f"/comment/comment/{content_object.id}/" #content_object.content_object.get_absolute_url()
        else:
            # Direkt olarak yorumun detay sayfasına yönlendir
            url_path = f"/comment/comment/{content_object.id}/"
    # Beğeni bildirimleri için URL yapılandırması
    elif code == "post_like" and content_object:
        # Like objesi üzerinden content_object'e erişim (Like modelinin GenericForeignKey'i)
        if hasattr(content_object, 'content_object') and hasattr(content_object.content_object, 'id'):
            # Beğenilen içeriğin ID'sini al ve URL'yi oluştur
            liked_object = content_object.content_object
            if hasattr(liked_object, 'get_absolute_url'):
                url_path = liked_object.get_absolute_url()
            else:
                # Post için varsayılan URL
                if hasattr(liked_object, 'id'):
                    app_name = liked_object._meta.app_label
                    model_name = liked_object._meta.model_name
                    if app_name == 'post' and model_name == 'post':
                        url_path = f"/post/detail/{liked_object.id}/"
    elif code in "comment_like" and content_object:
        if hasattr(content_object, 'content_object') and hasattr(content_object.content_object, 'id'):
            # Beğenilen içeriğin ID'sini al ve URL'yi oluştur
            liked_object = content_object.content_object
            if hasattr(liked_object, 'get_absolute_url'):
                url_path = liked_object.get_absolute_url()
            else:
                # Post için varsayılan URL
                if hasattr(liked_object, 'id'):
                    app_name = liked_object._meta.app_label
                    model_name = liked_object._meta.model_name
                    if app_name == 'comment' and model_name == 'comment':
                        url_path = f"/comment/comment/{liked_object.id}/"
    elif code in "reply_like" and content_object:
        if hasattr(content_object, 'content_object') and hasattr(content_object.content_object, 'id'):
            # Beğenilen içeriğin ID'sini al ve URL'yi oluştur
            liked_object = content_object.content_object
            if hasattr(liked_object, 'get_absolute_url'):
                url_path = liked_object.get_absolute_url()
            else:
                # Post için varsayılan URL
                if hasattr(liked_object, 'id'):
                    app_name = liked_object._meta.app_label
                    model_name = liked_object._meta.model_name
                    if app_name == 'comment' and model_name == 'comment':
                        url_path = f"/comment/comment/{liked_object.id}/"

    # notification = Notification.objects.create(
    #     recipient=recipient,
    #     sender=sender,
    #     notification_type=notification_type,
    #     title=notification_info['title'],
    #     text=notification_info['text'],
    #     url=url_path
    # )
    
    # İlgili içeriği bildirime bağla
    if content_object:
        content_type = ContentType.objects.get_for_model(content_object)
        content_type = content_type
        object_id = content_object.id

    
    # Ana içeriği bildirime bağla
    if parent_content_object:
        parent_content_type = ContentType.objects.get_for_model(parent_content_object)
        parent_content_type = parent_content_type
        parent_object_id = parent_content_object.id

    # Eğer parent_content_object verilmediyse ancak content_object'in kendi içeriği varsa
    elif content_object and hasattr(content_object, 'content_object'):
        # content_object'in bağlı olduğu nesneyi (örn: yorumun bağlı olduğu post) ana içerik olarak ayarla
        parent_content = content_object.content_object
        if parent_content:
            parent_content_type = ContentType.objects.get_for_model(parent_content)
            parent_content_type = parent_content_type
            parent_object_id = parent_content.id
    
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=notification_info['title'],
        text=notification_info['text'],
        url=url_path,
        content_type=content_type if content_object else None,
        object_id=object_id if content_object else None,
        parent_content_type=parent_content_type if parent_content else None,
        parent_object_id=parent_object_id if parent_content else None
    )
    return notification

