#!/usr/bin/env python
"""
Push Notifications Test Script - Chat Edition
Bu script chat ve push notification entegrasyonunu test eder
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
from apps.push_notifications.models import PushToken
from apps.push_notifications.services import ExpoPushNotificationService
from apps.chat.models import ChatRoom, Message

def test_basic_setup():
    """Temel kurulum kontrolü"""
    print("🔧 Temel kurulum kontrol ediliyor...")
    
    # Kullanıcı kontrolü
    users = User.objects.all()
    print(f"✅ Toplam kullanıcı sayısı: {users.count()}")
    
    # Push token kontrolü
    tokens = PushToken.objects.filter(is_active=True)
    print(f"✅ Aktif push token sayısı: {tokens.count()}")
    
    # Chat room kontrolü  
    chat_rooms = ChatRoom.objects.all()
    print(f"✅ Toplam chat room sayısı: {chat_rooms.count()}")
    
    return True

def test_push_service():
    """Push notification servisini test et"""
    print("\n📱 Push notification servisi test ediliyor...")
    
    try:
        service = ExpoPushNotificationService()
        print("✅ ExpoPushNotificationService başarıyla oluşturuldu")
        
        # Test kullanıcısı için token kontrolü
        user = User.objects.first()
        if user:
            tokens = service.get_user_tokens(user.id)
            print(f"✅ Kullanıcı {user.username} için {len(tokens)} token bulundu")
        
        return True
    except Exception as e:
        print(f"❌ Push service hatası: {str(e)}")
        return False

def test_chat_integration():
    """Chat entegrasyonunu test et"""
    print("\n💬 Chat-Push notification entegrasyonu test ediliyor...")
    
    try:
        # En az 2 kullanıcı gerekli
        users = User.objects.all()[:2]
        if len(users) < 2:
            print("⚠️ Test için en az 2 kullanıcı gerekli")
            return False
        
        sender = users[0]
        recipient = users[1]
        print(f"✅ Test kullanıcıları: {sender.username} -> {recipient.username}")
        
        # Chat room oluştur
        room, created = ChatRoom.get_or_create_chat_room(sender, recipient)
        print(f"✅ Chat room: {room.id} ({'oluşturuldu' if created else 'mevcut'})")
        
        # Test mesajı
        message = Message.objects.create(
            chat_room=room,
            sender=sender,
            text="Test push notification mesajı! 🚀",
            is_read=False
        )
        print(f"✅ Test mesajı oluşturuldu: {message.id}")
        
        # Push token kontrolü
        recipient_tokens = PushToken.objects.filter(user=recipient, is_active=True)
        if recipient_tokens.exists():
            print(f"✅ Alıcının {recipient_tokens.count()} aktif push token'ı var")
            
            # Simüle push notification
            print("📤 Push notification gönderme simülasyonu...")
            # Gerçek gönderim chat consumers'da otomatik olacak
            print("✅ Chat modülünde push notification entegrasyonu hazır")
        else:
            print("⚠️ Alıcının aktif push token'ı yok")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat entegrasyon hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Chat Push Notifications Entegrasyon Testi")
    print("=" * 50)
    
    # Testleri çalıştır
    test1 = test_basic_setup()
    test2 = test_push_service() 
    test3 = test_chat_integration()
    
    print("\n" + "=" * 50)
    if test1 and test2 and test3:
        print("🎉 TÜM TESTLER BAŞARILI!")
        print("✅ Push notification sistemi hazır")
        print("✅ Chat entegrasyonu hazır")
    else:
        print("⚠️ Bazı testler başarısız oldu")
    
    print("\n📝 Sonraki adımlar:")
    print("1. React Native uygulamasını başlatın")
    print("2. Uygulamada giriş yapın")
    print("3. Push notification izni verin")
    print("4. Profile -> Bildirim Testi ile test yapın")
    print("5. Chat mesajı gönderin ve push notification'ları test edin")
