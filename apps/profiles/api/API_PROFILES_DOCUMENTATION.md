# Profil API Dokümantasyonu

Bu dokümantasyon, mobil uygulamada kullanılacak kullanıcı profili ve ilişkili işlemler için API'leri açıklar.

## Genel Bilgiler

### API Tabanı URL
```
http://[domain]/api/v1/profiles/
```

### Kimlik Doğrulama
Bu API, JWT (JSON Web Token) tabanlı kimlik doğrulama kullanmaktadır. Tüm istekler için geçerli bir erişim tokeni gereklidir.

## Profil Endpointleri

### 1. Profil Listeleme

**Endpoint:** `/api/v1/profiles/`  
**Method:** `GET`  
**Açıklama:** Görünür durumdaki tüm profilleri listeler. Gizli profilleri sadece takip edenler görebilir.

#### Başarılı Yanıt (200 OK):
```json
[
  {
    "user": {
      "id": 1,
      "username": "kullanici_adi",
      "email": "email@ornek.com",
      "first_name": "Ad",
      "last_name": "Soyad",
      "date_joined": "2025-04-19T10:00:00Z",
      "is_active": true
    },
    "avatar": "http://domain.com/media/avatars/2025/04/avatar.jpg",
    "university": 1,
    "university_name": "Üniversite Adı",
    "department": 2,
    "department_name": "Bölüm Adı",
    "graduation_status": 1,
    "graduation_status_name": "Mezuniyet Durumu",
    "is_private": false,
    "is_verified": true,
    "bio": "Kullanıcı hakkında kısa bilgi",
    "followers_count": 42,
    "following_count": 38,
    "is_following": false,
    "has_pending_request": false
  },
  // Diğer profiller...
]
```

### 2. Profil Detay Görüntüleme

**Endpoint:** `/api/v1/profiles/{id}/`  
**Method:** `GET`  
**Açıklama:** Belirtilen ID'ye sahip profilin detaylarını gösterir.

#### Başarılı Yanıt (200 OK):
```json
{
  "user": {
    "id": 1,
    "username": "kullanici_adi",
    "email": "email@ornek.com",
    "first_name": "Ad",
    "last_name": "Soyad",
    "date_joined": "2025-04-19T10:00:00Z",
    "is_active": true
  },
  "avatar": "http://domain.com/media/avatars/2025/04/avatar.jpg",
  "university": 1,
  "university_name": "Üniversite Adı",
  "department": 2,
  "department_name": "Bölüm Adı",
  "graduation_status": 1,
  "graduation_status_name": "Mezuniyet Durumu",
  "is_private": false,
  "is_verified": true,
  "bio": "Kullanıcı hakkında kısa bilgi",
  "followers_count": 42,
  "following_count": 38,
  "is_following": false,
  "has_pending_request": false
}
```

#### Hata Yanıtı (403 Forbidden):
```json
{
  "detail": "Bu kullanıcının profilini görüntüleme yetkiniz yok."
}
```

### 3. Mevcut Kullanıcının Profili

**Endpoint:** `/api/v1/profiles/me/`  
**Method:** `GET`  
**Açıklama:** Kimlik doğrulaması yapılmış mevcut kullanıcının profil bilgilerini döndürür.

#### Başarılı Yanıt (200 OK):
```json
{
  "user": {
    "id": 1,
    "username": "kullanici_adi",
    "email": "email@ornek.com",
    "first_name": "Ad",
    "last_name": "Soyad",
    "date_joined": "2025-04-19T10:00:00Z",
    "is_active": true
  },
  "avatar": "http://domain.com/media/avatars/2025/04/avatar.jpg",
  "university": 1,
  "university_name": "Üniversite Adı",
  "department": 2,
  "department_name": "Bölüm Adı",
  "graduation_status": 1,
  "graduation_status_name": "Mezuniyet Durumu",
  "is_private": false,
  "is_verified": true,
  "bio": "Kullanıcı hakkında kısa bilgi",
  "followers_count": 42,
  "following_count": 38,
  "is_following": false,
  "has_pending_request": false
}
```

