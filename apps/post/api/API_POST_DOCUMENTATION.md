# Post API Dokümantasyonu

Bu API, sosyal medya platformunda gönderileri (post) yönetmek için kullanılır. Gönderileri listeleme, oluşturma, düzenleme, silme, belirli bir gönderiye erişme ve trend olan hashtagleri görüntüleme işlevlerini sağlar.

## Base URL

```
/api/v1/posts/
```

## Doğrulama ve Yetkilendirme

Tüm endpointler için JWT kimlik doğrulaması gereklidir. Yetkilendirme başlığına bir erişim tokenı ekleyin:

```
Authorization: Bearer {access_token}
```

## Gönderileri Listeleme

### Tüm Gönderileri Listeleme

**Endpoint:** `GET /posts/`

**Açıklama:** Tüm gönderileri listeler. Sonuçlar, kullanıcının ayarlarına göre filtrelenir (engellenen kullanıcıların gönderileri ve gizli profillerin gönderileri hariç tutulur).

**Query Parametreleri:**

- `page`: Sayfa numarası (default: 1)
- `posts_type`: Gönderi tipi filtresi ('all', 'following', 'verified')
- `university`: Üniversite ID'sine göre filtreleme
- `department`: Bölüm ID'sine göre filtreleme
- `search`: Gönderi içeriğinde arama yapar

**Yanıt:**

```json
{
  "count": 100,
  "next": "http://example.com/api/v1/posts/posts/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 10,
        "username": "ahmet",
        "profile_url": "/profile/ahmet/",
        "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
        "full_name": "Ahmet Yılmaz",
        "is_verified": true
      },
      "content": "Bu bir test gönderisidir. #test #örnek",
      "created_at": "2025-04-20T10:30:00Z",
      "updated_at": "2025-04-20T10:30:00Z",
      "images": [
        {
          "id": 1,
          "image": "http://example.com/media/posts/image1.jpg",
          "order": 0
        }
      ],
      "hashtags": [
        {
          "id": 5,
          "name": "test",
          "post_count": 10,
          "post_count_last_24h": 2,
          "url": "/post/hashtag/test/"
        },
        {
          "id": 8,
          "name": "örnek",
          "post_count": 5,
          "post_count_last_24h": 1,
          "url": "/post/hashtag/örnek/"
        }
      ],
      "like_count": 15,
      "comment_count": 3,
      "is_liked": false,
      "url": "/post/1/"
    }
  ]
}
```

### Kullanıcının Kendi Gönderilerini Listeleme

**Endpoint:** `GET /posts/my_posts/`

**Açıklama:** Oturum açmış olan kullanıcının kendi gönderilerini listeler.

### Belirli Bir Kullanıcının Gönderilerini Listeleme

**Endpoint:** `GET /posts/user_posts/?username={username}`

**Açıklama:** Belirtilen kullanıcının gönderilerini listeler. Eğer profil gizliyse ve kullanıcı takip etmiyorsa 403 Forbidden hatası döner.

### Hashtag'e Göre Gönderileri Listeleme

**Endpoint:** `GET /posts/by_hashtag/?hashtag={hashtag_name}`

**Açıklama:** Belirli bir hashtag'e sahip gönderileri listeler.

## Gönderi Detayları

**Endpoint:** `GET /posts/{id}/`

**Açıklama:** Belirli bir gönderinin detaylarını ve yorumlarını getirir.

**Yanıt:**

```json
{
  "id": 1,
  "user": {
    "id": 10,
    "username": "ahmet",
    "profile_url": "/profile/ahmet/",
    "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
    "full_name": "Ahmet Yılmaz",
    "is_verified": true
  },
  "content": "Bu bir test gönderisidir. #test #örnek",
  "created_at": "2025-04-20T10:30:00Z",
  "updated_at": "2025-04-20T10:30:00Z",
  "images": [
    {
      "id": 1,
      "image": "http://example.com/media/posts/image1.jpg",
      "order": 0
    }
  ],
  "hashtags": [
    {
      "id": 5,
      "name": "test",
      "post_count": 10,
      "post_count_last_24h": 2,
      "url": "/post/hashtag/test/"
    },
    {
      "id": 8,
      "name": "örnek",
      "post_count": 5,
      "post_count_last_24h": 1,
      "url": "/post/hashtag/örnek/"
    }
  ],
  "like_count": 15,
  "comment_count": 3,
  "is_liked": false,
  "url": "/post/1/",
  "comments": [
    {
      "id": 3,
      "user": {
        "id": 12,
        "username": "mehmet",
        "avatar_url": "http://example.com/media/avatars/mehmet.jpg",
        "full_name": "Mehmet Demir",
        "is_verified": false
      },
      "body": "Harika bir gönderi!",
      "created_at": "2025-04-20T11:15:00Z",
      "updated_at": "2025-04-20T11:15:00Z",
      "replies": [],
      "images": [],
      "like_count": 2,
      "is_liked": true
    }
  ]
}
```

## Gönderi Oluşturma

**Endpoint:** `POST /posts/`

**Açıklama:** Yeni bir gönderi oluşturur. En fazla 4 resim eklenebilir.

**İstek:**

```json
{
  "content": "Yeni bir gönderi oluşturuyorum. #yeni #gönderi",
  "images_upload": [binary_image_file1, binary_image_file2]
}
```

