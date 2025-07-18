from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from .models import Notification, create_notifications


class NotificationService:
    """
    Bildirim oluşturma, silme ve yönetme işlemleri için merkezi servis sınıfı.
    Tüm bildirim işlemleri için bu sınıf kullanılmalıdır.
    """
    
    @staticmethod
    def create_notification(sender, recipient, code, content_object=None, parent_content_object=None):
        """
        Genel bildirim oluşturma metodu.
        Tüm bildirim türleri için bu metot kullanılabilir.
        
        Parameters:
        -----------
        sender : User
            Bildirimi gönderen kullanıcı
        recipient : User
            Bildirimi alan kullanıcı
        code : str
            Bildirim türü kodu (follow, like, comment vs.)
        content_object : Model instance, optional
            Bildirime konu olan içerik nesnesi (yorum, beğeni, gönderi vs.)
        parent_content_object : Model instance, optional
            Bildirime konu olan içeriğin bağlı olduğu ana içerik nesnesi
            (örn: bir yorum için post/etkinlik gibi ana içerik)
            
        Returns:
        --------
        Notification
            Oluşturulan bildirim nesnesi
        """
        # Aynı kullanıcı kendine bildirim gönderemez
        if sender == recipient:
            return None

        notification = create_notifications(sender, recipient, code, content_object)

        # Eğer parent_content_object verildiyse, bildirime ekle
        if notification and parent_content_object:
            parent_content_type = ContentType.objects.get_for_model(parent_content_object)
            notification.parent_content_type = parent_content_type
            notification.parent_object_id = parent_content_object.id
            notification.save()
        
        return notification
    
    @staticmethod
    def create_follow_notification(follower, followed_user):
        """
        Takip bildirimi oluşturur
        """
        return NotificationService.create_notification(
            sender=follower,
            recipient=followed_user,
            code="follow"
        )
    
    @staticmethod
    def create_follow_request_notification(requester, requested_user):
        """
        Takip isteği bildirimi oluşturur
        """
        return NotificationService.create_notification(
            sender=requester,
            recipient=requested_user,
            code="follow_request"
        )
    
    @staticmethod
    def create_follow_accepted_notification(accepter, requester):
        """
        Takip isteği kabul bildirimi oluşturur
        """
        return NotificationService.create_notification(
            sender=accepter,
            recipient=requester,
            code="follow_accepted"
        )
    
    @staticmethod
    def create_like_notification(user, like_obj):
        """
        Beğeni bildirimi oluşturur
        
        Parameters:
        -----------
        user : User
            Beğeniyi yapan kullanıcı
        like_obj : Like
            Beğeni nesnesi
        """
        # İçerik sahibi bul
        if hasattr(like_obj.content_object, 'user') and like_obj.content_object.user != user:
            # Beğenilen içeriğin modeli
            model_name = like_obj.content_type.model
            if model_name == "post":
                return NotificationService.create_notification(
                    sender=user,
                    recipient=like_obj.content_object.user,
                    code="post_like",
                    content_object=like_obj,
                    parent_content_object=like_obj.content_object  # Post'un kendisi ana içerik
                )
            elif model_name == "confessionmodel":
                return NotificationService.create_notification(
                    sender=user,
                    recipient=like_obj.content_object.user,
                    code="confession_like",
                    content_object=like_obj,
                    parent_content_object=like_obj.content_object  # Post'un kendisi ana içerik
                )
            elif model_name == "comment":
                comment = like_obj.content_object
                # Ana içerik (yorumun ait olduğu post, etkinlik vb)
                parent_object = comment.content_object

                if comment.parent:
                    return NotificationService.create_notification(
                        sender=user,
                        recipient=comment.user,
                        code="reply_like",
                        content_object=like_obj,
                        parent_content_object=comment
                    )
                else:
                    return NotificationService.create_notification(
                        sender=user,
                        recipient=comment.user,
                        code="comment_like",
                        content_object=like_obj,
                        parent_content_object=comment
                    )
        return None
    
    @staticmethod
    def create_comment_notification(user, comment):
        """
        Yorum bildirimi oluşturur
        
        Parameters:
        -----------
        user : User
            Yorumu yapan kullanıcı
        comment : Comment
            Yorum nesnesi
        """
        # İçeriğin sahibini bul ve ona bildirim gönder
        if hasattr(comment.content_object, 'user') and comment.content_object.user != user:
            # Ana içerik (yorumun yapıldığı post, etkinlik vb.)
            parent_object = comment.content_object
            
            return NotificationService.create_notification(
                sender=user,
                recipient=comment.content_object.user,
                code="comment",
                content_object=comment,
                parent_content_object=parent_object
            )
        return None
    
    @staticmethod
    def create_comment_reply_notification(user, comment, parent_comment):
        """
        Yorum yanıtı bildirimi oluşturur
        
        Parameters:
        -----------
        user : User
            Yanıtı yapan kullanıcı
        comment : Comment
            Yanıt yorumu nesnesi
        parent_comment : Comment
            Ana yorum nesnesi
        """
        if parent_comment.user != user:
            # Ana içerik (yorumun yapıldığı post, etkinlik vb.)
            parent_object = comment.content_object
            
            return NotificationService.create_notification(
                sender=user,
                recipient=parent_comment.user,
                code="comment_reply",
                content_object=comment,
                parent_content_object=parent_object
            )
        return None
    
    @staticmethod
    def delete_notification(sender, recipient, code, content_object=None):
        """
        Belirli bir bildirim türünü siler
        """
        notifications = Notification.objects.filter(
            sender=sender,
            recipient=recipient
        )
        
        # Eğer bildirim kodu belirtilmişse, o türdeki bildirimleri filtrele
        if code:
            from .models import NotificationType
            notification_type = NotificationType.objects.filter(code=code).first()
            if notification_type:
                notifications = notifications.filter(notification_type=notification_type)
        
        # Eğer content_object belirtilmişse, o nesneye ait bildirimleri filtrele
        if content_object:
            content_type = ContentType.objects.get_for_model(content_object)
            notifications = notifications.filter(
                content_type=content_type,
                object_id=content_object.id
            )
        
        # Bildirimleri sil
        count = notifications.count()
        notifications.delete()
        return count
    
    @staticmethod
    def delete_notification_by_object(content_object):
        """
        Belirli bir nesneye ait tüm bildirimleri siler
        """
        if not content_object or not content_object.id:
            return 0
            
        content_type = ContentType.objects.get_for_model(content_object)
        notifications = Notification.objects.filter(
            content_type=content_type,
            object_id=content_object.id
        )
        count = notifications.count()
        notifications.delete()
        return count
    
    @staticmethod
    def mark_as_read(notification_id, user):
        """
        Bildirimi okundu olarak işaretler
        """
        try:
            notification = Notification.objects.get(id=notification_id, recipient=user)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_as_read(user):
        """
        Kullanıcının tüm bildirimlerini okundu olarak işaretler
        """
        from django.utils import timezone
        now = timezone.now()
        count = Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True,
            read_at=now
        )
        return count