### 4. Profil Takipçileri

**Endpoint:** `/api/v1/profiles/{id}/followers/`  
**Method:** `GET`  
**Açıklama:** Belirtilen ID'ye sahip profilin takipçilerini listeler.

#### Başarılı Yanıt (200 OK):
```json
[
  {
    "user": {
      "id": 2,
      "username": "takipci_1",
      "email": "takipci1@ornek.com",
      "first_name": "Takipçi",
      "last_name": "Bir",
      "date_joined": "2025-04-19T10:00:00Z",
      "is_active": true
    },
    "avatar": "http://domain.com/media/avatars/2025/04/takipci1.jpg",
    "university": 1,
    "university_name": "Üniversite Adı",
    "department": 2,
    "department_name": "Bölüm Adı",
    "graduation_status": 1,
    "graduation_status_name": "Mezuniyet Durumu",
    "is_private": false,
    "is_verified": true,
    "bio": "Takipçi hakkında kısa bilgi",
    "followers_count": 15,
    "following_count": 20,
    "is_following": true,
    "has_pending_request": false
  },
  // Diğer takipçiler...
]
```

#### Hata Yanıtı (403 Forbidden) - Gizli profil için:
```json
{
  "detail": "Bu kullanıcının takipçilerini görüntüleme yetkiniz yok."
}
```

### 5. Profil Takip Edilenler

**Endpoint:** `/api/v1/profiles/{id}/following/`  
**Method:** `GET`  
**Açıklama:** Belirtilen ID'ye sahip profilin takip ettiği kullanıcıları listeler.

#### Başarılı Yanıt (200 OK):
```json
[
  {
    "user": {
      "id": 3,
      "username": "takip_edilen",
      "email": "takipedilen@ornek.com",
      "first_name": "Takip",
      "last_name": "Edilen",
      "date_joined": "2025-04-19T10:00:00Z",
      "is_active": true
    },
    "avatar": "http://domain.com/media/avatars/2025/04/takip_edilen.jpg",
    "university": 1,
    "university_name": "Üniversite Adı",
    "department": 2,
    "department_name": "Bölüm Adı",
    "graduation_status": 1,
    "graduation_status_name": "Mezuniyet Durumu",
    "is_private": false,
    "is_verified": true,
    "bio": "Takip edilen hakkında kısa bilgi",
    "followers_count": 25,
    "following_count": 10,
    "is_following": false,
    "has_pending_request": false
  },
  // Diğer takip edilenler...
]
```

#### Hata Yanıtı (403 Forbidden) - Gizli profil için:
```json
{
  "detail": "Bu kullanıcının takip ettiklerini görüntüleme yetkiniz yok."
}
```

## Takip Sistemi Endpointleri

### 1. Kullanıcı Takip Etme veya Takibi Bırakma

**Endpoint:** `/api/v1/profiles/follow/{username}/`  
**Method:** `POST`  
**Açıklama:** Belirtilen kullanıcıyı takip eder veya takibi bırakır.

#### Başarılı Yanıt - Takip Edildi (200 OK):
```json
{
  "status": "followed",
  "followers_count": 43
}
```

#### Başarılı Yanıt - Takip İsteği Gönderildi (200 OK):
```json
{
  "status": "requested",
  "followers_count": 43,
  "message": "kullanici_adi hesabı gizli. Takip isteği gönderildi."
}
```

#### Başarılı Yanıt - Takibi Bırakıldı (200 OK):
```json
{
  "status": "unfollowed",
  "followers_count": 41
}
```

#### Hata Yanıtı (400 Bad Request):
```json
{
  "detail": "Kendinizi takip edemezsiniz"
}
```

### 2. Gelen Takip İstekleri Listesi

**Endpoint:** `/api/v1/profiles/follow-requests/`  
**Method:** `GET`  
**Açıklama:** Kullanıcının aldığı bekleyen takip isteklerini listeler.

