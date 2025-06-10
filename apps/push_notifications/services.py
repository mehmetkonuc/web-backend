import requests
import json
import logging
from typing import List, Dict, Any, Optional, Union
from django.conf import settings
from django.contrib.auth.models import User

from .models import PushToken
from .utils import create_expo_message, log_push_notification, sanitize_notification_text


logger = logging.getLogger(__name__)


class ExpoPushNotificationService:
    """
    Expo Push Notification servisi
    """
    
    EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
    
    def send_notification(self, user_id: int, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Tek bir kullanıcıya push notification gönderir
        """
        try:
            # Kullanıcının push token'ını al
            push_token = PushToken.objects.filter(user_id=user_id, is_active=True).first()
            
            if not push_token:
                logger.warning(f"User {user_id} için aktif push token bulunamadı")
                return False
            
            # Mesaj oluştur
            message = create_expo_message(
                to=push_token.expo_token,
                title=sanitize_notification_text(title, 50),
                body=sanitize_notification_text(body, 100),
                data=data
            )
            
            # Expo'ya gönder
            response = self._send_to_expo([message])
            
            if response and response.get('data'):
                receipt_data = response['data'][0]
                success = receipt_data.get('status') == 'ok'
                
                if not success:
                    error_msg = receipt_data.get('message', 'Bilinmeyen hata')
                    log_push_notification(user_id, push_token.expo_token, title, False, error_msg)
                    return False
                
                log_push_notification(user_id, push_token.expo_token, title, True)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Push notification gönderim hatası: {str(e)}")
            return False
    
    def send_bulk_notifications(self, user_ids: List[int], title: str, body: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
        """
        Birden fazla kullanıcıya push notification gönderir
        """
        results = {"success": 0, "failed": 0}
        
        try:
            # Aktif push token'ları al
            push_tokens = PushToken.objects.filter(user_id__in=user_ids, is_active=True).select_related('user')
            
            if not push_tokens.exists():
                logger.warning(f"Belirtilen kullanıcılar için aktif push token bulunamadı: {user_ids}")
                return results
            
            # Mesajları hazırla
            messages = []
            for push_token in push_tokens:
                try:
                    message = create_expo_message(
                        to=push_token.expo_token,
                        title=sanitize_notification_text(title, 50),
                        body=sanitize_notification_text(body, 100),
                        data=data                    )
                    messages.append(message)
                except Exception as e:
                    logger.error(f"Mesaj oluşturma hatası - User {push_token.user.pk}: {str(e)}")
                    results["failed"] += 1
            
            # Expo'ya gönder
            if messages:
                response = self._send_to_expo(messages)
                
                if response and response.get('data'):
                    for i, receipt_data in enumerate(response['data']):
                        push_token = push_tokens[i]
                        success = receipt_data.get('status') == 'ok'
                        
                        if success:
                            results["success"] += 1
                            log_push_notification(push_token.user.pk, push_token.expo_token, title, True)
                        else:
                            results["failed"] += 1
                            error_msg = receipt_data.get('message', 'Bilinmeyen hata')
                            log_push_notification(push_token.user.pk, push_token.expo_token, title, False, error_msg)
                
            return results
            
        except Exception as e:
            logger.error(f"Bulk push notification hatası: {str(e)}")
            return results
    
    def _send_to_expo(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Expo Push API'ye mesajları gönderir
        """
        try:
            response = self.session.post(
                self.EXPO_PUSH_URL,
                data=json.dumps(messages),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Expo API hatası: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Expo API isteğinde hata: {str(e)}")
            return None
    
    def get_user_tokens(self, user_id: int) -> List[str]:
        """
        Kullanıcının aktif push token'larını döndürür
        """
        try:
            push_tokens = PushToken.objects.filter(user_id=user_id, is_active=True)
            return [token.expo_token for token in push_tokens]
        except Exception as e:
            logger.error(f"User {user_id} için push token'lar alınırken hata: {str(e)}")
            return []


# Singleton servis instance
push_service = ExpoPushNotificationService()


def send_notification_push(user_id: int, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Bildirim push'ı gönderir
    """
    return push_service.send_notification(user_id, title, body, data)


def send_chat_push(user_id: int, sender_name: str, message: str, chat_room_id: str) -> bool:
    """
    Chat mesajı push'ı gönderir
    """
    title = f"{sender_name} size mesaj gönderdi"
    body = sanitize_notification_text(message, 80)
    data = {
        "type": "chat",
        "chat_room_id": chat_room_id,
        "sender_name": sender_name
    }
    
    return push_service.send_notification(user_id, title, body, data)