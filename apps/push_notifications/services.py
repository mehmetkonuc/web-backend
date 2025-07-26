import json
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.contrib.auth.models import User
import os

# Firebase admin import'u koşullu yap
try:
    import firebase_admin
    from firebase_admin import messaging, credentials
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

from .models import FCMToken, NotificationLog

logger = logging.getLogger(__name__)


class FirebaseNotificationService:
    """
    Firebase Cloud Messaging (FCM) servisi
    """
    
    def __init__(self):
        self.app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """
        Firebase Admin SDK'yı başlatır
        """
        try:
            # Development modda Firebase'i devre dışı bırak
            if getattr(settings, 'DEBUG', False):
                logger.info("Firebase devre dışı (DEBUG=True)")
                return
                
            # Firebase mevcut değilse pas geç
            if not FIREBASE_AVAILABLE:
                logger.warning("Firebase Admin SDK mevcut değil")
                return
                
            # Firebase enabled kontrolü
            if not getattr(settings, 'FIREBASE_ENABLED', False):
                logger.warning("Firebase devre dışı (service account key dosyası bulunamadı)")
                return
            
            # Eğer zaten başlatılmışsa, tekrar başlatma
            if firebase_admin._apps:
                self.app = firebase_admin.get_app()
                return
            
            # Firebase service account key dosyasının yolu
            service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_KEY', None)
            
            if not service_account_path:
                logger.error("FIREBASE_SERVICE_ACCOUNT_KEY setting tanımlanmamış")
                return
                
            if not os.path.exists(service_account_path):
                logger.error(f"Firebase service account key dosyası bulunamadı: {service_account_path}")
                return
            
            # Firebase app'i başlat
            cred = credentials.Certificate(service_account_path)
            self.app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK başarıyla başlatıldı")
            
        except Exception as e:
            logger.error(f"Firebase başlatma hatası: {str(e)}")
            self.app = None
    
    def register_token(self, user: User, fcm_token: str, platform: str, device_info: Optional[dict] = None) -> bool:
        """
        Kullanıcının FCM token'ını kaydeder veya günceller
        """
        try:
            token_obj, created = FCMToken.objects.update_or_create(
                user=user,
                platform=platform,
                defaults={
                    'fcm_token': fcm_token,
                    'device_info': device_info or {},
                    'is_active': True
                }
            )
            
            action = "oluşturuldu" if created else "güncellendi"
            logger.info(f"FCM Token {action}: {user.username} - {platform}")
            return True
            
        except Exception as e:
            logger.error(f"FCM Token kaydetme hatası: {str(e)}")
            return False
    
    def remove_token(self, user: User, fcm_token: Optional[str] = None) -> bool:
        """
        Kullanıcının FCM token'ını siler
        """
        try:
            if fcm_token:
                # Belirli token'ı sil
                FCMToken.objects.filter(user=user, fcm_token=fcm_token).delete()
            else:
                # Kullanıcının tüm token'larını sil
                FCMToken.objects.filter(user=user).delete()
            
            logger.info(f"FCM Token silindi: {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"FCM Token silme hatası: {str(e)}")
            return False
    
    def send_notification(self, user_id: int, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Tek bir kullanıcıya push notification gönderir
        """
        try:
            logger.debug(f"Firebase durumu - FIREBASE_AVAILABLE: {FIREBASE_AVAILABLE}, app: {self.app}")
            if not FIREBASE_AVAILABLE or not self.app:
                logger.error("Firebase başlatılmamış veya mevcut değil")
                return False
            
            # Kullanıcının aktif FCM token'larını al
            user = User.objects.get(id=user_id)
            fcm_tokens = FCMToken.objects.filter(user=user, is_active=True)
            
            if not fcm_tokens.exists():
                logger.warning(f"User {user_id} için aktif FCM token bulunamadı")
                return False
            
            success_count = 0
            
            for token_obj in fcm_tokens:
                try:
                    # FCM mesajı oluştur
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body
                        ),
                        data=self._prepare_data(data),
                        token=token_obj.fcm_token,
                        android=messaging.AndroidConfig(
                            priority='high',
                            notification=messaging.AndroidNotification(
                                icon='ic_notification',
                                color='#FF6B6B',
                                sound='default'
                            )
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    alert=messaging.ApsAlert(
                                        title=title,
                                        body=body
                                    ),
                                    badge=1,
                                    sound='default'
                                )
                            )
                        )
                    )
                    
                    # Mesajı gönder
                    response = messaging.send(message)
                    
                    # Log kaydı
                    self._log_notification(user, token_obj, title, body, data, 'success')
                    success_count += 1
                    
                    logger.info(f"FCM mesajı gönderildi: {response}")
                    
                except messaging.UnregisteredError:
                    # Token geçersiz, sil
                    token_obj.is_active = False
                    token_obj.save()
                    self._log_notification(user, token_obj, title, body, data, 'failed', 'Token geçersiz')
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"FCM gönderim hatası: {error_msg}")
                    self._log_notification(user, token_obj, title, body, data, 'failed', error_msg)
            
            return success_count > 0
            
        except User.DoesNotExist:
            logger.error(f"User {user_id} bulunamadı")
            return False
        except Exception as e:
            logger.error(f"FCM notification gönderim hatası: {str(e)}")
            return False
    
    def send_bulk_notifications(self, user_ids: List[int], title: str, body: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
        """
        Birden fazla kullanıcıya push notification gönderir
        """
        results = {"success": 0, "failed": 0}
        
        if not FIREBASE_AVAILABLE or not self.app:
            logger.error("deneme", FIREBASE_AVAILABLE, self.app)

            logger.error("Firebase başlatılmamış veya mevcut değil")
            return results
        
        try:
            # Aktif FCM token'ları al
            fcm_tokens = FCMToken.objects.filter(
                user_id__in=user_ids, 
                is_active=True
            ).select_related('user')
            
            if not fcm_tokens.exists():
                logger.warning(f"Belirtilen kullanıcılar için aktif FCM token bulunamadı: {user_ids}")
                return results
            
            # Mesajları hazırla
            messages = []
            token_objects = []
            
            for token_obj in fcm_tokens:
                try:
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body
                        ),
                        data=self._prepare_data(data),
                        token=token_obj.fcm_token,
                        android=messaging.AndroidConfig(
                            priority='high',
                            notification=messaging.AndroidNotification(
                                icon='ic_notification',
                                color='#FF6B6B',
                                sound='default'
                            )
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    alert=messaging.ApsAlert(
                                        title=title,
                                        body=body
                                    ),
                                    badge=1,
                                    sound='default'
                                )
                            )
                        )
                    )
                    
                    messages.append(message)
                    token_objects.append(token_obj)
                    
                except Exception as e:
                    logger.error(f"Mesaj oluşturma hatası - User {token_obj.user.pk}: {str(e)}")
                    results["failed"] += 1
                    self._log_notification(token_obj.user, token_obj, title, body, data, 'failed', str(e))
            
            # Toplu gönderim
            if messages:
                response = messaging.send_all(messages)
                
                # Sonuçları işle
                for i, result in enumerate(response.responses):
                    token_obj = token_objects[i]
                    
                    if result.success:
                        results["success"] += 1
                        self._log_notification(token_obj.user, token_obj, title, body, data, 'success')
                    else:
                        results["failed"] += 1
                        error_msg = result.exception.details if result.exception else 'Bilinmeyen hata'
                        self._log_notification(token_obj.user, token_obj, title, body, data, 'failed', error_msg)
                        
                        # Token geçersizse pasif yap
                        if isinstance(result.exception, messaging.UnregisteredError):
                            token_obj.is_active = False
                            token_obj.save()
            
            return results
            
        except Exception as e:
            logger.error(f"Bulk FCM notification hatası: {str(e)}")
            return results
    
    def _prepare_data(self, data: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """
        FCM data payload'ını hazırlar (tüm değerler string olmalı)
        """
        if not data:
            return {}
        
        prepared_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                prepared_data[key] = json.dumps(value)
            else:
                prepared_data[key] = str(value)
        
        return prepared_data
    
    def _log_notification(self, user: User, token_obj: FCMToken, title: str, body: str, 
                         data: Optional[Dict[str, Any]], status: str, error_message: Optional[str] = None):
        """
        Notification gönderim logunu kaydeder
        """
        try:
            NotificationLog.objects.create(
                user=user,
                fcm_token=token_obj,
                title=title,
                body=body,
                data=data or {},
                status=status,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Notification log kaydetme hatası: {str(e)}")
    
    def get_user_tokens(self, user_id: int) -> List[str]:
        """
        Kullanıcının aktif FCM token'larını döndürür
        """
        try:
            fcm_tokens = FCMToken.objects.filter(user_id=user_id, is_active=True)
            return [token.fcm_token for token in fcm_tokens]
        except Exception as e:
            logger.error(f"User {user_id} için FCM token'lar alınırken hata: {str(e)}")
            return []


# Singleton servis instance
firebase_service = FirebaseNotificationService()


def send_notification_push(user_id: int, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Bildirim push'ı gönderir
    """
    return firebase_service.send_notification(user_id, title, body, data)


def send_chat_push(user_id: int, sender_name: str, message: str, chat_id: str) -> bool:
    """
    Chat mesajı push'ı gönderir
    """
    title = f"{sender_name} size mesaj gönderdi"
    body = message[:100] + "..." if len(message) > 100 else message
    data = {
        "type": "message",
        "chatId": chat_id,
        "otherUser": json.dumps({"name": sender_name}),
        "senderId": sender_name
    }
    
    return firebase_service.send_notification(user_id, title, body, data)


def send_like_push(user_id: int, liker_name: str, post_id: str) -> bool:
    """
    Beğeni push'ı gönderir
    """
    title = "Gönderiniz beğenildi"
    body = f"{liker_name} gönderinizi beğendi"
    data = {
        "type": "like",
        "postId": post_id,
        "userId": str(user_id)
    }
    
    return firebase_service.send_notification(user_id, title, body, data)


def send_comment_push(user_id: int, commenter_name: str, post_id: str) -> bool:
    """
    Yorum push'ı gönderir
    """
    title = "Gönderinize yorum yapıldı"
    body = f"{commenter_name} gönderinize yorum yaptı"
    data = {
        "type": "comment",
        "postId": post_id,
        "userId": str(user_id)
    }
    
    return firebase_service.send_notification(user_id, title, body, data)


def send_follow_push(user_id: int, follower_name: str, follower_id: str) -> bool:
    """
    Takip push'ı gönderir
    """
    title = "Yeni takipçiniz var"
    body = f"{follower_name} sizi takip etmeye başladı"
    data = {
        "type": "follow",
        "userId": follower_id
    }
    
    return firebase_service.send_notification(user_id, title, body, data)