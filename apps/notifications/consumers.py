import json
import jwt
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from urllib.parse import parse_qs
from .models import Notification
from .services import NotificationService
from django.utils import timezone
from apps.common.templatetags.time_tags import relative_time

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Kullanıcıyı varsayılan olarak scope'dan al (web için mevcut yöntem)
        self.user = self.scope["user"]
        
        # Headers'dan authorization token'ını alma (React Native için - öncelik)
        headers = dict(self.scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode('utf-8')
        
        # Fallback: Query string'den token alma (eski yöntem)
        query_string = parse_qs(self.scope['query_string'].decode())
        query_auth_header = query_string.get('authorization', [None])[0]
        token_param = query_string.get('token', [None])[0]
        
        # Eğer user anonim ise ve token varsa (mobil uygulama için)
        if isinstance(self.user, AnonymousUser) and (auth_header or query_auth_header or token_param):
            try:
                # Token'ı al - öncelik sırası: headers > query auth > query token
                token = None
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                elif query_auth_header and query_auth_header.startswith('Bearer '):
                    token = query_auth_header.split(' ')[1]
                    print(f"Notifications - Token query auth'dan alındı: {token[:20]}...")
                elif token_param:
                    token = token_param
                    print(f"Notifications - Token query param'dan alındı: {token[:20]}...")
                
                if not token:
                    print("Notifications - Token bulunamadı")
                    await self.close(code=4003)
                    return
                
                # JWT token'ı çözümle
                from rest_framework_simplejwt.tokens import UntypedToken
                from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
                
                try:
                    # JWT settings'ten key'i al
                    jwt_settings = settings.SIMPLE_JWT
                    signing_key = jwt_settings.get('SIGNING_KEY', settings.SECRET_KEY)
                    algorithm = jwt_settings.get('ALGORITHM', 'HS256')
                    
                    # Token'ı doğrula
                    UntypedToken(token)  # Token geçerliliğini kontrol et
                    
                    # Payload'ı decode et
                    payload = jwt.decode(
                        token,
                        signing_key,
                        algorithms=[algorithm]
                    )
                    
                    # Token'dan user_id al
                    user_id = payload.get('user_id')
                    if user_id:
                        # Kullanıcıyı veritabanından çek
                        self.user = await self.get_user_by_id(user_id)
                        if not self.user:
                            print(f"Notifications - Kullanıcı bulunamadı: {user_id}")
                            await self.close(code=4003)
                            return
                    else:
                        print("Notifications - Token'da user_id bulunamadı")
                        await self.close(code=4003)
                        return
                        
                except (jwt.DecodeError, jwt.ExpiredSignatureError, InvalidToken, TokenError) as e:
                    print(f"Token doğrulama hatası: {str(e)}")
                    await self.close(code=4003)
                    return
                    
            except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
                print(f"Token doğrulama hatası: {str(e)}")
                await self.close(code=4003)
                return
            except Exception as e:
                print(f"Beklenmeyen hata: {str(e)}")
                await self.close(code=4003)
                return
        
        # Kullanıcı kimliği doğrulanmadıysa bağlantıyı reddet
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4003)
            return
        
        # Bildirim grup adını ayarla
        self.notification_group_name = f"user_{self.user.id}_notifications"

        # Grup'a katıl
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Bağlantı başarılı olduğunda grup adını bildir
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "notification_group_name": self.notification_group_name,
            "user_id": self.user.id
        }))
    async def disconnect(self, close_code):
        # Grup'tan ayrıl - sadece group_name varsa
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
        
    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data.get("command", None)
        if command == "ping":
            # Ping komutuna pong ile yanıt ver
            try:
                await self.send(text_data=json.dumps({
                    "type": "pong",
                    "timestamp": timezone.now().isoformat()
                }))
                print(f"Pong sent to: {self.user.username}, group: {self.notification_group_name}")
            except Exception as e:
                print(f"Error sending pong to {self.user.username}: {str(e)}")
            
        elif command == "mark_as_read":
            notification_id = data.get("notification_id", None)
            if notification_id:
                await self.mark_notification_as_read(notification_id)
                await self.send(text_data=json.dumps({
                    "type": "notification_read",
                    "notification_id": notification_id
                }))
        
        elif command == "get_unread_count":
            count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                "type": "unread_count",
                "count": count
            }))
            
        elif command == "get_notifications":
            notifications = await self.get_notifications()
            await self.send(text_data=json.dumps({
                "type": "notifications_list",
                "notifications": notifications
            }))
            
        elif command == "mark_all_as_read":
            await self.mark_all_as_read()
            await self.send(text_data=json.dumps({
                "type": "all_notifications_read"
            }))

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        # NotificationService kullanarak bildirimi okundu olarak işaretle
        return NotificationService.mark_as_read(notification_id, self.user)

    @database_sync_to_async
    def get_unread_count(self):
        return Notification.objects.filter(recipient=self.user, is_read=False).count()
        
    @database_sync_to_async
    def get_notifications(self):
        # Son 20 bildirimi getir
        notifications = Notification.objects.filter(recipient=self.user, is_read=False).order_by('-created_at')[:20]

        # Bildirimleri JSON serileştirilebilir formata dönüştür
        result = []
        for notification in notifications:
            # Tarihi kullanıcının zaman dilimine göre ayarla (Django settings.py'deki TIME_ZONE kullanılır)
            # localized_datetime = timezone.localtime(notification.created_at)

            result.append({
                'id': notification.id,
                'title': notification.title,
                'text': notification.text,
                'url': notification.url,
                'is_read': notification.is_read,
                'sender': notification.sender.username if notification.sender else None,
                'icon_class': notification.notification_type.icon_class,
                'created_at': relative_time(notification.created_at),
                'avatar' : notification.sender.profile.avatar.url if notification.sender and notification.sender.profile.avatar else None,
           })
        
        return result
        
    @database_sync_to_async
    def mark_all_as_read(self):
        # NotificationService kullanarak tüm bildirimleri okundu olarak işaretle
        return NotificationService.mark_all_as_read(self.user)

    @database_sync_to_async
    def get_user_by_id(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    # Notification handler
    async def notification_message(self, event):
        # İstemciye bildirim gönder
        message = event["message"]
        
        await self.send(text_data=json.dumps({
            "type": "new_notification",
            "notification": message
        }))