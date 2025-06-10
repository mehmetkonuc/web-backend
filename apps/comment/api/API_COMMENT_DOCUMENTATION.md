# Comment API Dokümantasyonu

Bu API, sosyal medya platformunda yorumları (comment) yönetmek için kullanılır. GenericForeignKey yapısıyla herhangi bir içerik tipine (post, etkinlik, vb.) yorum yapılabilir ve bu yorumlar için CRUD işlemleri gerçekleştirilebilir.

## Base URL

```
/api/v1/comments/
```

## Doğrulama ve Yetkilendirme

Tüm endpointler için JWT kimlik doğrulaması gereklidir. Yetkilendirme başlığına bir erişim tokenı ekleyin:

```
Authorization: Bearer {access_token}
```

## GenericForeignKey Kullanımı Hakkında

Comment API'si, Django'nun ContentType framework'ünü kullanarak farklı model tiplerinin yorumlanmasını sağlar.

Her API çağrısında:
- `content_type_id`: Yorum yapılacak içerik tipinin ID'si (ContentType tablosundan)
- `object_id`: Yorum yapılacak içerik nesnesinin ID'si

Bu değerleri öğrenmek için Django shell'de şu kodları çalıştırabilirsiniz:

```python
from django.contrib.contenttypes.models import ContentType
from apps.post.models import Post

# Post modeli için content_type_id'yi alın
content_type_id = ContentType.objects.get_for_model(Post).id
print(content_type_id)  # Örneğin: 15
```

## Yorumları Listeleme

### Tüm Yorumları Listeleme (İçerik Tipine Göre)

**Endpoint:** `GET /comments/`

**Açıklama:** Belirli bir içerik nesnesine ait tüm üst seviye yorumları listeler.

**Query Parametreleri:**
- `content_type_id`: İçerik tipinin ID'si (zorunlu)
- `object_id`: İçerik nesnesinin ID'si (zorunlu)
- `page`: Sayfa numarası (varsayılan: 1)
- `ordering`: Sıralama kriteri (örn: "-created_at")

**Yanıt:**

```json
{
  "count": 10,
  "next": "http://example.com/api/v1/comments/comments/?content_type_id=15&object_id=5&page=2",
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
      "body": "Bu bir yorum örneğidir.",
      "created_at": "2025-04-20T12:30:00Z",
      "updated_at": "2025-04-20T12:30:00Z",
      "replies": [
        {
          "id": 3,
          "user": {
            "id": 12,
            "username": "mehmet",
            "avatar_url": "http://example.com/media/avatars/mehmet.jpg",
            "full_name": "Mehmet Demir",
            "is_verified": false
          },
          "body": "Bu bir cevap örneğidir.",
          "created_at": "2025-04-20T13:15:00Z",
          "updated_at": "2025-04-20T13:15:00Z",
          "replies": [],
          "images": [],
          "like_count": 1,
          "is_liked": false
        }
      ],
      "images": [
        {
          "id": 1,
          "image": "http://example.com/media/comments/image1.jpg",
          "order": 0
        }
      ],
      "like_count": 5,
      "is_liked": true
    }
  ]
}
```

### İçerik İçin Yorumları Getirme (Alternatif Endpoint)

**Endpoint:** `GET /comments/for_content/`

**Açıklama:** Belirli bir içerik nesnesine ait tüm üst seviye yorumları listeler.

**Query Parametreleri:**
- `content_type_id`: İçerik tipinin ID'si (zorunlu)
- `object_id`: İçerik nesnesinin ID'si (zorunlu)

### Kullanıcının Kendi Yorumlarını Listeleme

**Endpoint:** `GET /comments/my_comments/`

**Açıklama:** Oturum açmış olan kullanıcının tüm yorumlarını listeler.

## Yorum Detayları

**Endpoint:** `GET /comments/{id}/`

**Açıklama:** Belirli bir yorumun detaylarını getirir.

**Yanıt:**

