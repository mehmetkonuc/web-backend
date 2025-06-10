# Üniversite Platformu - PRD (Product Requirements Document)

## İçerik

1. [Proje Genel Bakış](#1-proje-genel-bakış)
2. [Mimari Yapı](#2-mimari-yapı)
3. [Uygulama Modülleri](#3-uygulama-modülleri)
4. [Bildirim Sistemi](#4-bildirim-sistemi)
5. [Kullanıcı Arayüzü](#5-kullanıcı-arayüzü)
6. [Kullanıcı İşlemleri](#6-kullanıcı-işlemleri)
7. [Veri Modelleri](#7-veri-modelleri)
8. [WebSocket İletişimi](#8-websocket-i̇letişimi)
9. [Gelecek Özellikler](#9-gelecek-özellikler)

## 1. Proje Genel Bakış

**Proje Adı:** Üniversite Platformu  
**Platform Türü:** Web Uygulaması  
**Teknoloji Stack:** Django, Django Channels, WebSocket, Redis, Bootstrap

Bu platform, üniversite ortamında kullanıcıların etkileşimde bulunabileceği, gerçek zamanlı bildirimler alabileceği ve çeşitli içerikler paylaşabileceği web tabanlı bir uygulamadır. Kullanıcılar platforma kaydolabilir, profil oluşturabilir, diğer kullanıcıları takip edebilir ve çeşitli etkileşimlerde bulunabilirler.

## 2. Mimari Yapı

### Backend

- **Framework:** Django 5.x
- **Asenkron İletişim:** Django Channels
- **Veritabanı:** PostgreSQL (varsayılan)
- **Cache Sistemi:** Redis (WebSocket kanalları için)
- **Statik Dosya Sunumu:** Whitenoise

### Frontend

- **CSS Framework:** Bootstrap 5
- **JavaScript:** Vanilla JS
- **İkon Seti:** Tabler Icons
- **Responsive Tasarım:** Tüm cihazlar için uyumlu

### Deployment

- **ASGI Server:** Daphne/Uvicorn
- **WebSocket Desteği:** Django Channels ile ASGI
- **Statik Dosyalar:** Whitenoise ile servis edilmekte

## 3. Uygulama Modülleri

Proje, aşağıdaki Django uygulamalarından oluşmaktadır:

### 1. Guest (Ziyaretçi)

- Kayıt olma
- Giriş yapma
- Şifre sıfırlama
- Ana sayfa yönlendirme

### 2. Profiles (Profiller)

- Kullanıcı profilleri
- Profil düzenleme
- Kullanıcı takip sistemi

### 3. Members (Üyeler)

- Üye listesi
- Üye detayları
- Üye etkileşimleri

### 4. Notifications (Bildirimler)

- Gerçek zamanlı bildirim sistemi
- Bildirim tipleri ve yönetimi
- WebSocket ile anlık bildirim dağıtımı

### 5. Dataset (Veri Seti)

- Veri yönetimi
- İçerik paylaşımı

## 4. Bildirim Sistemi

Bildirim sistemi, platformun en temel özelliklerinden biridir ve Django Channels kullanılarak WebSocket üzerinden gerçek zamanlı olarak çalışır.

### Bildirim Modelleri

#### NotificationType

- `code` : Bildirim türü kodu (örn. "follow", "like")
- `name` : Bildirim türü adı
- `description` : Açıklama
- `icon_class` : Bildirim ikonunun CSS sınıfı

#### Notification

- `recipient` : Bildirimi alan kullanıcı (ForeignKey -> User)
- `sender` : Bildirimi gönderen kullanıcı (ForeignKey -> User, opsiyonel)
- `notification_type` : Bildirim türü (ForeignKey -> NotificationType)
- `content_type` ve `object_id` : İlişkili içerik (Generic Foreign Key)
- `title` : Bildirim başlığı
- `text` : Bildirim metni
- `url` : Tıklanınca yönlendirilecek URL
- `is_read` : Okundu durumu
- `read_at` : Okunma zamanı
- `created_at` ve `updated_at` : Oluşturma ve güncelleme zamanları

### Bildirim Tipleri

1. **Takip Bildirimi (`follow`)**: Bir kullanıcı sizi takip ettiğinde
2. **Beğeni Bildirimi (`like`)**: İçeriğiniz beğenildiğinde

### Bildirim Akışı

1. Model üzerinde yeni bir bildirim oluşturulur
2. `save()` metodunda, yeni bildirim WebSocket üzerinden alıcıya gönderilir
3. Alıcı tarafta JavaScript ile bildirim yakalanıp UI güncellenir
4. Kullanıcı bildirimleri okuyabilir, okundu olarak işaretleyebilir

## 5. Kullanıcı Arayüzü

### Bildirim Arayüzü Bileşenleri

- **Bildirim Dropdown**: Üst menüde bildirim simgesi ve açılır dropdown
- **Bildirim Rozeti**: Okunmamış bildirim sayısını gösteren rozet
- **Bildirim Listesi**: Dropdown içinde gösterilen bildirim listesi
- **Okundu/Okunmadı İşaretleme**: Bildirimleri okundu olarak işaretleme butonları
- **Tümünü Okundu İşaretle**: Tüm bildirimleri tek seferde okundu olarak işaretleme butonu

### Sayfa Şablonları

- `base.html`: Ana şablon
- `header.html`: Üst menü ve bildirim arayüzü
- `sidebar.html`: Yan menü
- `footer.html`: Alt bilgi alanı

### Bildirim Şablonları

- `notifications/list.html`: Tüm bildirimleri listeleyen sayfa
- `notifications/detail.html`: Bildirim detayı sayfası

## 6. Kullanıcı İşlemleri

### Kimlik Doğrulama

- Kayıt olma (çok aşamalı kayıt formu)
- Giriş yapma 
- Şifre sıfırlama
- Çıkış yapma

### Profil İşlemleri

- Profil görüntüleme
- Profil düzenleme
- Avatar yükleme
- Kullanıcı takip etme/takipten çıkma

### Bildirim İşlemleri

- Bildirimleri görüntüleme
- Bildirimleri filtreleme (tür, okundu/okunmadı)
- Bildirim okundu işaretleme
- Tüm bildirimleri okundu işaretleme

## 7. Veri Modelleri

### User (Django'nun Dahili User Modeli)

- Django'nun varsayılan kullanıcı modeli kullanılmakta

### Profile

- Kullanıcı profil bilgileri
- Avatar, isim, soyisim, vb. bilgiler

### Notification & NotificationType

- Yukarıda açıklandığı gibi bildirim modelleri

## 8. WebSocket İletişimi

### Bildirim Consumer

`NotificationConsumer` sınıfı, WebSocket üzerinden bildirim iletişimini yönetir:

#### Bağlantı Yönetimi
- `connect()`: Kullanıcı bağlandığında kanal grubuna dahil etme
- `disconnect()`: Kullanıcı ayrıldığında gruptan çıkarma

#### Komutlar
- `mark_as_read`: Bildirimi okundu olarak işaretleme
- `get_unread_count`: Okunmamış bildirim sayısını alma
- `get_notifications`: Bildirimleri listeler
- `mark_all_as_read`: Tüm bildirimleri okundu olarak işaretleme

#### Mesaj Tipleri
- `notification_message`: Yeni bildirim gönderme
- `notification_read`: Bildirim okundu bilgisi
- `unread_count`: Okunmamış bildirim sayısı
- `notifications_list`: Bildirim listesi
- `all_notifications_read`: Tüm bildirimleri okundu işaretleme

### Frontend WebSocket İletişimi

`notifications.js` dosyası, frontend tarafında WebSocket iletişimini yönetir:

- WebSocket bağlantısı kurma ve yönetme
- Komutları gönderme (get_notifications, mark_as_read, vb.)
- Gelen mesajları işleme ve UI'ı güncelleme

## 9. Gelecek Özellikler

### Kısa Vadeli Hedefler

- **Bildirim Tercihleri**: Kullanıcıların hangi bildirimleri alacağını seçebilmesi
- **Mobil Görünüm İyileştirmeleri**: Daha iyi mobil deneyim
- **Tarayıcı Bildirimleri**: Push notification desteği

### Orta Vadeli Hedefler

- **İçerik Filtreleme**: Gelişmiş içerik filtreleme seçenekleri
- **Arama Fonksiyonu**: İçerikler ve kullanıcılar için arama özelliği
- **Gruplar**: Kullanıcı grupları oluşturma imkanı

### Uzun Vadeli Hedefler

- **Mobil Uygulama**: Native mobil uygulama
- **API Genişletme**: 3. parti entegrasyonlar için API
- **Analitik ve Raporlama**: Kullanım istatistikleri ve raporlama

---

*Bu PRD dokümanı, projenin mevcut durumu ve geliştirme planları hakkında genel bir bakış sunmaktadır. Geliştirme süreci boyunca güncellenecek ve genişletilecektir.*

*Son güncelleme: 06.04.2025*