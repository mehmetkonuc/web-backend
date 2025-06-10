/**
 * Header bölümündeki mesaj bildirimlerini yöneten JavaScript dosyası
 */

document.addEventListener('DOMContentLoaded', function() {
    // TEMEL DOM ELEMANLARI
    const messagesDropdown = document.querySelector('.dropdown-messages');
    const messagesList = document.querySelector('.dropdown-messages .messages-list');
    const messagesBadge = document.querySelector('.badge-messages');
    const messagesBadgeCount = document.querySelector('.badge-messages-count');
    const markAllReadButton = document.querySelector('.dropdown-messages-read-all');
    
    console.log('SAYFA YÜKLENDI - Badge elementleri:', 
        messagesBadge ? 'Bulundu' : 'Bulunamadı', 
        messagesBadgeCount ? 'Bulundu' : 'Bulunamadı');
    
    // TEMEL DEĞIŞKENLER
    let chatSocket;
    let isConnecting = false;
    
    // "Tümünü okundu olarak işaretle" butonuna click event ekle
    if (markAllReadButton) {
        markAllReadButton.addEventListener('click', function(e) {
            e.preventDefault();
            if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
                console.log('📨 Tüm sohbetler okundu olarak işaretleniyor...');
                sendCommand('mark_all_as_read');
            }
        });
    }
    
    // WEBSOCKET BAĞLANTI FONKSİYONU
    function setupWebSocket() {
        if (isConnecting || (chatSocket && chatSocket.readyState === WebSocket.OPEN)) {
            return;
        }
        
        isConnecting = true;
        
        // WebSocket URL'sini oluştur
        const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = `${wsProtocol}${window.location.host}/ws/chat/`;
        
        console.log('⚡️ WebSocket bağlantısı başlatılıyor:', wsUrl);
        
        // Bağlantıyı oluştur
        chatSocket = new WebSocket(wsUrl);
        
        // Bağlantı açıldığında
        chatSocket.onopen = function() {
            console.log('✅ WebSocket bağlantısı BAŞARILI');
            isConnecting = false;
            
            // İlk verileri yükle
            sendCommand('get_unread_count');
            sendCommand('get_recent_rooms');
        };
        
        // Mesaj geldiğinde - TÜM MESAJLAR İÇİN ÇALIŞIR
        chatSocket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('📥 YENİ MESAJ ALINDI:', data);
                
                // YENİ MESAJ BİLDİRİMİ
                if (data.type === 'message_notification') {
                    console.log('💬 YENİ CHAT MESAJI BİLDİRİMİ!');
                    
                    // Badge'i anında göster
                    if (messagesBadge) {
                        messagesBadge.classList.remove('d-none');
                        console.log('🔴 Badge gösterildi!');
                    }
                    
                    // Tümünü okundu olarak işaretle butonunu göster
                    if (markAllReadButton) {
                        markAllReadButton.classList.remove('d-none');
                        console.log('📩 "Tümünü Oku" butonu gösterildi!');
                    }
                    
                    // Diğer işlemleri de yap
                    showBrowserNotification(data.message, data.room_id);
                    sendCommand('get_unread_count');
                    sendCommand('get_recent_rooms');                
                }
                
                // OKUNMAMIŞ SOHBET SAYISI
                else if (data.type === 'unread_count') {
                    console.log('📊 Okunmamış sohbet sayısı:', data.count);
                    updateUnreadBadge(data.count);
                }
                
                // SON SOHBETLER
                else if (data.type === 'recent_rooms') {
                    console.log('📋 Son sohbetler güncellendi, oda sayısı:', data.rooms?.length || 0);
                    updateChatList(data.rooms || []);
                }
                  // TÜM MESAJLAR OKUNDU
                else if (data.type === 'all_messages_read') {
                    console.log('✅ Tüm mesajlar okundu olarak işaretlendi');
                    
                    // Badge'i gizle
                    if (messagesBadge) {
                        messagesBadge.classList.add('d-none');
                    }
                    
                    // Sayacı gizle ve içeriğini temizle
                    if (messagesBadgeCount) {
                        messagesBadgeCount.textContent = '';
                        messagesBadgeCount.classList.add('d-none');
                    }
                    
                    // Tümünü okundu olarak işaretle butonunu gizle
                    if (markAllReadButton) {
                        markAllReadButton.classList.add('d-none');
                    }
                    
                    // Sohbet listesini güncelle
                    sendCommand('get_recent_rooms');
                    
                    // Sayacı sıfırla
                    if (messagesBadgeCount) {
                        messagesBadgeCount.textContent = '';
                        messagesBadgeCount.classList.add('d-none');
                    }
                    
                    // Mesaj listesini güncelle - "okunmamış mesaj yok" mesajını göster
                    if (messagesList) {
                        messagesList.innerHTML = '<li class="list-group-item text-center py-3"><span class="text-muted">Okunmamış mesajınız yok</span></li>';
                    }
                }
                
            } catch (error) {
                console.error('⚠️ WebSocket mesajı işlenemedi:', error);
            }
        };
        
        // Bağlantı kapandığında
        chatSocket.onclose = function() {
            console.log('❌ WebSocket bağlantısı koptu - yeniden deneniyor...');
            isConnecting = false;
            
            // 3 saniye sonra yeniden bağlan
            setTimeout(setupWebSocket, 3000);
        };
        
        // Hata oluştuğunda
        chatSocket.onerror = function(error) {
            console.error('⚠️ WebSocket hatası:', error);
            isConnecting = false;
        };
    }
    
    // WebSocket komut gönderme fonksiyonu
    function sendCommand(command, data = {}) {
        if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
            console.warn('⚠️ WebSocket bağlı değil, komut gönderilemedi:', command);
            return false;
        }
        
        const message = {
            command: command,
            ...data
        };
        
        chatSocket.send(JSON.stringify(message));
        console.log('📤 Komut gönderildi:', command);
        return true;
    }    // Badge güncelleme fonksiyonu
    function updateUnreadBadge(count) {
        // Ana badge (ikon üzerindeki)
        if (messagesBadge) {
            if (count > 0) {
                messagesBadge.classList.remove('d-none');
                console.log('🔴 Badge gösteriliyor, okunmamış sohbet sayısı:', count);
            } else {
                messagesBadge.classList.add('d-none');
                console.log('⚪ Badge gizleniyor, okunmamış sohbet yok');
            }
        }
        
        // Dropdown içindeki sayaç ve tümünü okundu olarak işaretle butonu
        if (messagesBadgeCount) {
            if (count > 0) {
                messagesBadgeCount.textContent = count + ' Yeni';
                messagesBadgeCount.classList.remove('d-none');
                
                // Tümünü okundu olarak işaretle butonunu göster
                if (markAllReadButton) {
                    markAllReadButton.classList.remove('d-none');
                }
            } else {
                messagesBadgeCount.textContent = '';
                messagesBadgeCount.classList.add('d-none');
                
                // Tümünü okundu olarak işaretle butonunu gizle
                if (markAllReadButton) {
                    markAllReadButton.classList.add('d-none');
                }
            }
        }
    }// Mesaj listesini güncelleme
    function updateChatList(rooms) {
        if (!messagesList) return;
        
        // Sadece okunmamış mesajları olan odaları filtrele
        const unreadRooms = rooms.filter(room => room.unread_count > 0);
        
        if (unreadRooms.length === 0) {
            messagesList.innerHTML = '<li class="list-group-item text-center py-3"><span class="text-muted">Okunmamış mesajınız yok</span></li>';
            return;
        }
        
        messagesList.innerHTML = '';
        unreadRooms.forEach(room => {
            const li = document.createElement('li');
            li.className = 'list-group-item list-group-item-action dropdown-notifications-item notification-unread';
            
            // Son mesaj bilgilerini al
            let messageContent = 'Henüz mesaj yok';
            let messageTime = '';            
            if (room.last_message) {
                messageContent = room.last_message.content;
                if (messageContent.length > 25) {
                    messageContent = messageContent.substring(0, 25) + '...';
                }
                
                messageTime = room.last_message.created_at;
            }

            let avatarHTML = '';
            if (room.last_message.sender_avatar) {
                avatarHTML = `<img src="${room.last_message.sender_avatar}" class="user-avatar">`;
            } else {
                const firstInitial = room.last_message.sender_first_name?.charAt(0)?.toUpperCase() || '';
                const lastInitial = room.last_message.sender_last_name?.charAt(0)?.toUpperCase() || '';
                avatarHTML = `
                    <span class="avatar-initial rounded-circle bg-label-primary">
                        ${firstInitial}${lastInitial}
                    </span>`;
            }



            li.innerHTML = `
                <a href="/chat/${room.id}/" class="d-flex text-reset">
                    <div class="flex-shrink-0 me-3">
                        <div class="avatar avatar-md">
                            ${avatarHTML}
                        </div>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="small mb-1">${room.last_message.sender_full_name}</h6>
                        <small class="mb-1 d-block text-body">${messageContent}</small>
                        <small class="text-body-secondary">${messageTime}</small>
                    </div>
                    <div class="flex-shrink-0 dropdown-notifications-actions">
                        <div class="dropdown-notifications-archive">
                            <span class="badge bg-primary rounded-pill">${room.unread_count}</span>
                        </div>
                    </div>
                </a>`;
            
            messagesList.appendChild(li);
        });
        
        // "Tümünü gör butonu" kaldırıldı - zaten header.html'de mevcut
    }
    
    // Tarayıcı bildirimi
    function showBrowserNotification(message, roomId) {
        if (!("Notification" in window)) return;
        
        if (Notification.permission === "granted") {
            createNotification(message, roomId);
        } 
        else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(function (permission) {
                if (permission === "granted") {
                    createNotification(message, roomId);
                }
            });
        }
    }
    
    // Bildirim oluşturma
    function createNotification(message, roomId) {
        const notification = new Notification(`Yeni mesaj: ${message.sender_name}`, {
            body: message.content,
            icon: '/static/assets/img/avatars/1.png'
        });
        
        notification.onclick = function() {
            window.open(`/chat/${roomId}/`, '_self');
        };
    }

    // Sayfa görünür olduğunda WebSocket'i kontrol et
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            console.log('👁️ Sayfa aktif, WebSocket kontrolü yapılıyor');
            if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
                setupWebSocket();
            }
        }
    });
    
    // WebSocket bağlantısını başlat
    setupWebSocket();
    
    // Her 30 saniyede bir bağlantıyı kontrol et 
    setInterval(function() {
        if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
            console.log('⏱️ Periyodik kontrol: WebSocket yeniden bağlanıyor');
            setupWebSocket();
        }
    }, 30000);
});