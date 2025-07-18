# Confession API Documentation

## 📋 **Genel Bakış**
Confession API, kullanıcıların anonim veya açık itiraflar paylaşabilmesini sağlayan RESTful API'dir. Bu API, güvenlik, gizlilik ve performans odaklı olarak tasarlanmıştır.

## 🔐 **Kimlik Doğrulama**
Tüm API endpoint'leri JWT Authentication gerektirir.

```http
Authorization: Bearer <your-jwt-token>
```

## 🔗 **Base URL**
```
https://your-domain.com/api/v1/confessions/
```

## 📋 **Ana Endpoints**

### 1. İtiraf Listesi
```http
GET /confessions/
```

**Query Parameters:**
- `page`: Sayfa numarası (default: 1)
- `page_size`: Sayfa boyutu (default: 20)
- `search`: İçerik arama
- `category`: Kategori ID'si
- `university`: Üniversite ID'si
- `ordering`: Sıralama (-created_at, created_at, -like_count, -comment_count)

**Response:**
```json
{
  "count": 150,
  "next": "https://api.example.com/confessions/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 5,
        "username": "user123",
        "is_anonymous": true,
        "display_name": "Anonim",
        "avatar_url": null,
        "university": "İTÜ"
      },
      "content": "Bu bir itiraf örneği...",
      "category": {
        "id": 1,
        "name": "Aşk",
        "confession_count": 150
      },
      "university": {
        "id": 1,
        "name": "İstanbul Teknik Üniversitesi"
      },
      "images": [],
      "created_at": "2025-01-17T10:30:00Z",
      "like_count": 25,
      "comment_count": 8,
      "bookmark_count": 5,
      "is_liked": false,
      "is_bookmarked": false,
      "is_owner": false,
      "privacy_type": "anonymous"
    }
  ]
}
```

### 2. İtiraf Oluşturma
```http
POST /confessions/
```

**Request Body (FormData):**
```json
{
  "content": "İtiraf metni (max 2000 karakter)",
  "category": 1,
  "university": 1,
  "is_privacy": true,
  "images_upload": [file1, file2, file3, file4]
}
```

**Response:**
```json
{
  "success": true,
  "message": "İtiraf başarıyla oluşturuldu",
  "confession": {
    "id": 123,
    "user": { ... },
    "content": "İtiraf metni...",
    "category": { ... },
    "university": { ... },
    "images": [
      {
        "id": 1,
        "image_thumbnail": "https://api.example.com/media/...",
        "image_medium": "https://api.example.com/media/...",
        "image_large": "https://api.example.com/media/...",
        "order": 0
      }
    ],
    "created_at": "2025-01-17T10:30:00Z",
    "privacy_type": "anonymous"
  }
}
```

### 3. İtiraf Detayı
```http
GET /confessions/{id}/
```

**Response:**
```json
{
  "id": 1,
  "user": { ... },
  "content": "İtiraf metni...",
  "category": { ... },
  "university": { ... },
  "images": [ ... ],
  "comments": [
    {
      "id": 1,
      "user": { ... },
      "content": "Yorum metni...",
      "created_at": "2025-01-17T10:35:00Z",
      "like_count": 3,
      "is_liked": false
    }
  ],
  "created_at": "2025-01-17T10:30:00Z",
  "like_count": 25,
  "comment_count": 8,
  "bookmark_count": 5,
  "is_liked": false,
  "is_bookmarked": false,
  "is_owner": false,
  "privacy_type": "anonymous"
}
```

### 4. İtiraf Güncelleme
```http
PATCH /confessions/{id}/
```

**Request Body:**
```json
{
  "content": "Güncellenmiş itiraf metni",
  "is_privacy": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "İtiraf başarıyla güncellendi",
  "confession": { ... }
}
```

### 5. İtiraf Silme
```http
DELETE /confessions/{id}/
```

**Response:**
```json
{
  "success": true,
  "message": "İtiraf başarıyla silindi"
}
```

## 🔥 **Özel Endpoint'ler**

### 1. Trend İtiraflar
```http
GET /confessions/trending/
```

Son 24 saatte en çok beğeni alan itiraflar.

### 2. Kategoriye Göre İtiraflar
```http
GET /confessions/by_category/?category_id=1
```

### 3. Üniversiteye Göre İtiraflar
```http
GET /confessions/by_university/?university_id=1
```

### 4. Kullanıcının İtirafları
```http
GET /confessions/my_confessions/
```

### 5. Anonim İtiraflar
```http
GET /confessions/anonymous/
```

### 6. Açık İtiraflar
```http
GET /confessions/open/
```

### 7. Gizlilik Değiştirme
```http
POST /confessions/{id}/toggle_privacy/
```

**Response:**
```json
{
  "success": true,
  "message": "İtiraf anonim olarak ayarlandı",
  "is_privacy": true,
  "privacy_type": "anonymous"
}
```

### 8. İstatistikler
```http
GET /confessions/stats/
```

**Response:**
```json
{
  "total_confessions": 1500,
  "anonymous_confessions": 1200,
  "open_confessions": 300,
  "popular_categories": [
    {
      "id": 1,
      "name": "Aşk",
      "confession_count": 450
    }
  ]
}
```

## ⚙️ **Filtreleme & Tercihler**

