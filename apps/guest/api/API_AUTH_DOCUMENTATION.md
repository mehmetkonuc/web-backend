# Kimlik Doğrulama API Dokümantasyonu

Bu dokümantasyon, mobil uygulamada kullanılacak kullanıcı kimlik doğrulama ve kayıt API'lerini açıklar.

## Genel Bilgiler

### API Tabanı URL
```
http://[domain]/api/v1/auth/
```

### Kimlik Doğrulama
Bu API, JWT (JSON Web Token) tabanlı kimlik doğrulama kullanmaktadır.

## Giriş ve Kayıt Endpointleri

### 1. Kullanıcı Girişi

**Endpoint:** `login/`  
**Method:** `POST`  
**Açıklama:** Kullanıcı adı veya email ile giriş yapılmasını sağlar.

#### İstek (Request):
```json
{
  "login_identifier": "kullanici_adi_veya_email@ornek.com",
  "password": "sifre",
  "remember_me": true
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "refresh": "refresh_token_değeri",
  "access": "access_token_değeri",
  "user": {
    "id": 1,
    "username": "kullanici_adi",
    "email": "email@ornek.com",
    "first_name": "Ad",
    "last_name": "Soyad",
    "date_joined": "2025-04-19T10:00:00Z",
    "is_active": true,
    "profile": {
      "university": 1,
      "university_name": "Üniversite Adı",
      "department": 2,
      "department_name": "Bölüm Adı",
      "graduation_status": 1,
      "graduation_status_name": "Mezuniyet Durumu",
      "is_verified": true
    }
  }
}
```

#### Hatalı Yanıt (401 Unauthorized):
```json
{
  "error": "Geçersiz kullanıcı adı veya şifre."
}
```

### 2. İki Adımlı Kayıt - Adım 1

**Endpoint:** `register/step1/`  
**Method:** `POST`  
**Açıklama:** İki adımlı kayıt sürecinin ilk adımı; kullanıcı kimlik bilgilerini alır.

#### İstek (Request):
```json
{
  "username": "kullanici_adi",
  "first_name": "Ad",
  "last_name": "Soyad",
  "email": "email@ornek.com",
  "password": "sifre123",
  "password2": "sifre123"
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "message": "İlk adım başarıyla tamamlandı",
  "data": {
    "username": "kullanici_adi",
    "first_name": "Ad",
    "last_name": "Soyad",
    "email": "email@ornek.com"
  },
  "step": 2
}
```

#### Hatalı Yanıt (400 Bad Request):
```json
{
  "username": ["Bu kullanıcı adı zaten kullanılıyor."],
  "email": ["Bu email adresi zaten kullanılıyor."],
  "password": ["Şifreler eşleşmiyor."]
}
```

### 3. Veri Seçeneklerini Al

**Endpoint:** `dataset-options/`  
**Method:** `GET`  
**Açıklama:** Kayıt sırasında kullanılacak üniversite, bölüm ve mezuniyet durumu seçeneklerini döndürür.

#### Başarılı Yanıt (200 OK):
```json
{
  "universities": [
    {"id": 1, "name": "Üniversite A"},
    {"id": 2, "name": "Üniversite B"}
  ],
  "departments": [
    {"id": 1, "name": "Bölüm A"},
    {"id": 2, "name": "Bölüm B"}
  ],
  "graduation_statuses": [
    {"id": 1, "name": "Mezun"},
    {"id": 2, "name": "Öğrenci"}
  ]
}
```

### 4. İki Adımlı Kayıt - Adım 2 (Mevcut Veri)

**Endpoint:** `register/step2/`  
**Method:** `GET`  
**Açıklama:** İlk adımda girilen bilgileri ve kullanıcıya sunulacak seçenekleri döndürür.

#### Başarılı Yanıt (200 OK):
```json
{
  "step1_data": {
    "username": "kullanici_adi",
    "first_name": "Ad",
    "last_name": "Soyad",
    "email": "email@ornek.com"
  },
  "universities": [
    {"id": 1, "name": "Üniversite A"},
    {"id": 2, "name": "Üniversite B"}
  ],
  "departments": [
    {"id": 1, "name": "Bölüm A"},
    {"id": 2, "name": "Bölüm B"}
  ],
  "graduation_statuses": [
    {"id": 1, "name": "Mezun"},
    {"id": 2, "name": "Öğrenci"}
  ],
  "step": 2
}
```

### 5. İki Adımlı Kayıt - Adım 2 (Tamamlama)

**Endpoint:** `register/step2/`  
**Method:** `POST`  
**Açıklama:** İki adımlı kayıt sürecinin ikinci adımı; profil bilgilerini alır ve kaydı tamamlar.

#### İstek (Request):
```json
{
  "university": 1,
  "department": 2,
  "graduation_status": 1
}
```

#### Başarılı Yanıt (201 Created):
```json
{
  "message": "Kayıt başarıyla tamamlandı",
  "refresh": "refresh_token_değeri",
  "access": "access_token_değeri",
  "user": {
    "id": 1,
    "username": "kullanici_adi",
    "email": "email@ornek.com",
    "first_name": "Ad",
    "last_name": "Soyad",
    "date_joined": "2025-04-19T10:00:00Z",
    "is_active": true,
    "profile": {
      "university": 1,
      "university_name": "Üniversite A",
      "department": 2,
      "department_name": "Bölüm B",
      "graduation_status": 1,
      "graduation_status_name": "Mezun",
      "is_verified": false
    }
  }
}
```

#### Hatalı Yanıt (400 Bad Request):
```json
{
  "error": "İlk adım tamamlanmadı",
  "step": 1
}
```

