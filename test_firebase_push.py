#!/usr/bin/env python
"""
Firebase Push Notification Test Script

Bu script Firebase Cloud Messaging (FCM) sisteminizi test etmek için kullanılır.
"""

import os
import sys
import django
from django.conf import settings
from django.utils import timezone

# Django ayarlarını yükle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.chat.models import ChatRoom, Message
from apps.push_notifications.models import FCMToken
from apps.push_notifications.services import firebase_service


def create_test_users():
    """Test kullanıcıları oluşturur"""
    print("🔄 Test kullanıcıları oluşturuluyor...")
    
    # Gönderici kullanıcı
    sender, created = User.objects.get_or_create(
        username='test_sender',
        defaults={
            'email': 'sender@test.com',
            'first_name': 'Test',
            'last_name': 'Gönderici'
        }
    )
    if created:
        sender.set_password('testpass123')
        sender.save()
    
    # Alıcı kullanıcı
    recipient, created = User.objects.get_or_create(
        username='test_recipient',
        defaults={
            'email': 'recipient@test.com',
            'first_name': 'Test',
            'last_name': 'Alıcı'
        }
    )
    if created:
        recipient.set_password('testpass123')
        recipient.save()
    
    print(f"✅ Gönderici: {sender.username} ({sender.get_full_name()})")
    print(f"✅ Alıcı: {recipient.username} ({recipient.get_full_name()})")
    
    return sender, recipient


def create_test_fcm_token(user, token="test_fcm_token_12345"):
    """Test FCM token'ı oluşturur"""
    print(f"🔄 {user.username} için FCM token oluşturuluyor...")
    
    fcm_token, created = FCMToken.objects.update_or_create(
        user=user,
        platform='android',
        defaults={
            'fcm_token': token,
            'device_info': {
                'model': 'Test Device',
                'version': '1.0',
                'platform': 'android'
            },
            'device_name': 'Test Android Device',
            'is_active': True
        }
    )
    
    action = "oluşturuldu" if created else "güncellendi"
    print(f"✅ FCM Token {action}: {token[:20]}...")
    
    return fcm_token


def test_direct_notification():
    """Doğrudan notification testi"""
    print("\n" + "="*60)
    print("🔔 DOĞRUDAN NOTIFICATION TESTI")
    print("="*60)
    
    sender, recipient = create_test_users()
    fcm_token = create_test_fcm_token(recipient)
    
    # Notification gönder
    print("🔄 Push notification gönderiliyor...")
    
    success = firebase_service.send_notification(
        user_id=recipient.id,
        title="Test Notification",
        body="Bu bir test mesajıdır. Firebase FCM sistemi çalışıyor!",
        data={
            'type': 'test',
            'sender_id': str(sender.id),
            'test_data': 'success'
        }
    )
    
    if success:
        print("✅ Push notification başarıyla gönderildi!")
    else:
        print("❌ Push notification gönderilemedi!")
    
    return success


def test_chat_notification():
    """Chat mesajı için notification testi"""
    print("\n" + "="*60)
    print("💬 CHAT NOTIFICATION TESTI")
    print("="*60)
    
    sender, recipient = create_test_users()
    fcm_token = create_test_fcm_token(recipient)
    
    # Chat room oluştur
    print("🔄 Chat room oluşturuluyor...")
    chat_room, created = ChatRoom.objects.get_or_create(
        user1=sender,
        user2=recipient
    )
    
    print(f"✅ Chat room {'oluşturuldu' if created else 'bulundu'}: {chat_room.id}")
    
    # Test mesajı oluştur
    print("🔄 Test mesajı oluşturuluyor...")
    message = Message.objects.create(
        room=chat_room,
        sender=sender,
        text="Merhaba! Bu bir test mesajıdır. 🚀"
    )
    
    if not chat_room.is_active:
        chat_room.is_active = True
        chat_room.save()
    
    print(f"✅ Test mesajı oluşturuldu: {message.id}")
    
    # Chat notification gönder
    print("🔄 Chat push notification gönderiliyor...")
    
    title = f"Yeni mesaj - {sender.get_full_name() or sender.username}"
    body = message.text[:100] + "..." if len(message.text) > 100 else message.text
    
    data = {
        'type': 'chat_message',
        'room_id': str(chat_room.id),
        'message_id': str(message.id),
        'sender_id': str(sender.id),
        'sender_name': sender.get_full_name() or sender.username
    }
    
    success = firebase_service.send_notification(
        user_id=recipient.id,
        title=title,
        body=body,
        data=data
    )
    
    if success:
        print("✅ Chat push notification başarıyla gönderildi!")
    else:
        print("❌ Chat push notification gönderilemedi!")
    
    return success


def test_bulk_notification():
    """Toplu notification testi"""
    print("\n" + "="*60)
    print("📢 TOPLU NOTIFICATION TESTI")
    print("="*60)
    
    # Birden fazla kullanıcı oluştur
    users = []
    for i in range(3):
        user, created = User.objects.get_or_create(
            username=f'bulk_test_user_{i}',
            defaults={
                'email': f'bulk{i}@test.com',
                'first_name': f'Bulk{i}',
                'last_name': 'Test'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
        
        # FCM token oluştur
        create_test_fcm_token(user, f"bulk_test_token_{i}_12345")
        users.append(user)
        print(f"✅ Kullanıcı {i+1}: {user.username}")
    
    # Toplu notification gönder
    print("🔄 Toplu push notification gönderiliyor...")
    
    user_ids = [user.id for user in users]
    results = firebase_service.send_bulk_notifications(
        user_ids=user_ids,
        title="Toplu Test Notification",
        body="Bu toplu gönderim testidir. Herkese gönderildi!",
        data={
            'type': 'bulk_test',
            'timestamp': str(timezone.now())
        }
    )
    
    print(f"✅ Toplu notification sonuçları:")
    print(f"   - Başarılı: {results.get('success', 0)}")
    print(f"   - Başarısız: {results.get('failed', 0)}")
    
    return results.get('success', 0) > 0


def main():
    """Ana test fonksiyonu"""
    print("🔥 FIREBASE PUSH NOTIFICATION TESTI BAŞLADI")
    print("="*60)
    
    # Firebase servisinin durumunu kontrol et
    if not firebase_service.app:
        print("❌ Firebase servisi başlatılmamış!")
        print("   Firebase service account key dosyasını kontrol edin.")
        return False
    else:
        print("✅ Firebase servisi aktif")
    
    # Testleri çalıştır
    test_results = []
    
    # Test 1: Doğrudan notification
    test_results.append(test_direct_notification())
    
    # Test 2: Chat notification
    test_results.append(test_chat_notification())
    
    # Test 3: Toplu notification
    test_results.append(test_bulk_notification())
    
    # Sonuçları göster
    print("\n" + "="*60)
    print("📊 TEST SONUÇLARI")
    print("="*60)
    
    success_count = sum(test_results)
    total_tests = len(test_results)
    
    print(f"✅ Başarılı testler: {success_count}/{total_tests}")
    print(f"❌ Başarısız testler: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("\n🎉 TÜM TESTLER BAŞARILI!")
        print("Firebase push notification sistemi düzgün çalışıyor.")
    else:
        print("\n⚠️  BAZI TESTLER BAŞARISIZ!")
        print("Firebase konfigürasyonunu ve service account key'i kontrol edin.")
    
    return success_count == total_tests


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ TEST HATASI: {str(e)}")
        import traceback
        traceback.print_exc()