**Not:** `images_upload` alanı `multipart/form-data` olarak gönderilmelidir.

**Yanıt:**

```json
{
  "id": 5,
  "user": {
    "id": 10,
    "username": "ahmet",
    "profile_url": "/profile/ahmet/",
    "avatar_url": "http://example.com/media/avatars/ahmet.jpg",
    "full_name": "Ahmet Yılmaz",
    "is_verified": true
  },
  "content": "Yeni bir gönderi oluşturuyorum. #yeni #gönderi",
  "created_at": "2025-04-24T14:30:00Z",
  "updated_at": "2025-04-24T14:30:00Z",
  "images": [
    {
      "id": 10,
      "image": "http://example.com/media/posts/image10.jpg",
      "order": 0
    },
    {
      "id": 11,
      "image": "http://example.com/media/posts/image11.jpg",
      "order": 1
    }
  ],
  "hashtags": [
    {
      "id": 15,
      "name": "yeni",
      "post_count": 8,
      "post_count_last_24h": 3,
      "url": "/post/hashtag/yeni/"
    },
    {
      "id": 20,
      "name": "gönderi",
      "post_count": 12,
      "post_count_last_24h": 5,
      "url": "/post/hashtag/gönderi/"
    }
  ],
  "like_count": 0,
  "comment_count": 0,
  "is_liked": false,
  "url": "/post/5/"
}
```

## Gönderi Güncelleme

**Endpoint:** `PUT /posts/{id}/` veya `PATCH /posts/{id}/`

**Açıklama:** Var olan bir gönderiyi günceller. Sadece gönderiyi oluşturan kullanıcı tarafından yapılabilir.

**İstek:**

```json
{
  "content": "Güncellenmiş gönderi içeriği. #güncel"
}
```

## Gönderi Silme

**Endpoint:** `DELETE /posts/{id}/`

**Açıklama:** Var olan bir gönderiyi siler. Sadece gönderiyi oluşturan kullanıcı tarafından yapılabilir.

## Trend Olan Hashtagler

**Endpoint:** `GET /posts/trending/`

**Açıklama:** Trend olan hashtagleri ve bu hashtaglere sahip bazı gönderileri döndürür.

**Yanıt:**

```json
{
  "hashtags": [
    {
      "id": 25,
      "name": "trending",
      "post_count": 50,
      "post_count_last_24h": 30,
      "url": "/post/hashtag/trending/"
    }
  ],
  "posts": {
    "25": [
      {
        "id": 100,
        "user": {
          "id": 15,
          "username": "user1",
          "profile_url": "/profile/user1/",
          "avatar_url": "http://example.com/media/avatars/user1.jpg",
          "full_name": "User One",
          "is_verified": true
        },
        "content": "Trend olan bir gönderi #trending",
        "created_at": "2025-04-23T18:45:00Z",
        "updated_at": "2025-04-23T18:45:00Z",
        "images": [],
        "hashtags": [
          {
            "id": 25,
            "name": "trending",
            "post_count": 50,
            "post_count_last_24h": 30,
            "url": "/post/hashtag/trending/"
          }
        ],
        "like_count": 150,
        "comment_count": 25,
        "is_liked": false,
        "url": "/post/100/"
      }
    ]
  }
}
```

## Trend Olan Hashtagleri Ayrı Şekilde Getirme

**Endpoint:** `GET /hashtags/trending/`

**Açıklama:** Sadece trend olan hashtaglerin listesini döner.

## Filtreleme Seçenekleri

### Filtreleme Seçeneklerini Getirme

**Endpoint:** `GET /filter-options/`

**Açıklama:** Filtreleme için kullanılabilecek üniversiteler, bölümler ve gönderi tiplerini listeler.

**Yanıt:**

```json
{
  "universities": [
    {
      "id": 1,
      "name": "İstanbul Teknik Üniversitesi"
    },
    {
      "id": 2,
      "name": "Boğaziçi Üniversitesi"
    }
  ],
  "departments": [
    {
      "id": 1,
      "name": "Bilgisayar Mühendisliği"
    },
    {
      "id": 2,
      "name": "Elektrik-Elektronik Mühendisliği"
    }
  ],
  "post_types": [
    {
      "id": "all",
      "name": "Bütün Gönderiler"
    },
    {
      "id": "following",
      "name": "Sadece Takip Ettiklerim"
    },
    {
      "id": "verified",
      "name": "Sadece Doğrulanmış Hesaplar"
    }
  ]
}
```

### Kullanıcı Filtre Tercihlerini Getirme

**Endpoint:** `GET /filter-preferences/`

**Açıklama:** Kullanıcının kayıtlı filtre tercihlerini getirir.

**Yanıt:**

```json
{
  "posts_type": "following",
  "university": 1,
  "department": 2
}
```

### Kullanıcı Filtre Tercihlerini Güncelleme

**Endpoint:** `PUT /filter-preferences/`

**Açıklama:** Kullanıcının filtre tercihlerini günceller.

**İstek:**

```json
{
  "posts_type": "verified",
  "university": 2,
  "department": 1
}
```

### Kullanıcı Filtre Tercihlerini Temizleme

**Endpoint:** `POST /filter-preferences/clear/`

**Açıklama:** Kullanıcının filtre tercihlerini temizler ve varsayılan değerlere döndürür.

**Yanıt:**

```json
{
  "detail": "Filter preferences cleared successfully"
}
```