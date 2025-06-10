## Bildirimler (Notifications) API

### Genel Bakış

Bildirimler API, kullanıcı bildirimlerini yönetmek ve erişmek için aşağıdaki işlevleri sağlar:
- Bildirim listesini alma ve filtreleme
- Belirli bir bildirimi görüntüleme
- Bildirimleri okundu olarak işaretleme
- Tüm bildirimleri okundu olarak işaretleme
- Okunmamış bildirim sayısını alma
- Son bildirimleri alma
- Bildirim türlerini listeleme

### API Base URL
```
/api/v1/notifications/
```

### Kimlik Doğrulama Gereksinimleri

Tüm bildirim API endpointleri kimlik doğrulaması gerektirir. İsteklerde JWT erişim token'ınızı sağlamanız gereklidir.

```
Authorization: Bearer [access_token]
```

### Endpoint'ler

#### 1. Bildirim Listesi Alma

- **URL**: `/api/v1/notifications/notifications/`
- **Metod**: `GET`
- **Açıklama**: Kullanıcının bildirimlerini listeler.
- **Sorgu Parametreleri**:
  - `type`: Bildirim türü koduna göre filtreler (örn: "follow", "comment")
  - `is_read`: Okunma durumuna göre filtreler ("true" veya "false")
  - `page`: Sayfa numarası (pagination için)
  - `page_size`: Sayfa başına bildirim sayısı

- **Örnek Yanıt**:
```json
{
  "count": 15,
  "next": "http://example.com/api/v1/notifications/notifications/?page=2",
  "previous": null,
  "results": [
    {
      "id": 123,
      "sender": {
        "id": 456,
        "username": "kullanici_adi",
        "avatar_url": "/media/avatars/user.jpg",
        "full_name": "Ad Soyad"
      },
      "notification_type": {
        "id": 1,
        "code": "follow",
        "name": "Takip Bildirimi",
        "icon_class": "tabler-user-plus"
      },
      "title": "Yeni Takipçi",
      "text": "kullanici_adi sizi takip etmeye başladı.",
      "url": "/profile/kullanici_adi/",
      "is_read": false,
      "read_at": null,
      "created_at": "2025-04-30T15:30:45Z",
      "content_type": 12,
      "object_id": 34,
      "content_type_name": "follow",
      "parent_content_type": null,
      "parent_object_id": null,
      "parent_content_type_name": null
    },
    {
      "id": 124,
      "sender": {
        "id": 457,
        "username": "baska_kullanici",
        "avatar_url": "/media/avatars/user2.jpg",
        "full_name": "Başka Kullanıcı"
      },
      "notification_type": {
        "id": 2,
        "code": "comment",
        "name": "Yorum Bildirimi",
        "icon_class": "tabler-message-circle"
      },
      "title": "Yeni Yorum",
      "text": "baska_kullanici içeriğinize yorum yaptı.",
      "url": "/comment/comment/67/",
      "is_read": false,
      "read_at": null,
      "created_at": "2025-05-01T14:22:15Z",
      "content_type": 15,
      "object_id": 67,
      "content_type_name": "comment",
      "parent_content_type": 10,
      "parent_object_id": 42,
      "parent_content_type_name": "post"
    }
    // ... diğer bildirimler
  ]
}
```

#### 2. Bildirim Detayı Alma

- **URL**: `/api/v1/notifications/notifications/{id}/`
- **Metod**: `GET`
- **Açıklama**: Belirli bir bildirimin detaylarını gösterir.