```json
{
  "id": 1,
  "user": {
    "id": 10,
    "username": "ahmet",
    "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
    "full_name": "Ahmet Yılmaz",
    "is_verified": true
  },
  "body": "Bu bir yorum örneğidir.",
  "created_at": "2025-04-20T12:30:00Z",
  "updated_at": "2025-04-20T12:30:00Z",
  "replies": [
    {
      "id": 3,
      "user": {
        "id": 12,
        "username": "mehmet",
        "avatar_url": "http://example.com/media/avatars/mehmet.jpg",
        "full_name": "Mehmet Demir",
        "is_verified": false
      },
      "body": "Bu bir cevap örneğidir.",
      "created_at": "2025-04-20T13:15:00Z",
      "updated_at": "2025-04-20T13:15:00Z",
      "replies": [],
      "images": [],
      "like_count": 1,
      "is_liked": false
    }
  ],
  "images": [
    {
      "id": 1,
      "image": "http://example.com/media/comments/image1.jpg",
      "order": 0
    }
  ],
  "like_count": 5,
  "is_liked": true
}
```

## Yoruma Ait Cevapları Listeleme

**Endpoint:** `GET /comments/{id}/replies/`

**Açıklama:** Belirli bir yoruma yapılmış cevapları listeler.

## Yorum Oluşturma

**Endpoint:** `POST /comments/`

**Açıklama:** Yeni bir yorum oluşturur. En fazla 4 resim eklenebilir.

**İstek:**

```json
{
  "content_type_id": 15,
  "object_id": 5,
  "body": "Bu bir yorumdur.",
  "parent_id": null,
  "images_upload": [binary_image_file1, binary_image_file2]
}
```

**Not:**
- `parent_id` bir cevap oluşturulmak isteniyorsa, cevap verilecek yorumun ID'si olarak belirtilir. Eğer üst seviye bir yorum oluşturulacaksa `null` olarak bırakılır.
- `images_upload` alanı `multipart/form-data` olarak gönderilmelidir.
- Cevap yorumlarına cevap veremezsiniz (sadece bir seviye iç içe yorumlara izin verilir).

**Yanıt:**

```json
{
  "id": 10,
  "user": {
    "id": 10,
    "username": "ahmet",
    "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
    "full_name": "Ahmet Yılmaz",
    "is_verified": true
  },
  "body": "Bu bir yorumdur.",
  "created_at": "2025-04-24T15:30:00Z",
  "updated_at": "2025-04-24T15:30:00Z",
  "replies": [],
  "images": [
    {
      "id": 5,
      "image": "http://example.com/media/comments/image5.jpg",
      "order": 0
    },
    {
      "id": 6,
      "image": "http://example.com/media/comments/image6.jpg",
      "order": 1
    }
  ],
  "like_count": 0,
  "is_liked": false
}
```

## Yorum Güncelleme

**Endpoint:** `PUT /comments/{id}/` veya `PATCH /comments/{id}/`

**Açıklama:** Var olan bir yorumu günceller. Sadece yorumu oluşturan kullanıcı tarafından yapılabilir.

**İstek:**

```json
{
  "body": "Güncellenmiş yorum içeriği."
}
```

## Yorum Silme

**Endpoint:** `DELETE /comments/{id}/`

**Açıklama:** Var olan bir yorumu siler. Sadece yorumu oluşturan kullanıcı tarafından yapılabilir.

## İyi Uygulama Örnekleri

### Post'a Yorum Yapmak

```javascript
// React Native örneği
const postComment = async (postId, commentText, images = []) => {
  try {
    // Önce Post modeli için ContentType ID'sini bilmeliyiz (örn. 15)
    const postContentTypeId = 15;
    
    // FormData oluştur
    const formData = new FormData();
    formData.append('content_type_id', postContentTypeId);
    formData.append('object_id', postId);
    formData.append('body', commentText);
    
    // Resimler varsa ekle (en fazla 4 resim)
    images.slice(0, 4).forEach((image, index) => {
      formData.append('images_upload', {
        uri: image.uri,
        type: 'image/jpeg',
        name: `comment_image_${index}.jpg`
      });
    });
    
    const response = await api.post('/api/v1/comments/comments/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Yorum eklenirken hata oluştu:', error);
    throw error;
  }
};
```

### Yoruma Cevap Yazmak

```javascript
// React Native örneği
const replyToComment = async (commentId, commentContentTypeId, originalObjectId, replyText) => {
  try {
    const formData = new FormData();
    formData.append('content_type_id', commentContentTypeId); // Yorumun bağlı olduğu içeriğin content type id'si
    formData.append('object_id', originalObjectId); // Yorumun bağlı olduğu içeriğin id'si
    formData.append('parent_id', commentId); // Cevap verdiğimiz yorumun id'si
    formData.append('body', replyText);
    
    const response = await api.post('/api/v1/comments/comments/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Yoruma cevap verilirken hata oluştu:', error);
    throw error;
  }
};
```