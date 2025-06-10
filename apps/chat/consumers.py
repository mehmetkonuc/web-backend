import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User, AnonymousUser
from django.utils import timezone
from django.conf import settings
from urllib.parse import parse_qs
import jwt
from .models import ChatRoom, Message
from apps.common.templatetags.time_tags import relative_time
from .utils import can_message_user
from apps.push_notifications.services import ExpoPushNotificationService

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # URL'den chat odası ID'sini al
        self.room_id = self.scope['url_route']['kwargs'].get('room_id')
        
        # Eğer room_id yoksa, bu genel bir mesaj listesi websocket'i olacak
        if not self.room_id:
            self.is_room_specific = False
            self.room_group_name = None
        else:
            self.is_room_specific = True
            self.room_group_name = f'chat_{self.room_id}'
        
        # Kullanıcıyı doğrula
        self.user = self.scope["user"]
        
        # URL'den authorization token'ını alma (mobil uygulamalar için)
        query_string = parse_qs(self.scope['query_string'].decode())
        auth_header = query_string.get('authorization', [None])[0]
        token_param = query_string.get('token', [None])[0]
        
        # Eğer user anonim ise ve token varsa (mobil uygulama için)
        if isinstance(self.user, AnonymousUser) and (auth_header or token_param):
            try:
                # Token'ı al
                token = None
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                elif token_param:
                    token = token_param
                
                if not token:
                    await self.close(code=4003)
                    return
                
                # JWT token'ı çözümle
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=["HS256"]
                )
                
                # Token'dan user_id al
                user_id = payload.get('user_id')
                if user_id:
                    self.user = await self.get_user_by_id(user_id)
                    if not self.user:
                        await self.close(code=4003)
                        return
                else:
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
        
        # Kullanıcıya ait kişisel mesaj grup adı
        self.personal_group_name = f'chat_personal_{self.user.id}'
        
        # Kişisel grup'a katıl (tüm kullanıcıya özel mesajlar için)
        await self.channel_layer.group_add(
            self.personal_group_name,
            self.channel_name
        )
        
        # Eğer belirli bir chat odasına bağlanıyorsa
        if self.is_room_specific:
            # Kullanıcının bu odaya erişim izni var mı kontrol et
            has_access = await self.check_room_access(self.room_id)
            if not has_access:
                await self.close(code=4004)  # Erişim reddedildi
                return
                
            # Oda grup'una katıl
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
        
        await self.accept()
        
        # Bağlantı başarılı olduğunda bilgi mesajı gönder
        connection_info = {
            "type": "connection_established",
            "user_id": self.user.id,
            "personal_group": self.personal_group_name
        }
                
        await self.send(text_data=json.dumps(connection_info))

    async def disconnect(self, close_code):
        # Eğer belirli bir odaya bağlıysa, gruptan ayrıl
        if self.is_room_specific:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        # Kişisel gruptan ayrıl
        await self.channel_layer.group_discard(
            self.personal_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data.get("command", None)

        if command == "send_message":
            message_text = data.get("message", "")
            room_id = data.get("room_id") if not self.is_room_specific else self.room_id
            
            if not room_id:
                return
                
            # Mesajı veritabanına kaydet (engelleme kontrolü içerir)
            message_data, error = await self.save_message(room_id, message_text)
            
            if message_data:
                # Odadaki herkese mesajı gönder
                await self.channel_layer.group_send(
                    f'chat_{room_id}',
                    {
                        'type': 'chat_message',
                        'message': message_data
                    }
                )
                
                # Alıcı kullanıcılara bildirim gönder
                recipients = await self.get_room_recipients(room_id)
                for recipient_id in recipients:
                    if recipient_id != self.user.id:
                        await self.channel_layer.group_send(
                            f'chat_personal_{recipient_id}',
                            {
                                'type': 'new_message_notification',
                                'message': message_data,
                                'room_id': room_id
                            }
                        )
            else:
                # Mesaj gönderilemedi (engellenmiş kullanıcı veya diğer hata)
                await self.send(text_data=json.dumps({
                    'type': 'message_blocked',
                    'error': error or "Mesaj gönderilemedi.",
                    'room_id': room_id
                }))
        
        elif command == "mark_as_read":
            message_id = data.get("message_id")
            if message_id:
                success = await self.mark_message_as_read(message_id)
        
        elif command == "mark_room_as_read":
            room_id = data.get("room_id") if not self.is_room_specific else self.room_id
            print("girdi")
            if room_id:
                await self.mark_room_messages_as_read(room_id)
                await self.send(text_data=json.dumps({
                    "type": "room_messages_read",
                    "room_id": room_id
                }))
                
        elif command == "mark_all_as_read":
            # Tüm sohbetlerdeki okunmamış mesajları okundu olarak işaretle
            success = await self.mark_all_messages_as_read()
            if success:
                # Kullanıcıya bildirim gönder
                await self.send(text_data=json.dumps({
                    "type": "all_messages_read"
                }))
                # Güncel verileri gönder
                await self.send(text_data=json.dumps({
                    "type": "unread_count",
                    "count": 0
                }))
        
        elif command == "notify_messages_read":
            # ChatDetailContext'ten gelen mesaj okundu bildirimi
            room_id = data.get("room_id")
            message_id = data.get("message_id")
            
            if room_id:
                # Odadaki okunmamış mesaj sayısını hesapla
                unread_count = await self.get_room_unread_count(room_id)
                
                # Kullanıcının kişisel websocket'ine güncelleme gönder
                # Bu sayede ChatContext real-time olarak güncellenecek
                await self.channel_layer.group_send(
                    self.personal_group_name,
                    {
                        'type': 'messages_read_notification',
                        'room_id': room_id,
                        'unread_count': unread_count,
                        'message_id': message_id
                    }
                )
        
        elif command == "get_unread_count":
            count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                "type": "unread_count",
                "count": count
            }))
        
        elif command == "get_recent_rooms":
            rooms = await self.get_recent_rooms()
            await self.send(text_data=json.dumps({
                "type": "recent_rooms",
                "rooms": rooms
            }))
            
        elif command == "message_with_attachments":
            message_id = data.get("message_id")
            if message_id:
                try:
                    # Mesajı veritabanından al
                    message = await self.get_message_by_id(message_id)
                    if message:
                        # Odadaki herkese mesajı gönder
                        room_id = message.get('chat_room_id')
                        await self.channel_layer.group_send(
                            f'chat_{room_id}',
                            {
                                'type': 'chat_message',
                                'message': message
                            }
                        )
                        
                        # Alıcı kullanıcılara bildirim gönder
                        recipients = await self.get_room_recipients(room_id)
                        for recipient_id in recipients:
                            if recipient_id != self.user.id:  # Kendime bildirim gönderme
                                await self.channel_layer.group_send(
                                    f'chat_personal_{recipient_id}',
                                    {
                                        'type': 'new_message_notification',
                                        'message': message,
                                        'room_id': room_id
                                    }
                                )
                except Exception as e:
                    print(f"Mesaj işleme hatası: {str(e)}")

    async def chat_message(self, event):
        """Mesajı belirli bir odadaki tüm istemcilere gönder"""
        message = event['message']
        
        # Eğer bu kullanıcı mesajın gönderenı değilse ve şu anda bu odaya aktif olarak bağlıysa
        # mesajı otomatik olarak okundu işaretle
        if (self.is_room_specific and 
            message.get('sender_id') != self.user.id and 
            str(self.room_id) == str(message.get('chat_room_id', self.room_id))):
            
            # Mesajı otomatik olarak okundu işaretle
            await self.auto_mark_message_as_read(message.get('id'))
            
            # Mesaj verisini güncelle
            message['is_read'] = True
        
        await self.send(text_data=json.dumps({
            'type': 'new_message',  # 'chat_message' yerine 'new_message' kullan
            'message': message
        }))

    async def new_message_notification(self, event):
        """Yeni mesaj bildirimini kullanıcıya gönder"""
        message = event['message']
        room_id = event['room_id']
        
        # Eğer kullanıcı şu anda bu odaya bağlı değilse bildirim gönder
        # Bağlıysa zaten chat_message ile mesajı alacak
        if not self.is_room_specific or self.room_id != room_id:
            await self.send(text_data=json.dumps({
                'type': 'message_notification',
                'message': message,
                'room_id': room_id
            }))

    async def messages_read_notification(self, event):
        """Mesajlar okundu bildirimini kullanıcıya gönder"""
        room_id = event['room_id']
        unread_count = event['unread_count']
        message_id = event.get('message_id')
        
        await self.send(text_data=json.dumps({
            'type': 'messages_read_notification',
            'room_id': room_id,
            'unread_count': unread_count,
            'message_id': message_id
        }))

    @database_sync_to_async
    def get_user_by_id(self, user_id):
        """Kullanıcı ID'sine göre kullanıcıyı al"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def check_room_access(self, room_id):
        """Kullanıcının bu odaya erişimi var mı kontrol et"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            # Kullanıcı bu odanın katılımcısı mı?
            return room.participants.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False
    @database_sync_to_async
    def save_message(self, room_id, content):
        """Mesajı veritabanına kaydet ve JSON temsilini döndür"""
        try:
            chat_room = ChatRoom.objects.get(id=room_id)
            
            # Chat odasındaki diğer katılımcıları kontrol et
            other_participants = chat_room.participants.exclude(id=self.user.id)
            
            for participant in other_participants:
                # Engelleme durumu ve gizlilik ayarlarını kontrol et
                can_send, reason = can_message_user(self.user, participant)
                if not can_send:
                    return None, reason
            
            # Yeni mesaj oluştur
            message = Message.objects.create(
                chat_room=chat_room,
                sender=self.user,
                text=content,
                is_read=False
            )
            if not chat_room.is_active:
                chat_room.is_active = True
                chat_room.save(update_fields=['is_active'])
            # JSON temsilini oluştur
            message_data = {
                'id': message.id,
                'content': message.text,
                'sender_id': message.sender.id,
                'sender_name': message.sender.username,
                'sender_first_name': message.sender.first_name,
                'sender_last_name': message.sender.last_name,
                'sender_full_name': message.sender.get_full_name(),
                'sender_avatar': message.sender.profile.avatar.url if hasattr(message.sender, 'profile') and message.sender.profile.avatar else None,
                'created_at': message.timestamp.isoformat(),
                'is_read': message.is_read            }
            
            # Push notification gönder (offline kullanıcılar için)
            self.send_push_notification_for_message(message, chat_room, other_participants)
            
            return message_data, None
            
        except ChatRoom.DoesNotExist:
            return None, "Sohbet odası bulunamadı."

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mesajı okundu olarak işaretle"""
        try:
            message = Message.objects.get(id=message_id)
            message.is_read = True  # 'read_by.add' yerine 'is_read = True'
            message.save()  # Değişiklikleri kaydetmeyi unutmayın
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_room_messages_as_read(self, room_id=None):
        """Odadaki tüm mesajları okundu olarak işaretle"""
        if not room_id:
            room_id = self.room_id
            
        try:
            # Kullanıcının henüz okumadığı mesajları bul
            room = ChatRoom.objects.get(id=room_id)
            unread_messages = Message.objects.filter(
                chat_room=room,
                is_read=False
            ).exclude(sender=self.user)  # sender__id__ne yerine exclude kullan
            
            # Mesajları okundu olarak işaretle
            for message in unread_messages:
                message.is_read = True
                message.save()
                    
            return True
        except ChatRoom.DoesNotExist:
            return False    
        
    @database_sync_to_async
    def mark_all_messages_as_read(self):
        """Kullanıcının tüm sohbetlerindeki okunmamış mesajları okundu olarak işaretle"""
        try:
            # Kullanıcının katılımcı olduğu tüm chat odalarını al
            chat_rooms = ChatRoom.objects.filter(participants=self.user)
            
            # Tüm odalardaki okunmamış mesajları bul
            for room in chat_rooms:
                # Kullanıcının gönderdiği mesajlar hariç, okunmamış mesajları al
                unread_messages = Message.objects.filter(
                    chat_room=room,
                    is_read=False
                ).exclude(sender=self.user)
                
                # Mesajları okundu olarak işaretle
                for message in unread_messages:
                    message.is_read = True
                    message.save()
            
            return True
        except Exception as e:
            print(f"Tüm mesajları okundu olarak işaretleme hatası: {str(e)}")
            return False

    @database_sync_to_async
    def get_unread_count(self):
        """Kullanıcının okunmamış mesaj olan oda sayısını al"""
        # Kullanıcının katılımcı olduğu tüm odaları bul
        chat_rooms = ChatRoom.objects.filter(participants=self.user)
        
        # Okunmamış mesajı olan oda sayısını hesapla
        rooms_with_unread = 0
        for room in chat_rooms:
            has_unread = Message.objects.filter(
                chat_room=room,
                is_read=False
            ).exclude(sender=self.user).exists()  # Sadece var/yok kontrolü
            
            if has_unread:
                rooms_with_unread += 1
            
        return rooms_with_unread

    @database_sync_to_async
    def get_room_recipients(self, room_id):
        """Odadaki diğer katılımcıların ID'lerini al"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            return list(room.participants.values_list('id', flat=True))
        except ChatRoom.DoesNotExist:
            return []

    @database_sync_to_async
    def get_recent_rooms(self, limit=10):
        """Kullanıcının son mesajlaştığı odaları al"""
        # Kullanıcının katılımcı olduğu tüm odaları bul
        chat_rooms = ChatRoom.objects.filter(participants=self.user)

        # Her oda için son mesaj ve okunmamış mesaj sayısı
        room_data = []
        for room in chat_rooms:
            # Son mesaj
            last_message = Message.objects.filter(chat_room=room).order_by('-timestamp').first()
            
            # Okunmamış mesaj sayısı
            unread_count = Message.objects.filter(
                chat_room=room,
                is_read=False
            ).exclude(sender=self.user).count()
            
            # Diğer katılımcılar (1-1 sohbet için)
            other_participants = room.participants.exclude(id=self.user.id)
            
            # Oda adı: Katılımcıların isimlerinden oluştur
            room_name = ', '.join([p.username for p in other_participants]) if other_participants else 'Yeni Sohbet'
            
            room_info = {
                'id': room.id,
                'name': room_name,  # Doğrudan hesaplanmış adı kullan
                'unread_count': unread_count,
                'participants': [{'id': p.id, 'username': p.username} for p in other_participants],
                'updated_at': last_message.timestamp.isoformat() if last_message else room.created_at.isoformat() if hasattr(room, 'created_at') else timezone.now().isoformat()
            }
            
            # Son mesaj bilgisi
            if last_message:
                room_info['last_message'] = {
                    'id': last_message.id,
                    'content': last_message.text,
                    'sender_id': last_message.sender.id,
                    'sender_name': last_message.sender.username,
                    'sender_first_name': last_message.sender.first_name,
                    'sender_last_name': last_message.sender.last_name,
                    'sender_full_name': last_message.sender.get_full_name(),
                    'sender_avatar': last_message.sender.profile.avatar.url if hasattr(last_message.sender, 'profile') and last_message.sender.profile.avatar else None,
                    # 'created_at': last_message.timestamp.isoformat(),
                    'created_at': relative_time(last_message.timestamp),
                    'is_read': last_message.is_read
                }
            
            room_data.append(room_info)
            
        # Son mesaj tarihine göre sırala
        room_data.sort(key=lambda x: x.get('updated_at'), reverse=True)
        return room_data[:limit]

    @database_sync_to_async
    def get_message_by_id(self, message_id):
        """ID'ye göre mesaj bilgilerini getir"""
        try:
            message = Message.objects.get(id=message_id)

            # JSON temsilini oluştur
            message_data = {
                'id': message.id,
                'content': message.text,
                'sender_id': message.sender.id,
                'sender_name': message.sender.username,
                'sender_avatar': message.sender.profile.avatar.url if hasattr(message.sender, 'profile') and message.sender.profile.avatar else None,
                'created_at': message.timestamp.isoformat(),
                'is_read': message.is_read,
                'chat_room_id': message.chat_room.id
            }
            
            # Ekleri ekle
            attachments = []
            for attachment in message.attachments.all():
                attachments.append({
                    'id': attachment.id,
                    'file': settings.FRONTEND_URL + attachment.file.url,
                    'file_type': attachment.file_type
                })
            
            if attachments:
                message_data['attachments'] = attachments
            return message_data
            
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def get_room_unread_count(self, room_id):
        """Belirli bir odadaki okunmamış mesaj sayısını al"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            # Kullanıcının gönderdiği mesajlar hariç, okunmamış mesaj sayısı
            unread_count = Message.objects.filter(
                chat_room=room,
                is_read=False
            ).exclude(sender=self.user).count()
            
            return unread_count
        except ChatRoom.DoesNotExist:
            return 0
    @database_sync_to_async
    def auto_mark_message_as_read(self, message_id):
        """
        Kullanıcı sohbet odasına aktif olarak bağlıyken gelen mesajları 
        otomatik olarak okundu işaretle
        """
        try:
            message = Message.objects.get(id=message_id)
            
            # Mesaj zaten okunmuşsa veya kullanıcının kendi mesajıysa işlem yapma
            if message.is_read or message.sender == self.user:
                return False
            
            # Mesajı okundu olarak işaretle
            message.is_read = True
            message.save(update_fields=['is_read'])
              # Debug log
            print(f"Auto-marked message {message_id} as read for user {self.user.username}")
            print(f"Debug: Message chat room ID: {message.chat_room.id}")
            
            # Read receipt gönder (opsiyonel - sender'a bildirim)
            # Bu sayede sender mesajın okunduğunu anlayabilir
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_personal_{message.sender.id}",
                {
                    'type': 'message_read_receipt',
                    'message_id': message_id,
                    'reader_id': self.user.id,
                    'room_id': message.chat_room.id
                }
            )
              # ChatContext'e unread count güncellemesi gönder
            # Bu kullanıcının ChatContext'ine mesajın okunduğunu bildir
            room_unread_count = self.get_room_unread_count_sync(message.chat_room.id)
            print(f"Debug: Sending messages_read_notification to user {self.user.id} for room {message.chat_room.id} with unread_count {room_unread_count}")
            async_to_sync(channel_layer.group_send)(
                f"chat_personal_{self.user.id}",
                {
                    'type': 'messages_read_notification',
                    'room_id': message.chat_room.id,
                    'unread_count': room_unread_count,
                    'message_id': message_id
                }
            )
            
            return True
            
        except Message.DoesNotExist:
            print(f"Message {message_id} not found for auto-read marking")
            return False
        except Exception as e:
            print(f"Error auto-marking message {message_id} as read: {str(e)}")
            return False

    def get_room_unread_count_sync(self, room_id):
        """Belirli bir odadaki okunmamış mesaj sayısını al (senkron)"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            # Kullanıcının gönderdiği mesajlar hariç, okunmamış mesaj sayısı
            unread_count = Message.objects.filter(
                chat_room=room,
                is_read=False
            ).exclude(sender=self.user).count()
            
            return unread_count
        except ChatRoom.DoesNotExist:
            return 0
    async def message_read_receipt(self, event):
        """Read receipt bildirimini gönder"""
        message_id = event['message_id']
        reader_id = event['reader_id']
        room_id = event['room_id']
        
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': message_id,
            'reader_id': reader_id,
            'room_id': room_id
        }))
    
    def send_push_notification_for_message(self, message, chat_room, recipients):
        """
        Yeni mesaj için push notification gönder
        Sadece offline olan kullanıcılara gönderir
        """
        try:
            push_service = ExpoPushNotificationService()
            
            for recipient in recipients:
                # Kullanıcının aktif push token'ları var mı kontrol et
                tokens = push_service.get_user_tokens(recipient.id)
                
                if tokens:
                    # Push notification mesajını hazırla
                    title = f"Yeni mesaj - {message.sender.get_full_name() or message.sender.username}"
                    body = message.text[:100] + "..." if len(message.text) > 100 else message.text
                    
                    # Ekstra data
                    data = {
                        'type': 'chat_message',
                        'room_id': str(chat_room.id),
                        'message_id': str(message.id),
                        'sender_id': str(message.sender.id),
                        'sender_name': message.sender.get_full_name() or message.sender.username
                    }
                    
                    # Bulk notification gönder
                    push_service.send_bulk_notification(
                        tokens=tokens,
                                            title=title,
                        body=body,
                        data=data
                    )
                    
                    print(f"Chat: Push notification sent to {recipient.username} for message {message.id}")
                
        except Exception as e:
            print(f"Chat: Push notification error: {str(e)}")
            # Hata durumunda chat işlevselliği etkilenmesin
            pass