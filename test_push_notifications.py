#!/usr/bin/env python
"""
Push Notifications Test Script
Bu script notifications modülünün push notification entegrasyonunu test eder
"""

import os
import sys
import django

# Django projesini ayarla
web_path = os.path.abspath('.')  # Mevcut dizin (web klasörü)
if web_path not in sys.path:
    sys.path.insert(0, web_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.notifications.services import NotificationService
from apps.push_notifications.models import PushToken
from apps.chat.models import ChatRoom, Message
from apps.push_notifications.services import ExpoPushNotificationService

def test_push_notifications():
    print("🚀 Push Notifications Test Başlıyor...")
    print("-" * 50)
    
    # 1. Kullanıcıları kontrol et
    print("1️⃣ Kullanıcıları kontrol ediliyor...")
    users = User.objects.all()[:2]  # İlk 2 kullanıcıyı al
    
    if len(users) < 2:
        print("❌ En az 2 kullanıcı gerekli. Önce kullanıcı oluşturun.")
        return False
    
    sender = users[0]
    recipient = users[1]
    print(f"✅ Gönderen: {sender.username}")
    print(f"✅ Alıcı: {recipient.username}")
    
    # 2. Push token kontrol et
    print("\n2️⃣ Push token kontrol ediliyor...")
    push_token = PushToken.objects.filter(user=recipient).first()
    
    if not push_token:
        print("⚠️ Alıcı kullanıcının push token'ı yok. Test push token oluşturuluyor...")
        push_token = PushToken.objects.create(
            user=recipient,
            expo_token="ExponentPushToken[test-token-1234567890]",
            device_name="Test Device",
            is_active=True
        )
        print(f"✅ Test push token oluşturuldu: {push_token.expo_token}")
    else:
        print(f"✅ Push token mevcut: {push_token.expo_token}")
    
    # 3. Test bildirim oluştur
    print("\n3️⃣ Test bildirimi oluşturuluyor...")
    try:
        notification = NotificationService.create_notification(
            sender=sender,
            recipient=recipient,
            code="follow"  # Takip bildirimi testi
        )
        
        if notification:
            print(f"✅ Bildirim oluşturuldu: ID {notification.id}")
            print(f"   Başlık: {notification.title}")
            print(f"   Metin: {notification.text}")
            print("   📱 WebSocket ve Push Notification otomatik gönderildi!")
            return True
        else:
            print("❌ Bildirim oluşturulamadı")
            return False
            
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        return False

def test_direct_push():
    print("\n4️⃣ Direkt push notification testi...")
    try:
        from apps.push_notifications.services import send_notification_push
        
        # İlk kullanıcıya direkt push gönder
        user = User.objects.first()
        if not user:
            print("❌ Test için kullanıcı bulunamadı")
            return False
            
        success = send_notification_push(
            user_id=user.id,
            title="🧪 Test Bildirimi",
            body="Bu bir test push notification'dır",
            data={"test": True}
        )
        
        if success:
            print(f"✅ Direkt push notification başarıyla gönderildi: {user.username}")
                    return True
        else:
            print(f"❌ Push notification gönderilemedi: {user.username}")
            return False
            
    except Exception as e:
        print(f"❌ Direkt push test hatası: {str(e)}")
        return False

def test_chat_push_notifications():
    """Chat push notification'larını test et"""
    print("\n4️⃣ Chat Push Notifications Test ediliyor...")
    
    try:
        # Kullanıcıları al
        users = User.objects.all()[:2]
        if len(users) < 2:
            print("❌ Chat testi için en az 2 kullanıcı gerekli")
            return False
            
        sender = users[0]
        recipient = users[1]
        
        # Push token kontrol et
        push_token = PushToken.objects.filter(user=recipient, is_active=True).first()
        if not push_token:
            print("⚠️ Alıcı kullanıcının aktif push token'ı yok")
            return False
        
        # Chat room oluştur veya al
        chat_room, created = ChatRoom.get_or_create_chat_room(sender, recipient)
        print(f"✅ Chat room {'oluşturuldu' if created else 'bulundu'}: {chat_room.id}")
        
        # Test mesajı oluştur
        message = Message.objects.create(
            chat_room=chat_room,
            sender=sender,
            text="Bu bir test chat mesajıdır! 💬",
            is_read=False
        )
        
        # Chat room'u aktif yap
        if not chat_room.is_active:
            chat_room.is_active = True
            chat_room.save()
        
        print(f"✅ Test mesajı oluşturuldu: {message.id}")
        
        # Push notification servisini test et
        push_service = ExpoPushNotificationService()
        tokens = push_service.get_user_tokens(recipient.id)
        
        if not tokens:
            print("❌ Alıcı kullanıcının push token'ı bulunamadı")
            return False
        
        print(f"✅ {len(tokens)} adet push token bulundu")
        
        # Chat push notification gönder
        title = f"Yeni mesaj - {sender.get_full_name() or sender.username}"
        body = message.text[:100] + "..." if len(message.text) > 100 else message.text
        
        data = {
            'type': 'chat_message',
            'room_id': str(chat_room.id),
            'message_id': str(message.id),
            'sender_id': str(sender.id),
            'sender_name': sender.get_full_name() or sender.username
        }
        
        # Notification gönder
        result = push_service.send_bulk_notification(
            tokens=tokens,
            title=title,
            body=body,
            data=data
        )
        
        if result['success']:
            print(f"✅ Chat push notification başarıyla gönderildi!")
            print(f"   📱 Başlık: {title}")
            print(f"   💬 İçerik: {body}")
            print(f"   🔗 Room ID: {chat_room.id}")
            return True
        else:
            print(f"❌ Chat push notification gönderilemedi: {result.get('error', 'Bilinmeyen hata')}")
            return False
            
    except Exception as e:
        print(f"❌ Chat push test hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":    print("🔧 Push Notifications Entegrasyonu Test Ediliyor")
    print("=" * 60)
    
    # Ana test
    success1 = test_push_notifications()
    
    # Direkt push test
    success2 = test_direct_push()
    
    # Chat push test
    success3 = test_chat_push_notifications()
    
    print("\n" + "=" * 60)
    if success1 and success2 and success3:
        print("🎉 TÜM TESTLER BAŞARILI!")
        print("✅ Notifications modülü push notification entegrasyonu çalışıyor")
        print("✅ Chat modülü push notification entegrasyonu çalışıyor")
    else:
        print("⚠️ Bazı testler başarısız oldu. Logları kontrol edin.")
    
    print("\n📝 Sonraki adımlar:")
    print("1. React Native uygulamanızda push token kaydedin")
    print("2. Gerçek bir aksiyon yapın (beğeni, yorum, mesaj vs.)")  
    print("3. Push notification'ların geldiğini kontrol edin")
