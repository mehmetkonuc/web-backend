# Members API Dokümantasyonu

Bu dokümantasyon, mobil uygulamada kullanılacak üyeler (members) modülü için API'leri açıklar.

## Genel Bilgiler

### API Tabanı URL
```
http://[domain]/api/v1/members/
```

### Kimlik Doğrulama
Bu API, JWT (JSON Web Token) tabanlı kimlik doğrulama kullanmaktadır. Tüm istekler için geçerli bir erişim tokeni gereklidir.

## Üye Listeleme Endpointleri

### 1. Tüm Üyeleri Listeleme

**Endpoint:** `/api/v1/members/`  
**Method:** `GET`  
**Açıklama:** Mevcut üyeleri listeler. Çeşitli filtreler kullanarak sonuçları daraltabilirsiniz.

#### Query Parametreleri:
- `search`: Ad, soyad, kullanıcı adı veya biyografide arama yapar
- `name`: Ad ve soyad'da birlikte arama yapar
- `first_name`: Sadece ad'da arama yapar
- `last_name`: Sadece soyad'da arama yapar
- `university`: Üniversite ID'si ile filtreleme
- `department`: Bölüm ID'si ile filtreleme
- `graduation_status`: Mezuniyet durumu ID'si ile filtreleme
- `is_verified`: Doğrulanmış hesaplar için filtreleme (true/false)
- `page`: Sayfa numarası (sayfalama için)
- `page_size`: Sayfa başına gösterilecek üye sayısı

#### Başarılı Yanıt (200 OK):
```json
{
  "count": 42,
  "next": "http://[domain]/api/v1/members/?page=2",
  "previous": null,
  "results": [
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
      "has_pending_request": false,
      "is_blocked": false
    },
    // Diğer üyeler...
  ]
}
```

### 2. Üye Filtreleme Seçeneklerini Alma

**Endpoint:** `/api/v1/members/filter-options/`  
**Method:** `GET`  
**Açıklama:** Üye filtreleme için kullanılabilecek seçenekleri (üniversiteler, bölümler, mezuniyet durumları) döndürür.

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

## Kullanıcı Filtreleme Tercihleri

### 1. Kullanıcı Filtreleme Tercihlerini Görüntüleme

**Endpoint:** `/api/v1/members/filter-preferences/`  
**Method:** `GET`  
**Açıklama:** Kullanıcının kayıtlı filtreleme tercihlerini getirir.

#### Başarılı Yanıt (200 OK):
```json
{
  "university": 1,
  "department": 2,
  "graduation_status": 1,
  "is_verified": true
}
```

### 2. Kullanıcı Filtreleme Tercihlerini Güncelleme

**Endpoint:** `/api/v1/members/filter-preferences/`  
**Method:** `PUT`, `PATCH`  
**Açıklama:** Kullanıcının filtreleme tercihlerini günceller.

#### İstek (Request):
```json
{
  "university": 1,
  "department": 2,
  "graduation_status": null,
  "is_verified": true
}
```

#### Başarılı Yanıt (200 OK):
```json
{
  "university": 1,
  "department": 2,
  "graduation_status": null,
  "is_verified": true
}
```

### 3. Kullanıcı Filtreleme Tercihlerini Temizleme

**Endpoint:** `/api/v1/members/filter-preferences/clear/`  
**Method:** `POST`  
**Açıklama:** Kullanıcının tüm filtreleme tercihlerini temizler.

#### Başarılı Yanıt (200 OK):
```json
{
  "detail": "Filter preferences cleared successfully"
}
```

## Takip İşlemleri

Üyeleri takip etmek için Profil API'sindeki takip endpointlerini kullanabilirsiniz:

### Kullanıcıyı Takip Etme veya Takibi Bırakma

**Endpoint:** `/api/v1/profiles/follow/{username}/`  
**Method:** `POST`  
**Açıklama:** Belirtilen kullanıcıyı takip eder veya takibi bırakır.

## React Native Expo Uygulama İçin Entegrasyon

Bu API'yi React Native Expo uygulamanızda kullanmak için aşağıdaki örnek kodları kullanabilirsiniz:

### 1. Üye Listesi Getirme

```javascript
import axios from 'axios';
import { getToken } from './tokenStorage'; // Kendi token saklama sisteminiz

const fetchMembers = async (filters = {}, page = 1) => {
  try {
    const token = await getToken();
    
    // Filtreleri query string'e dönüştür
    const queryParams = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        queryParams.append(key, value);
      }
    });
    queryParams.append('page', page);
    
    const response = await axios.get(`${API_BASE_URL}/api/v1/members/?${queryParams.toString()}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error fetching members:', error);
    throw error;
  }
};
```

### 2. Filtreleme Seçeneklerini Getirme

```javascript
const fetchFilterOptions = async () => {
  try {
    const token = await getToken();
    
    const response = await axios.get(`${API_BASE_URL}/api/v1/members/filter-options/`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error fetching filter options:', error);
    throw error;
  }
};
```

### 3. Kullanıcı Takip İşlemi

```javascript
const toggleFollow = async (username) => {
  try {
    const token = await getToken();
    
    const response = await axios.post(`${API_BASE_URL}/api/v1/profiles/follow/${username}/`, {}, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error toggling follow status:', error);
    throw error;
  }
};
```

### 4. Üye Listesi Componenti Örneği

```jsx
import React, { useState, useEffect } from 'react';
import { FlatList, View, Text, Image, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { fetchMembers } from '../api/membersApi';

const MembersScreen = () => {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(true);
  const [filters, setFilters] = useState({});

  const loadMembers = async (newPage = 1, newFilters = filters) => {
    try {
      setLoading(true);
      const response = await fetchMembers(newFilters, newPage);
      
      if (newPage === 1) {
        setMembers(response.results);
      } else {
        setMembers([...members, ...response.results]);
      }
      
      setHasNextPage(response.next !== null);
      setPage(newPage);
    } catch (error) {
      console.error('Error loading members:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers();
  }, []);

  const handleLoadMore = () => {
    if (hasNextPage && !loading) {
      loadMembers(page + 1);
    }
  };

  const applyFilters = (newFilters) => {
    setFilters(newFilters);
    loadMembers(1, newFilters);
  };

  const renderMemberItem = ({ item }) => (
    <MemberCard 
      member={item}
      onPress={() => navigation.navigate('UserProfile', { userId: item.user.id })}
      onFollowPress={() => toggleFollow(item.user.username)}
    />
  );

  return (
    <View style={styles.container}>
      <FilterBar onApplyFilters={applyFilters} />
      
      <FlatList
        data={members}
        renderItem={renderMemberItem}
        keyExtractor={item => item.user.id.toString()}
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.5}
        ListFooterComponent={loading ? <ActivityIndicator /> : null}
        ListEmptyComponent={
          !loading ? (
            <View style={styles.emptyContainer}>
              <Text>No members found</Text>
            </View>
          ) : null
        }
      />
    </View>
  );
};

// Diğer komponentler ve stiller...

export default MembersScreen;
```

---

*Not: Bu dokümantasyon üye listesi ve ilgili filtreler için API kullanımını açıklamaktadır. Takip işlevselliği için Profile API dokümantasyonuna bakınız.*