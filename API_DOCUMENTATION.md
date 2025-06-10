# API Dokümantasyonu

Bu dokümantasyon, mobil uygulama geliştirme sürecinde kullanılacak API endpointlerini açıklar.

## Genel Bilgiler

### API Tabanı URL
```
http://192.168.0.164:8000/api/v1
```

### Kimlik Doğrulama
Bu API, JWT (JSON Web Token) tabanlı kimlik doğrulama kullanmaktadır.

#### JWT Endpoints

| Endpoint | Metod | Açıklama |
|----------|-------|----------|
| `/token/` | POST | Kullanıcı bilgileriyle token elde etme |
| `/token/refresh/` | POST | Geçerli bir refresh token kullanarak yeni bir access token elde etme |
| `/token/verify/` | POST | Token'ın geçerliliğini doğrulama |

#### Token Alma Örneği
```json
// POST /api/token/
{
  "username": "kullanici_adi",
  "password": "sifre"
}

// Yanıt
{
  "access": "access_token_değeri",
  "refresh": "refresh_token_değeri"
}
```

#### İstek Göndermek
API isteklerinde kimlik doğrulama için Authorization başlığını kullanın:
```
Authorization: Bearer [access_token]
```

## Ana Modüller

Sistemde aşağıdaki ana modüller bulunmaktadır:

### 1. Kullanıcı İşlemleri (Auth)
- Endpoint: `/auth/`
- İşlemler: Kayıt, giriş, şifre sıfırlama

## Hata Kodları

| Kod | Açıklama |
|-----|----------|
| 200 | Başarılı |
| 201 | Oluşturuldu |
| 400 | Geçersiz istek |
| 401 | Kimlik doğrulama hatası |
| 403 | Yetkisiz erişim |
| 404 | Bulunamadı |
| 500 | Sunucu hatası |

## Veri Formatı

Tüm API istekleri ve yanıtları JSON formatında olacaktır.

---

*Not: Bu dokümantasyon genel bir çerçeve sunmaktadır. Her modül için detaylı API dokümantasyonu ayrıca sağlanacaktır.*