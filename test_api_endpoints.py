#!/usr/bin/env python
"""
Push Notification API Endpoints Test
Django server'ın çalışırken API endpoint'lerini test eder
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_push_notification_endpoints():
    """Push notification API endpoint'lerini test et"""
    print("🌐 Push Notification API Endpoints Test")
    print("=" * 50)
    
    # Test token (sahte)
    test_token = "ExponentPushToken[test-api-1234567890]"
    
    print("1️⃣ Token Register Test...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/push-notifications/register/", {
            "expo_token": test_token,
            "device_name": "API Test Device"
        })
        print(f"✅ Register Status: {response.status_code}")
        if response.status_code == 201:
            print(f"✅ Response: {response.json()}")
        else:
            print(f"⚠️ Response: {response.text}")
    except Exception as e:
        print(f"❌ Register Error: {str(e)}")
    
    print("\n2️⃣ Token List Test...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/push-notifications/tokens/")
        print(f"✅ List Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Token count: {len(data.get('results', []))}")
        else:
            print(f"⚠️ Response: {response.text}")
    except Exception as e:
        print(f"❌ List Error: {str(e)}")
    
    print("\n3️⃣ Test Notification Send...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/push-notifications/test/", {
            "title": "API Test",
            "body": "API üzerinden test bildirimi",
            "data": json.dumps({"test": True})
        })
        print(f"✅ Test Send Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Response: {response.json()}")
        else:
            print(f"⚠️ Response: {response.text}")
    except Exception as e:
        print(f"❌ Test Send Error: {str(e)}")
    
    print("\n4️⃣ Bulk Notification Test...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/push-notifications/bulk/", {
            "user_ids": [1, 2],  # İlk 2 kullanıcı
            "title": "Bulk Test",
            "body": "Toplu bildirim testi",
            "data": json.dumps({"bulk": True})
        })
        print(f"✅ Bulk Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Response: {response.json()}")
        else:
            print(f"⚠️ Response: {response.text}")
    except Exception as e:
        print(f"❌ Bulk Error: {str(e)}")

def check_django_server():
    """Django server'ın çalışıp çalışmadığını kontrol et"""
    try:
        response = requests.get(f"{BASE_URL}/admin/", timeout=5)
        return response.status_code in [200, 302]  # 302 redirect normal
    except:
        return False

if __name__ == "__main__":
    if not check_django_server():
        print("❌ Django server çalışmıyor!")
        print("📋 Önce Django server'ı başlatın:")
        print("   cd c:\\Users\\Resat\\Desktop\\universite\\core\\web")
        print("   python manage.py runserver")
        exit(1)
    
    test_push_notification_endpoints()
    
    print("\n" + "=" * 50)
    print("📝 Sonuç:")
    print("✅ API endpoint'leri test edildi")
    print("🔧 Django admin panelinden de test edebilirsiniz:")
    print(f"   {BASE_URL}/admin/")