#### Başarılı Yanıt (200 OK):
```json
[
  {
    "id": 1,
    "from_user": {
      "user": {
        "id": 5,
        "username": "takip_isteyen",
        "email": "takipisteyen@ornek.com",
        "first_name": "Takip",
        "last_name": "İsteyen",
        "date_joined": "2025-04-19T10:00:00Z",
        "is_active": true
      },
      "avatar": "http://domain.com/media/avatars/2025/04/takip_isteyen.jpg",
      "is_private": false,
      "is_verified": true,
      "followers_count": 12,
      "following_count": 45
      // Diğer profil bilgileri...
    },
    "to_user": {
      // Mevcut kullanıcının profil bilgileri
    },
    "status": "pending",
    "created_at": "2025-04-19T15:30:00Z",
    "updated_at": "2025-04-19T15:30:00Z"
  },
  // Diğer takip istekleri...
]
```

### 3. Takip İsteğini Kabul Etme

**Endpoint:** `/api/v1/profiles/follow-requests/{request_id}/accept/`  
**Method:** `POST`  
**Açıklama:** Belirtilen takip isteğini kabul eder.

#### Başarılı Yanıt (200 OK):
```json
{
  "status": "accepted",
  "message": "Takip isteği kabul edildi."
}
```

#### Hata Yanıtı (404 Not Found):
```json
{
  "detail": "Takip isteği bulunamadı"
}
```

### 4. Takip İsteğini Reddetme

**Endpoint:** `/api/v1/profiles/follow-requests/{request_id}/reject/`  
**Method:** `POST`  
**Açıklama:** Belirtilen takip isteğini reddeder.

#### Başarılı Yanıt (200 OK):
```json
{
  "status": "rejected",
  "message": "Takip isteği reddedildi."
}
```

#### Hata Yanıtı (404 Not Found):
```json
{
  "detail": "Takip isteği bulunamadı"
}
```

## Engelleme Sistemi Endpointleri

### 1. Kullanıcı Engelleme veya Engeli Kaldırma

**Endpoint:** `/api/v1/profiles/block/{username}/`  
**Method:** `POST`  
**Açıklama:** Belirtilen kullanıcıyı engeller veya engelini kaldırır.

#### Başarılı Yanıt - Engellendi (200 OK):
```json
{
  "status": "blocked"
}
```

#### Başarılı Yanıt - Engel Kaldırıldı (200 OK):
```json
{
  "status": "unblocked"
}
```

#### Hata Yanıtı (400 Bad Request):
```json
{
  "detail": "Kendinizi engelleyemezsiniz"
}
```

### 2. Engellenen Kullanıcıları Listeleme

**Endpoint:** `/api/v1/profiles/blocked-users/`  
**Method:** `GET`  
**Açıklama:** Oturum açan kullanıcının engellediği profilleri listeler (sayfalanmış).

