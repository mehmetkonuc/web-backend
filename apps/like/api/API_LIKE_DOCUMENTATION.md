# Like API Dokümantasyonu

Bu API, sosyal medya platformunda beğeni (like) işlemlerini yönetmek için kullanılır. GenericForeignKey yapısıyla herhangi bir içerik tipine (post, yorum, etkinlik, vb.) beğeni eklenebilir ve bu beğeniler üzerinde çeşitli işlemler gerçekleştirilebilir.

## Base URL

```
/api/v1/likes/
```

## Doğrulama ve Yetkilendirme

Tüm endpointler için JWT kimlik doğrulaması gereklidir. Yetkilendirme başlığına bir erişim tokenı ekleyin:

```
Authorization: Bearer {access_token}
```

## GenericForeignKey Kullanımı Hakkında

Like API'si, Django'nun ContentType framework'ünü kullanarak farklı model tiplerinin beğenilmesini sağlar.

Her API çağrısında:
- `content_type_id`: Beğenilecek içerik tipinin ID'si (ContentType tablosundan)
- `object_id`: Beğenilecek içerik nesnesinin ID'si

Bu değerleri öğrenmek için Django shell'de şu kodları çalıştırabilirsiniz:

```python
from django.contrib.contenttypes.models import ContentType
from apps.post.models import Post
from apps.comment.models import Comment

# Post modeli için content_type_id'yi alın
post_content_type_id = ContentType.objects.get_for_model(Post).id
print(post_content_type_id)  # Örneğin: 15

# Comment modeli için content_type_id'yi alın
comment_content_type_id = ContentType.objects.get_for_model(Comment).id
print(comment_content_type_id)  # Örneğin: 16
```

## Beğeni İşlemleri

### Beğeni Listeleme

**Endpoint:** `GET /likes/`

**Açıklama:** Belirli bir içerik nesnesine ait tüm beğenileri listeler.

**Query Parametreleri:**
- `content_type_id`: İçerik tipinin ID'si (opsiyonel)
- `object_id`: İçerik nesnesinin ID'si (opsiyonel)
- `user_id`: Kullanıcı ID'si (opsiyonel)
- `page`: Sayfa numarası (varsayılan: 1)
- `ordering`: Sıralama kriteri (örn: "-created_at")

**Yanıt:**

```json
{
  "count": 50,
  "next": "http://example.com/api/v1/likes/likes/?content_type_id=15&object_id=5&page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 10,
        "username": "ahmet",
        "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
        "full_name": "Ahmet Yılmaz",
        "is_verified": true
      },
      "created_at": "2025-04-20T12:30:00Z"
    },
    {
      "id": 2,
      "user": {
        "id": 12,
        "username": "mehmet",
        "avatar_url": "http://example.com/media/avatars/mehmet.jpg",
        "full_name": "Mehmet Demir",
        "is_verified": false
      },
      "created_at": "2025-04-20T13:45:00Z"
    }
  ]
}
```

### Beğeni Oluşturma

**Endpoint:** `POST /likes/`

**Açıklama:** Yeni bir beğeni oluşturur.

**İstek:**

```json
{
  "content_type_id": 15,
  "object_id": 5
}
```

**Yanıt:**

```json
{
  "id": 75,
  "user": {
    "id": 10,
    "username": "ahmet",
    "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
    "full_name": "Ahmet Yılmaz",
    "is_verified": true
  },
  "created_at": "2025-04-24T16:30:00Z"
}
```

### Beğeni Silme

**Endpoint:** `DELETE /likes/{id}/`

**Açıklama:** Var olan bir beğeniyi siler. Sadece beğeniyi oluşturan kullanıcı tarafından yapılabilir.

### Beğeni Durumunu Değiştirme (Toggle)

**Endpoint:** `POST /likes/toggle/`

**Açıklama:** İçerik zaten beğenilmişse beğeniyi kaldırır, beğenilmemişse beğeni ekler.

**İstek:**

```json
{
  "content_type_id": 15,
  "object_id": 5
}
```

**Yanıt (Beğeni Eklendiğinde):**

```json
{
  "detail": "Like added.",
  "liked": true,
  "data": {
    "id": 80,
    "user": {
      "id": 10,
      "username": "ahmet",
      "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
      "full_name": "Ahmet Yılmaz",
      "is_verified": true
    },
    "created_at": "2025-04-24T16:35:00Z"
  }
}
```

**Yanıt (Beğeni Kaldırıldığında):**

```json
{
  "detail": "Like removed.",
  "liked": false
}
```

### Beğeni Kontrolü

**Endpoint:** `GET /likes/check/`

**Açıklama:** Kullanıcının belirli bir içeriği beğenip beğenmediğini kontrol eder.

**Query Parametreleri:**
- `content_type_id`: İçerik tipinin ID'si (zorunlu)
- `object_id`: İçerik nesnesinin ID'si (zorunlu)

**Yanıt:**

```json
{
  "liked": true
}
```

### Kullanıcının Kendi Beğenileri

**Endpoint:** `GET /likes/my_likes/`

**Açıklama:** Oturum açmış olan kullanıcının tüm beğenilerini listeler.

### Bir İçeriği Beğenen Kullanıcıları Listeleme

**Endpoint:** `GET /likes/likers/`

**Açıklama:** Belirli bir içeriği beğenen tüm kullanıcıları listeler.

**Query Parametreleri:**
- `content_type_id`: İçerik tipinin ID'si (zorunlu)
- `object_id`: İçerik nesnesinin ID'si (zorunlu)

**Yanıt:**

```json
{
  "count": 50,
  "next": "http://example.com/api/v1/likes/likers/?content_type_id=15&object_id=5&page=2",
  "previous": null,
  "results": [
    {
      "id": 10,
      "username": "ahmet",
      "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
      "full_name": "Ahmet Yılmaz",
      "is_verified": true
    },
    {
      "id": 12,
      "username": "mehmet",
      "avatar_url": "http://example.com/media/avatars/mehmet.jpg",
      "full_name": "Mehmet Demir",
      "is_verified": false
    }
  ]
}
```

## İyi Uygulama Örnekleri

### İçeriği Beğenme/Beğeniden Çıkarma (Toggle)

```javascript
// React Native örneği
const toggleLike = async (contentTypeId, objectId) => {
  try {
    const response = await api.post('/api/v1/likes/likes/toggle/', {
      content_type_id: contentTypeId,
      object_id: objectId
    }, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Beğeni işlemi sırasında hata oluştu:', error);
    throw error;
  }
};
```

### Beğeni Durumunu Kontrol Etme

```javascript
// React Native örneği
const checkLikeStatus = async (contentTypeId, objectId) => {
  try {
    const response = await api.get(`/api/v1/likes/likes/check/`, {
      params: {
        content_type_id: contentTypeId,
        object_id: objectId
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data.liked;
  } catch (error) {
    console.error('Beğeni durumu kontrol edilirken hata oluştu:', error);
    throw error;
  }
};
```

### Beğenen Kullanıcıları Listeleme

```javascript
// React Native örneği
const getLikers = async (contentTypeId, objectId) => {
  try {
    const response = await api.get(`/api/v1/likes/likes/likers/`, {
      params: {
        content_type_id: contentTypeId,
        object_id: objectId
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data.results;
  } catch (error) {
    console.error('Beğenen kullanıcılar listelenirken hata oluştu:', error);
    throw error;
  }
};
```