### 1. Filtreleme Seçenekleri
```http
GET /filter-options/
```

**Response:**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "Aşk",
      "confession_count": 450,
      "active_confession_count": 420
    }
  ],
  "universities": [
    {
      "id": 1,
      "name": "İstanbul Teknik Üniversitesi"
    }
  ],
  "sort_options": [
    {
      "value": "-created_at",
      "label": "En Yeni"
    },
    {
      "value": "-like_count",
      "label": "En Beğenilen"
    }
  ],
  "privacy_options": [
    {
      "value": "all",
      "label": "Tümü"
    },
    {
      "value": "anonymous",
      "label": "Anonim"
    },
    {
      "value": "open",
      "label": "Açık"
    }
  ]
}
```

### 2. Kullanıcı Tercihlerini Getir
```http
GET /filter-preferences/
```

### 3. Kullanıcı Tercihlerini Kaydet
```http
POST /filter-preferences/
```

**Request Body:**
```json
{
  "category": 1,
  "university": 1,
  "sort_by": "-created_at"
}
```

### 4. Tercihleri Temizle
```http
POST /filter-preferences/clear/
```

## 📂 **Kategoriler**

### 1. Kategori Listesi
```http
GET /categories/
```

### 2. Popüler Kategoriler
```http
GET /categories/popular/
```

## 🛡️ **Güvenlik Özellikleri**

### 1. Gizlilik Kontrolleri
- Anonim itiraflar için kullanıcı bilgileri gizlenir
- Engellenen kullanıcıların itirafları filtrelenir
- Gizli profillerin itirafları takip edilmeyen kullanıcılar için gizlenir

### 2. İzinler
- Sadece itiraf sahibi güncelleme/silme yapabilir
- Sadece aktif itiraflar görüntülenir
- Kimlik doğrulama tüm endpoint'ler için gerekli

### 3. Validasyon
- İçerik maksimum 2000 karakter
- Maksimum 4 resim yükleme
- Resim boyutu maksimum 10MB
- Desteklenen formatlar: JPEG, PNG, WEBP

## 🖼️ **Resim İşleme**

### Resim Boyutları
- **Thumbnail**: 150x150px
- **Medium**: 600x600px  
- **Large**: 1200x1200px
- **Original**: Orijinal boyut

### Resim URL'leri
```json
{
  "image_thumbnail": "https://api.example.com/media/confessions/2025/01/17/123/thumbnail.webp",
  "image_medium": "https://api.example.com/media/confessions/2025/01/17/123/medium.webp",
  "image_large": "https://api.example.com/media/confessions/2025/01/17/123/large.webp",
  "image_original": "https://api.example.com/media/confessions/2025/01/17/123/original.jpg"
}
```

## 🚨 **Hata Kodları**

### 400 Bad Request
```json
{
  "detail": "category_id parametresi gerekli"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "Bu itiraf görüntülenemiyor (gizlilik/engelleme ayarları)."
}
```

### 404 Not Found
```json
{
  "detail": "İtiraf bulunamadı."
}
```

### 422 Validation Error
```json
{
  "content": [
    "İtiraf içeriği boş olamaz."
  ],
  "images": [
    "En fazla 4 resim yükleyebilirsiniz."
  ]
}
```

## 📱 **Mobil Uygulama Örnekleri**

### React Native Fetch Örneği
```javascript
// İtiraf listesi
const fetchConfessions = async () => {
  const response = await fetch('https://api.example.com/api/v1/confessions/confessions/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  const data = await response.json();
  return data.results;
};

// İtiraf oluşturma
const createConfession = async (confessionData) => {
  const formData = new FormData();
  formData.append('content', confessionData.content);
  formData.append('category', confessionData.category);
  formData.append('university', confessionData.university);
  formData.append('is_privacy', confessionData.is_privacy);
  
  confessionData.images.forEach((image, index) => {
    formData.append('images_upload', {
      uri: image.uri,
      type: image.type,
      name: `image_${index}.jpg`
    });
  });
  
  const response = await fetch('https://api.example.com/api/v1/confessions/confessions/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'multipart/form-data'
    },
    body: formData
  });
  
  return await response.json();
};
```

## 🔧 **Performans Optimizasyonları**

### 1. Veritabanı Optimizasyonları
- `select_related` ve `prefetch_related` kullanımı
- Database indexing
- Queryset optimizasyonları

### 2. Resim Optimizasyonları
- Otomatik resim sıkıştırma
- Multiple boyut desteği
- WebP format desteği
- Lazy loading

### 3. Caching
- Response caching
- Database query caching
- Image caching

## 📊 **Rate Limiting**
- 100 istek/dakika (authenticated users)
- 20 istek/dakika (image upload)
- 5 istek/dakika (confession creation)

## 🎯 **Best Practices**

### 1. Mobil Uygulama
- Pagination kullanın
- Image thumbnail'ları tercih edin
- Offline support için local storage kullanın
- Error handling implementasyonu yapın

### 2. Güvenlik
- JWT token'ları güvenli saklayın
- HTTPS kullanın
- Input validation yapın
- Rate limiting'e dikkat edin

### 3. Performans
- Lazy loading kullanın
- Image compression uygulayın
- Gereksiz API çağrılarını önleyin
- Background sync implementasyonu yapın