#### Başarılı Yanıt (200 OK):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "user": {
        "id": 5,
        "username": "engellenen_kullanici",
        "first_name": "Engellenen",
        "last_name": "Kullanıcı"
      },
      "avatar": "http://domain.com/media/avatars/2025/05/avatar.jpg",
      "university": 1,
      "university_name": "Üniversite Adı",
      "department": 2,
      "department_name": "Bölüm Adı",
      "graduation_status": 1,
      "graduation_status_name": "Mezuniyet Durumu",
      "is_private": false,
      "is_verified": false,
      "bio": "Engellenen kullanıcı hakkında bilgi",
      "followers_count": 5,
      "following_count": 10,
      "is_following": false,
      "has_pending_request": false,
      "is_blocked": true
    },
    // Diğer engellenen profiller...
  ]
}
```

## Profil Ayarları Endpointleri

### 1. Profil Bilgilerini Güncelleme

**Endpoint:** `/api/v1/profiles/settings/update/`  
**Method:** `PUT`, `PATCH`  
**Açıklama:** Kullanıcının profil bilgilerini günceller.

#### İstek (Request):
```json
{
  "username": "yeni_kullanici_adi",
  "first_name": "Yeni Ad",
  "last_name": "Yeni Soyad",
  "email": "yeni_email@ornek.com",
  "bio": "Güncellenmiş profil açıklaması",
  "university": 2,
  "department": 3,
  "graduation_status": 1
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "username": "yeni_kullanici_adi",
  "first_name": "Yeni Ad",
  "last_name": "Yeni Soyad",
  "email": "yeni_email@ornek.com",
  "bio": "Güncellenmiş profil açıklaması",
  "university": 2,
  "department": 3,
  "graduation_status": 1
}
```

#### Hata Yanıtı (400 Bad Request):
```json
{
  "username": [
    "Bu kullanıcı adı başka bir kullanıcı tarafından kullanılıyor."
  ],
  "email": [
    "Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor."
  ]
}
```

### 2. Gizlilik Ayarlarını Güncelleme

**Endpoint:** `/api/v1/profiles/settings/privacy/`  
**Method:** `PUT`, `PATCH`  
**Açıklama:** Kullanıcının gizlilik ayarlarını günceller.

#### İstek (Request):
```json
{
  "is_private": true
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "is_private": true
}
```

#### Başarılı Yanıt (200 OK) - Profil Gizli Olmaktan Çıkarıldığında:
```json
{
  "is_private": false,
  "accepted_requests": 5
}
```

### 3. Şifre Değiştirme

**Endpoint:** `/api/v1/profiles/settings/password/`  
**Method:** `POST`  
**Açıklama:** Kullanıcının şifresini değiştirir.

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
  "message": "Şifreniz başarıyla değiştirildi."
}
```

#### Hata Yanıtı (400 Bad Request):
```json
{
  "old_password": [
    "Mevcut şifreniz yanlış."
  ],
  "new_password2": [
    "Yeni şifreler eşleşmiyor."
  ]
}
```

### 4. Hesap Silme

**Endpoint:** `/api/v1/profiles/settings/delete-account/`  
**Method:** `POST`  
**Açıklama:** Kullanıcının hesabını devre dışı bırakır (soft delete).

#### İstek (Request):
```json
{
  "password": "sifre"
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "message": "Hesabınız başarıyla silinmiştir."
}
```

#### Hata Yanıtı (400 Bad Request):
```json
{
  "password": [
    "Şifreniz yanlış."
  ]
}
```

## Profil Resmi (Avatar) İşlemleri

### 1. Profil Resmi Yükleme

**Endpoint:** `/api/v1/profiles/avatar/upload/`  
**Method:** `POST`  
**Açıklama:** Kullanıcının profil resmini günceller. Base64 formatında resim verisi alır.

#### İstek (Request):
```json
{
  "avatar": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/..."
}
```

#### Başarılı Yanıt (200 OK):
Profil serializer'ı ile aynı formatta profil bilgileri döner.

#### Hata Yanıtı (400 Bad Request):
```json
{
  "detail": "Profil resmi verileri bulunamadı"
}
```

### 2. Profil Resmi Silme

**Endpoint:** `/api/v1/profiles/avatar/delete/`  
**Method:** `DELETE`  
**Açıklama:** Kullanıcının profil resmini siler.

#### Başarılı Yanıt (200 OK):
Profil serializer'ı ile aynı formatta profil bilgileri döner (avatar alanı null olarak).

#### Hata Yanıtı (400 Bad Request):
```json
{
  "detail": "Kaldırılacak bir profil resmi bulunamadı"
}
```

## Dataset Seçenekleri

### 1. Veri Seçeneklerini Alma

**Endpoint:** `/api/v1/profiles/dataset-options/`  
**Method:** `GET`  
**Açıklama:** Profil ayarları için üniversite, bölüm ve mezuniyet durumu seçeneklerini döndürür.

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

## Yetkilendirme

API endpointlerinin tamamı, JWT kimlik doğrulaması gerektirmektedir. İsteklerde Authorization başlığını aşağıdaki gibi ayarlayın:

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