- **Örnek Yanıt**:
```json
{
  "id": 124,
  "sender": {
    "id": 457,
    "username": "baska_kullanici",
    "avatar_url": "/media/avatars/user2.jpg",
    "full_name": "Başka Kullanıcı"
  },
  "notification_type": {
    "id": 2,
    "code": "comment",
    "name": "Yorum Bildirimi",
    "icon_class": "tabler-message-circle"
  },
  "title": "Yeni Yorum",
  "text": "baska_kullanici içeriğinize yorum yaptı.",
  "url": "/comment/comment/67/",
  "is_read": false,
  "read_at": null,
  "created_at": "2025-05-01T14:22:15Z",
  "content_type": 15,
  "object_id": 67,
  "content_type_name": "comment",
  "parent_content_type": 10,
  "parent_object_id": 42,
  "parent_content_type_name": "post"
}
```

#### 3. Bildirimi Okundu Olarak İşaretleme

- **URL**: `/api/v1/notifications/notifications/{id}/mark_as_read/`
- **Metod**: `POST`
- **Açıklama**: Belirli bir bildirimi okundu olarak işaretler.

- **Örnek Yanıt**:
```json
{
  "id": 123,
  "sender": {
    "id": 456,
    "username": "kullanici_adi",
    "avatar_url": "/media/avatars/user.jpg",
    "full_name": "Ad Soyad"
  },
  "notification_type": {
    "id": 1,
    "code": "follow",
    "name": "Takip Bildirimi",
    "icon_class": "tabler-user-plus"
  },
  "title": "Yeni Takipçi",
  "text": "kullanici_adi sizi takip etmeye başladı.",
  "url": "/profile/kullanici_adi/",
  "is_read": true,
  "read_at": "2025-05-01T10:15:30Z",
  "created_at": "2025-04-30T15:30:45Z"
}
```

#### 4. Tüm Bildirimleri Okundu Olarak İşaretleme

- **URL**: `/api/v1/notifications/notifications/mark_all_as_read/`
- **Metod**: `POST`
- **Açıklama**: Kullanıcının tüm okunmamış bildirimlerini okundu olarak işaretler.

- **Örnek Yanıt**:
```json
{
  "success": true,
  "count": 5,
  "message": "5 notifications marked as read."
}
```

#### 5. Okunmamış Bildirim Sayısını Alma

- **URL**: `/api/v1/notifications/notifications/unread_count/`
- **Metod**: `GET`
- **Açıklama**: Kullanıcının okunmamış bildirim sayısını döndürür.

- **Örnek Yanıt**:
```json
{
  "count": 3
}
```

#### 6. Son Bildirimleri Alma

- **URL**: `/api/v1/notifications/notifications/recent/`
- **Metod**: `GET`
- **Açıklama**: Kullanıcının en son 5 bildirimini döndürür.

- **Örnek Yanıt**: Bildirim listesine benzer şekilde, son 5 bildirim içeren bir liste

#### 7. Bildirim Türlerini Listeleme

- **URL**: `/api/v1/notifications/notification-types/`
- **Metod**: `GET`
- **Açıklama**: Sistemdeki tüm bildirim türlerini listeler.

- **Örnek Yanıt**:
```json
[
  {
    "id": 1,
    "code": "follow",
    "name": "Takip Bildirimi",
    "icon_class": "tabler-user-plus"
  },
  {
    "id": 2,
    "code": "comment",
    "name": "Yorum Bildirimi",
    "icon_class": "tabler-message-circle"
  },
  // ... diğer bildirim türleri
]
```

### Notlar

- Tüm API istekleri için JWT token ile kimlik doğrulama gereklidir.
- Bildirimlerin URL alanı, ilgili içeriğe direkt olarak yönlendirmek için kullanılabilir.
- Mobil uygulama için dikkat edilmesi gereken hususlar:
  - Periyodik olarak `/unread_count/` endpoint'ini kontrol ederek yeni bildirim olup olmadığını kontrol edin.
  - Kullanıcı bir bildirimi görüntülediğinde, `mark_as_read` endpoint'ini çağırarak bildirimi okundu olarak işaretleyin.
  - Kullanıcı bildirimleri temizlemek için "Tümünü Okundu İşaretle" düğmesine bastığında, `mark_all_as_read` endpoint'ini çağırın.