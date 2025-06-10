# Chat API Dokümantasyonu

Bu dokümantasyon, Django Chat modülünün React Native Expo projesine entegrasyonu için hazırlanmıştır.

## 📋 İçindekiler
- [Genel Bilgiler](#genel-bilgiler)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoint'ler](#endpoints)
  - [Chat Odaları](#chat-odaları)
  - [Mesajlar](#mesajlar)
  - [Kullanıcı Arama](#kullanıcı-arama)
- [WebSocket](#websocket)
- [React Native Entegrasyonu](#react-native-entegrasyonu)
- [Hata Kodları](#hata-kodları)

## 🔐 Genel Bilgiler

### Authentication
Tüm API endpoint'leri kimlik doğrulaması gerektirir. Her istekte `Authorization` header'ında Bearer token gönderilmelidir.

```javascript
const headers = {
  'Authorization': `Bearer ${userToken}`,
  'Content-Type': 'application/json'
};
```

### Base URL
```
https://your-domain.com/api/v1/chat/
```

## 📞 Endpoint'ler

### Chat Odaları

#### 1. Chat Odalarını Listele
**GET** `/rooms/`

Kullanıcının katıldığı aktif chat odalarını getirir.

```javascript
// React Native örneği
const getChatRooms = async () => {
  try {
    const response = await fetch(`${BASE_URL}/rooms/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Chat odaları getirilirken hata:', error);
  }
};
```

**Response:**
```json
[
  {
    "id": 1,
    "participants": [
      {
        "id": 1,
        "username": "kullanici1",
        "fullName": "Ahmet Yılmaz",
        "avatar": "https://domain.com/media/avatars/user1.jpg",
        "isOnline": false,
        "isVerified": true,
        "university": "İstanbul Üniversitesi"
      }
    ],
    "other_participant": {
      "id": 2,
      "username": "kullanici2",
      "fullName": "Ayşe Kaya",
      "avatar": "https://domain.com/media/avatars/user2.jpg",
      "isOnline": true,
      "isVerified": false,
      "university": "Boğaziçi Üniversitesi"
    },
    "created_at": "2025-05-30T10:30:00Z",
    "updated_at": "2025-05-30T15:45:00Z",
    "is_active": true,
    "last_message": {
      "text": "Merhaba nasılsın?",
      "timestamp": "2025-05-30T15:45:00Z",
      "sender": {
        "id": 2,
        "username": "kullanici2",
        "fullName": "Ayşe Kaya"
      }
    },
    "unread": 3,
    "is_deleted": false
  }
]
```

#### 2. Yeni Chat Odası Oluştur
**POST** `/rooms/`

İki kullanıcı arasında chat odası oluşturur veya mevcut olanı getirir.

```javascript
const createChatRoom = async (userId) => {
  try {
    const response = await fetch(`${BASE_URL}/rooms/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: userId
      })
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Chat odası oluşturulurken hata:', error);
  }
};
```

**Request Body:**
```json
{
  "user_id": 2
}
```

#### 3. Chat Odası Detayı
**GET** `/rooms/{room_id}/`

Belirli bir chat odasının detaylarını getirir ve tüm mesajları okundu olarak işaretler.

```javascript
const getChatRoomDetail = async (roomId) => {
  try {
    const response = await fetch(`${BASE_URL}/rooms/${roomId}/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Chat odası detayı getirilirken hata:', error);
  }
};
```

#### 4. Chat Odasını Sil (Sadece Kendim İçin)
**POST** `/rooms/{room_id}/delete_for_me/`

Chat odasını sadece mevcut kullanıcı için siler. Diğer katılımcı için görünür kalmaya devam eder.

```javascript
const deleteChatForMe = async (roomId) => {
  try {
    const response = await fetch(`${BASE_URL}/rooms/${roomId}/delete_for_me/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Chat silinirken hata:', error);
  }
};
```

#### 5. Chat Odası Arama
**GET** `/rooms/search/?q={query}`

Katılımcı adına göre chat odalarında arama yapar.

```javascript
const searchChatRooms = async (query) => {
  try {
    const response = await fetch(`${BASE_URL}/rooms/search/?q=${encodeURIComponent(query)}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Chat arama hatası:', error);
  }
};
```

### Mesajlar

#### 1. Mesajları Listele (Sayfalama ile)
**GET** `/rooms/{room_id}/messages/?page={page_number}`

Belirli bir chat odasındaki mesajları sayfalama ile getirir.

```javascript
const getMessages = async (roomId, page = 1) => {
  try {
    const response = await fetch(`${BASE_URL}/rooms/${roomId}/messages/?page=${page}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Mesajlar getirilirken hata:', error);
  }
};
```

**Response:**
```json
{
  "count": 150,
  "next": "https://domain.com/api/chat/rooms/1/messages/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "sender": {
        "id": 1,
        "username": "kullanici1",
        "fullName": "Ahmet Yılmaz",
        "avatar": "https://domain.com/media/avatars/user1.jpg",
        "isOnline": false,
        "isVerified": true,
        "university": "İstanbul Üniversitesi"
      },
      "text": "Merhaba nasılsın?",
      "timestamp": "2025-05-30T15:45:00Z",
      "is_read": true,
      "is_delivered": true,
      "attachments": []
    }
  ]
}
```

#### 2. Yeni Mesaj Gönder
**POST** `/rooms/{room_id}/messages/`

Belirli bir chat odasına yeni mesaj gönderir.

```javascript
const sendMessage = async (roomId, messageText, images = []) => {
  try {
    const formData = new FormData();
    formData.append('text', messageText);
    
    // Resim ekleme
    images.forEach((image, index) => {
      formData.append('uploaded_images', {
        uri: image.uri,
        type: image.type,
        name: image.name || `image_${index}.jpg`
      });
    });
    
    const response = await fetch(`${BASE_URL}/rooms/${roomId}/messages/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'multipart/form-data'
      },
      body: formData
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Mesaj gönderilirken hata:', error);
  }
};
```

**Request Body (Form Data):**
```javascript
{
  text: "Merhaba nasılsın?",
  uploaded_images: [File, File, ...] // Opsiyonel
}
```

#### 3. Mesajı Okundu Olarak İşaretle
**POST** `/rooms/{room_id}/messages/{message_id}/mark_as_read/`

Belirli bir mesajı okundu olarak işaretler.

```javascript
const markMessageAsRead = async (roomId, messageId) => {
  try {
    const response = await fetch(`${BASE_URL}/rooms/${roomId}/messages/${messageId}/mark_as_read/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Mesaj okundu işaretlenirken hata:', error);
  }
};
```

### Kullanıcı Arama

#### Mesaj Gönderilecek Kullanıcıları Ara
**GET** `/users/search/?q={query}`

Mesaj gönderilebilecek kullanıcıları arar. Gizlilik ayarları ve engelleme durumları dikkate alınır.

```javascript
const searchUsers = async (query) => {
  try {
    const response = await fetch(`${BASE_URL}/users/search/?q=${encodeURIComponent(query)}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Kullanıcı arama hatası:', error);
  }
};
```

**Response:**
```json
[
  {
    "id": 2,
    "username": "kullanici2",
    "fullName": "Ayşe Kaya",
    "avatar": "https://domain.com/media/avatars/user2.jpg",
    "isOnline": true,
    "isVerified": false,
    "university": "Boğaziçi Üniversitesi"
  }
]
```

## 🔌 WebSocket

### Bağlantı Kurma

Real-time mesajlaşma için WebSocket kullanılır:

```javascript
import { io } from 'socket.io-client';

// WebSocket bağlantısı
const connectToChat = (roomId, userToken) => {
  const socket = io(`ws://your-domain.com/ws/chat/${roomId}/`, {
    auth: {
      token: userToken
    },
    transports: ['websocket']
  });
  
  return socket;
};

// Mesaj dinleme
socket.on('chat_message', (data) => {
  console.log('Yeni mesaj:', data);
  // UI'ı güncelle
});

// Mesaj gönderme
const sendWebSocketMessage = (message) => {
  socket.emit('chat_message', {
    message: message,
    room_id: roomId
  });
};
```

### WebSocket Event'leri

- `chat_message`: Yeni mesaj geldiğinde tetiklenir
- `message_read`: Mesaj okunduğunda tetiklenir
- `user_typing`: Kullanıcı yazıyor durumu
- `user_stopped_typing`: Kullanıcı yazmayı bıraktı

## 📱 React Native Entegrasyonu

### 1. Chat Service Oluşturma

```javascript
// services/chatService.js
import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE_URL = 'https://your-domain.com/api/chat';

class ChatService {
  async getAuthHeaders() {
    const token = await AsyncStorage.getItem('userToken');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async getChatRooms() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${BASE_URL}/rooms/`, {
      method: 'GET',
      headers
    });
    return response.json();
  }

  async createChatRoom(userId) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${BASE_URL}/rooms/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId })
    });
    return response.json();
  }

  async getMessages(roomId, page = 1) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${BASE_URL}/rooms/${roomId}/messages/?page=${page}`, {
      method: 'GET',
      headers
    });
    return response.json();
  }

  async sendMessage(roomId, text, images = []) {
    const token = await AsyncStorage.getItem('userToken');
    const formData = new FormData();
    formData.append('text', text);
    
    images.forEach((image, index) => {
      formData.append('uploaded_images', {
        uri: image.uri,
        type: image.type || 'image/jpeg',
        name: image.name || `image_${index}.jpg`
      });
    });

    const response = await fetch(`${BASE_URL}/rooms/${roomId}/messages/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      },
      body: formData
    });
    return response.json();
  }

  async searchUsers(query) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${BASE_URL}/users/search/?q=${encodeURIComponent(query)}`, {
      method: 'GET',
      headers
    });
    return response.json();
  }
}

export default new ChatService();
```

### 2. Chat Context Oluşturma

```javascript
// context/ChatContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import chatService from '../services/chatService';

const ChatContext = createContext();

const initialState = {
  chatRooms: [],
  currentChat: null,
  messages: [],
  loading: false,
  error: null
};

const chatReducer = (state, action) => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_CHAT_ROOMS':
      return { ...state, chatRooms: action.payload };
    case 'SET_CURRENT_CHAT':
      return { ...state, currentChat: action.payload };
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [action.payload, ...state.messages] };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    default:
      return state;
  }
};

export const ChatProvider = ({ children }) => {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  const loadChatRooms = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const rooms = await chatService.getChatRooms();
      dispatch({ type: 'SET_CHAT_ROOMS', payload: rooms });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const loadMessages = async (roomId, page = 1) => {
    try {
      const response = await chatService.getMessages(roomId, page);
      if (page === 1) {
        dispatch({ type: 'SET_MESSAGES', payload: response.results });
      } else {
        dispatch({ type: 'SET_MESSAGES', payload: [...state.messages, ...response.results] });
      }
      return response;
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    }
  };

  const sendMessage = async (roomId, text, images = []) => {
    try {
      const message = await chatService.sendMessage(roomId, text, images);
      dispatch({ type: 'ADD_MESSAGE', payload: message });
      return message;
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    }
  };

  return (
    <ChatContext.Provider value={{
      ...state,
      loadChatRooms,
      loadMessages,
      sendMessage,
      dispatch
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
```

### 3. Chat Bileşeni Örneği

```javascript
// components/ChatScreen.js
import React, { useEffect, useState } from 'react';
import { View, FlatList, TextInput, TouchableOpacity, Text } from 'react-native';
import { useChat } from '../context/ChatContext';

const ChatScreen = ({ route }) => {
  const { roomId } = route.params;
  const { messages, loadMessages, sendMessage } = useChat();
  const [newMessage, setNewMessage] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    loadMessages(roomId, 1);
  }, [roomId]);

  const handleSendMessage = async () => {
    if (newMessage.trim()) {
      await sendMessage(roomId, newMessage);
      setNewMessage('');
    }
  };

  const renderMessage = ({ item }) => (
    <View style={{ padding: 10, backgroundColor: '#f0f0f0', margin: 5 }}>
      <Text style={{ fontWeight: 'bold' }}>{item.sender.fullName}</Text>
      <Text>{item.text}</Text>
      <Text style={{ fontSize: 12, color: '#666' }}>
        {new Date(item.timestamp).toLocaleTimeString()}
      </Text>
    </View>
  );

  return (
    <View style={{ flex: 1 }}>
      <FlatList
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id.toString()}
        inverted
      />
      <View style={{ flexDirection: 'row', padding: 10 }}>
        <TextInput
          style={{ flex: 1, borderWidth: 1, padding: 10 }}
          value={newMessage}
          onChangeText={setNewMessage}
          placeholder="Mesajınızı yazın..."
        />
        <TouchableOpacity onPress={handleSendMessage} style={{ padding: 10, backgroundColor: '#007bff' }}>
          <Text style={{ color: 'white' }}>Gönder</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

export default ChatScreen;
```

## ⚠️ Hata Kodları

### HTTP Status Kodları

- `200`: Başarılı işlem
- `201`: Kaynak başarıyla oluşturuldu
- `400`: Geçersiz istek
- `401`: Kimlik doğrulaması gerekli
- `403`: Yasaklanmış (gizlilik ayarları, engelleme)
- `404`: Kaynak bulunamadı
- `500`: Sunucu hatası

### Özel Hata Mesajları

```json
{
  "detail": "Bu kullanıcıyı engellediniz. Mesaj göndermek için engeli kaldırın."
}
```

```json
{
  "detail": "Bu kullanıcı sizi engellemiş. Mesaj gönderemezsiniz."
}
```

```json
{
  "detail": "kullanici2 sadece takipçilerinden mesaj kabul ediyor."
}
```

## 📝 Notlar

1. **Sayfalama**: Mesajlar en yeniden eskiye doğru sıralanır ve sayfalama ile getirilir.
2. **Gizlilik**: Kullanıcıların mesaj gizlilik ayarları otomatik olarak kontrol edilir.
3. **Engelleme**: Engellenmiş kullanıcılarla mesajlaşma engellenir.
4. **Resim Yükleme**: Mesajlara çoklu resim ekleme desteklenir.
5. **Real-time**: WebSocket ile gerçek zamanlı mesajlaşma sağlanır.
6. **Silme**: Chat odaları sadece kullanıcı için silinir, kalıcı silme yapılmaz.

## 🔧 Test Etme

API endpoint'lerini test etmek için Postman veya benzer araçları kullanabilirsiniz. Authorization header'ını eklemeyi unutmayın:

```
Authorization: Bearer your_jwt_token_here
```

---

**Not**: Bu dokümantasyon Django Chat modülünün mevcut durumuna göre hazırlanmıştır. Yeni özellikler eklendiğinde dokümantasyon güncellenmelidir.