### 6. Tek Adımlı Kayıt (Geriye Dönük Uyumluluk)

**Endpoint:** `register/`  
**Method:** `POST`  
**Açıklama:** İki adımı tek bir istekte birleştiren eski stil kayıt.

#### İstek (Request):
```json
{
  "username": "kullanici_adi",
  "first_name": "Ad",
  "last_name": "Soyad",
  "email": "email@ornek.com",
  "password": "sifre123",
  "password2": "sifre123",
  "university": 1,
  "department": 2,
  "graduation_status": 1
}
```

#### Başarılı Yanıt (201 Created):
```json
{
  "username": "kullanici_adi",
  "email": "email@ornek.com",
  "first_name": "Ad",
  "last_name": "Soyad"
}
```

## JWT Token İşlemleri

### 1. Token Al

**Endpoint:** `token/`  
**Method:** `POST`  
**Açıklama:** Kullanıcı bilgileri ile JWT token çifti (access + refresh) alır.

#### İstek (Request):
```json
{
  "username": "kullanici_adi",
  "password": "sifre"
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "refresh": "refresh_token_değeri",
  "access": "access_token_değeri"
}
```

### 2. Token Yenile

**Endpoint:** `token/refresh/`  
**Method:** `POST`  
**Açıklama:** Geçerli bir refresh token ile yeni bir access token alır.

#### İstek (Request):
```json
{
  "refresh": "refresh_token_değeri"
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "access": "yeni_access_token_değeri"
}
```

### 3. Token Doğrula

**Endpoint:** `token/verify/`  
**Method:** `POST`  
**Açıklama:** Bir token'ın geçerli olup olmadığını kontrol eder.

#### İstek (Request):
```json
{
  "token": "doğrulanacak_token_değeri"
}
```

#### Başarılı Yanıt (200 OK):
```json
{}
```

## Kullanıcı Profili İşlemleri

### 1. Mevcut Kullanıcı Bilgilerini Al

**Endpoint:** `me/`  
**Method:** `GET`  
**Açıklama:** Oturum açmış kullanıcının bilgilerini döndürür.
**Yetkilendirme Gerektiriyor:** Evet (Bearer Token)

#### Başarılı Yanıt (200 OK):
```json
{
  "id": 1,
  "username": "kullanici_adi",
  "email": "email@ornek.com",
  "first_name": "Ad",
  "last_name": "Soyad",
  "date_joined": "2025-04-19T10:00:00Z",
  "is_active": true,
  "profile": {
    "university": 1,
    "university_name": "Üniversite A",
    "department": 2,
    "department_name": "Bölüm B",
    "graduation_status": 1,
    "graduation_status_name": "Mezun",
    "is_verified": false
  }
}
```

### 2. Şifre Değiştir

**Endpoint:** `change-password/`  
**Method:** `PUT`  
**Açıklama:** Kullanıcının şifresini değiştirir.
**Yetkilendirme Gerektiriyor:** Evet (Bearer Token)

#### İstek (Request):
```json
{
  "old_password": "eski_sifre",
  "new_password": "yeni_sifre",
  "new_password2": "yeni_sifre"
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "message": "Şifre başarıyla değiştirildi."
}
```

#### Hatalı Yanıt (400 Bad Request):
```json
{
  "old_password": "Mevcut şifre yanlış."
}
```

## Yetkilendirme

API endpointlerinin çoğu, JWT kimlik doğrulaması gerektirmektedir. İsteklerde Authorization başlığını aşağıdaki gibi ayarlayın:

```
Authorization: Bearer [access_token]
```

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

## React Native Expo Uygulama Geliştirme Notu

React Native Expo ile bu API'leri kullanırken, özellikle kayıt sürecindeki ikinci adımda (`register/step2/`) dikkat edilmesi gereken önemli bir nokta bulunmaktadır.

### Tip Dönüşümü Sorunu

React Native'de özellikle Picker bileşeni kullanırken, API'ye gönderilen sayısal değerler (ID'ler) için tip dönüşümü hataları oluşabilir. Aşağıdaki hata mesajıyla karşılaşabilirsiniz:

```
(NOBRIDGE) ERROR Warning: Error: Exception in HostFunction: TypeError: expected dynamic type 'string', but had type 'double'
```

### Çözüm

Bu sorunu çözmek için, Picker bileşenlerinde değerleri her zaman string olarak işleyin ve API'ye göndermeden önce sayıya dönüştürün:

1. State değerlerini string olarak tanımlayın:
   ```typescript
   const [university, setUniversity] = useState<string>("");
   const [department, setDepartment] = useState<string>("");
   const [graduationStatus, setGraduationStatus] = useState<string>("");
   ```

2. Picker bileşenlerinde değerleri string'e dönüştürün:
   ```tsx
   <Picker.Item key={uni.id.toString()} label={uni.name} value={uni.id.toString()} />
   ```

3. `onValueChange` fonksiyonlarını değerleri string'e dönüştürecek şekilde oluşturun:
   ```typescript
   onValueChange={(value) => setUniversity(value.toString())}
   ```

4. API'ye göndermeden önce string değerleri sayıya dönüştürün:
   ```typescript
   await registerStep2({
     university: parseInt(university, 10),
     department: parseInt(department, 10),
     graduation_status: parseInt(graduationStatus, 10),
   });
   ```

Bu yaklaşım, React Native'in platform bağımlı davranışlarından kaynaklanan sorunları önleyecektir.

---

*Not: Bu dokümantasyon, mobil uygulama geliştirme sürecinde kullanılacak API'lerin temel kullanımını açıklar.*