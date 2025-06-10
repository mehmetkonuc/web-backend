import re
import logging
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


def is_expo_push_token(token: str) -> bool:
    """
    Expo push token formatını doğrular
    """
    if not token or not isinstance(token, str):
        return False
    
    # Expo push token formatları:
    # - ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]
    # - ExpoPushToken[xxxxxxxxxxxxxxxxxxxxxx]
    expo_token_pattern = r'^Expo(nent)?PushToken\[[A-Za-z0-9_-]+\]$'
    
    return bool(re.match(expo_token_pattern, token))


def format_push_notification_data(title: str, body: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Push notification verilerini Expo formatına çevirir
    """
    notification_data: Dict[str, Any] = {
        'title': title,
        'body': body,
        'sound': 'default',
        'priority': 'high',
    }
    
    if data:
        notification_data['data'] = data
    
    return notification_data


def create_expo_message(to: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Expo push notification mesajı oluşturur
    """
    if not is_expo_push_token(to):
        raise ValueError(f"Geçersiz Expo push token: {to}")
    
    message = {
        'to': to,
        **format_push_notification_data(title, body, data)
    }
    
    return message


def log_push_notification(user_id: int, token: str, title: str, success: bool, error: Optional[str] = None):
    """
    Push notification gönderim durumunu loglar
    """
    status = "SUCCESS" if success else "FAILED"
    log_message = f"Push notification {status} - User ID: {user_id}, Token: {token[:20]}..., Title: {title}"
    
    if success:
        logger.info(log_message)
    else:
        logger.error(f"{log_message}, Error: {error}")


def sanitize_notification_text(text: str, max_length: int = 100) -> str:
    """
    Bildirim metnini temizler ve kısaltır
    """
    if not text:
        return ""
    
    # HTML taglerini temizle
    import html
    clean_text = html.unescape(text)
    
    # Fazla boşlukları temizle
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Uzunluk kontrolü
    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length-3] + "..."
    
    return clean_text