React Native Expo ile bu API'leri kullanırken dikkat edilmesi gereken birkaç önemli nokta bulunmaktadır:

### 1. Base64 ile Avatar Yükleme

Profil resmi yüklerken, resmi base64 formatına dönüştürmeniz gerekmektedir. Bu işlem için expo-image-picker ve FileSystem modüllerini kullanabilirsiniz:

```javascript
import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system';

// Resim seçme ve base64 dönüşümü
const pickImage = async () => {
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsEditing: true,
    aspect: [1, 1],
    quality: 0.7,
  });

  if (!result.cancelled && result.assets && result.assets[0].uri) {
    const uri = result.assets[0].uri;
    const base64 = await FileSystem.readAsStringAsync(uri, { encoding: FileSystem.EncodingType.Base64 });
    const mimeType = `image/${uri.split('.').pop() || 'jpeg'}`;
    
    return `data:${mimeType};base64,${base64}`;
  }
  
  return null;
};
```

### 2. FlatList ile Profil Listelerini Gösterme

Takipçiler ve takip edilenler gibi listeleri gösterirken, FlatList kullanımı performans açısından önemlidir:

```javascript
import { FlatList } from 'react-native';

// Profil listesi bileşeni
const ProfileList = ({ profiles, onPress }) => {
  const renderItem = ({ item }) => (
    <ProfileItem
      profile={item}
      onPress={() => onPress(item)}
    />
  );

  return (
    <FlatList
      data={profiles}
      renderItem={renderItem}
      keyExtractor={(item) => item.user.id.toString()}
      initialNumToRender={10}
      maxToRenderPerBatch={10}
      windowSize={10}
      removeClippedSubviews={true}
    />
  );
};
```

### 3. Form Doğrulama

Profil güncelleme ve diğer form işlemleri için Formik ve Yup kullanımı önerilir:

```javascript
import { Formik } from 'formik';
import * as Yup from 'yup';

// Profil güncelleme doğrulama şeması
const ProfileUpdateSchema = Yup.object().shape({
  username: Yup.string()
    .min(3, 'Kullanıcı adı en az 3 karakter olmalıdır')
    .max(30, 'Kullanıcı adı en fazla 30 karakter olabilir')
    .required('Kullanıcı adı gereklidir'),
  email: Yup.string()
    .email('Geçerli bir e-posta adresi giriniz')
    .required('E-posta gereklidir'),
  // Diğer alanlar...
});
```

### 4. Hata İşleme

API isteklerinde hata işleme için try-catch bloklarını kullanın ve kullanıcıya anlamlı hata mesajları gösterin:

```javascript
try {
  const response = await api.put('/api/v1/profiles/settings/update/', profileData);
  // Başarılı işlemler
} catch (error) {
  if (error.response) {
    // Sunucudan dönen hata
    const errorMessage = handleApiError(error.response.data);
    Alert.alert('Hata', errorMessage);
  } else if (error.request) {
    // İstek yapıldı ama yanıt alınamadı
    Alert.alert('Bağlantı Hatası', 'Sunucuya bağlanırken bir sorun oluştu.');
  } else {
    // İstek yapılırken bir hata oluştu
    Alert.alert('Hata', 'Bir sorun oluştu. Lütfen tekrar deneyin.');
  }
}
```

### 5. Avatar URL İşleme

Profil resimleri için, API'den dönen URL'leri doğru şekilde işlemeniz gerekir:

```javascript
// Avatar URL'ini işleyen yardımcı fonksiyon
const getAvatarSource = (profile) => {
  if (profile && profile.avatar) {
    return { uri: profile.avatar };
  }
  return require('../assets/images/default-avatar.png'); // Varsayılan resim
};
```

Bu uygulamalar, React Native Expo projelerinde API entegrasyonunu daha sorunsuz ve performanslı hale getirecektir.

---

*Not: Bu dokümantasyon, mobil uygulama geliştirme sürecinde kullanılacak API'lerin temel kullanımını açıklar.*