/**
 * Bildirim sistemi için JavaScript fonksiyonları
 * WebSocket tabanlı bildirim sistemi
 */

document.addEventListener('DOMContentLoaded', function() {    // DOM elementleri
    const notificationDropdown = document.querySelector('.dropdown-notifications');
    const notificationBadge = document.querySelector('.badge-notifications');
    const headerNotifications = document.querySelector('.manuel-list');let notificationSocket = null;
    let unreadNotificationCount = 0; // Okunmamış bildirim sayısını takip etmek için değişken
    let isConnecting = false; // Bağlantı durumunu takip etmek için
    
    // WebSocket bağlantısını başlat (kullanıcı oturum açmışsa)
    function connectWebSocket() {
        // Eğer bağlantı zaten kuruluyorsa veya açıksa işlem yapma
        if (isConnecting || (notificationSocket && notificationSocket.readyState === WebSocket.OPEN)) {
            return;
        }
        
        isConnecting = true;
        
        // Kullanıcı oturum açmışsa (bildirim badge'i varsa)
        if (notificationBadge && headerNotifications) {
            // Secure WebSocket protokolünü (wss) kullan veya normal (ws) - URL'e göre
            const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const wsURL = `${wsProtocol}${window.location.host}/ws/notifications/`;
            
            console.log('⚡️ Bildirim WebSocket bağlantısı başlatılıyor:', wsURL);
            notificationSocket = new WebSocket(wsURL);
              notificationSocket.onopen = function(e) {
                console.log('WebSocket bağlantısı başarıyla kuruldu');
                // Bağlantı kurulduğunda, okunmamış bildirim sayısını iste
                notificationSocket.send(JSON.stringify({
                    'command': 'get_unread_count'
                }));
                
                // Bildirim içeriğini hemen yükle (dropdown açık olmasa bile)
                requestNotifications();
            };
              notificationSocket.onmessage = function(e) {
                const data = JSON.parse(e.data);
                console.log('📥 Bildirim mesajı alındı:', data.type);
                
                // Yeni bildirim geldiğinde
                if (data.type === 'new_notification') {
                    console.log('🔔 Yeni bildirim alındı');
                    handleNewNotification(data.notification);
                }
                // Okunmamış bildirim sayısı güncellendiğinde
                else if (data.type === 'unread_count') {
                    console.log('📊 Okunmamış bildirim sayısı:', data.count);
                    unreadNotificationCount = data.count; // Sayacı güncelle
                    updateUnreadBadge(data.count);
                }
                // Bildirim okundu olarak işaretlendiğinde
                else if (data.type === 'notification_read') {
                    console.log('✓ Bildirim okundu:', data.notification_id);
                    handleNotificationRead(data.notification_id);
                }
                // Bildirimleri listeleme yanıtı
                else if (data.type === 'notifications_list') {
                    console.log('📋 Bildirim listesi güncellendi, bildirim sayısı:', data.notifications?.length || 0);
                    renderNotifications(data.notifications);
                }
                // Tüm bildirimleri okundu olarak işaretleme yanıtı
                else if (data.type === 'all_notifications_read') {
                    console.log('✓✓ Tüm bildirimler okundu olarak işaretlendi');
                    handleAllNotificationsRead();
                }
            };
              notificationSocket.onclose = function(e) {
                console.log('❌ WebSocket bağlantısı kapandı. Tekrar bağlanmaya çalışılacak...');
                isConnecting = false;
                
                // Bağlantı kapandığında tekrar bağlanmayı dene (5 saniye sonra)
                setTimeout(function() {
                    connectWebSocket();
                }, 5000);
            };
              notificationSocket.onerror = function(err) {
                console.error('⚠️ WebSocket hatası:', err);
                isConnecting = false;
            };
        }
    }
      // Bildirimleri WebSocket üzerinden iste
    function requestNotifications() {
        if (notificationSocket && notificationSocket.readyState === WebSocket.OPEN) {
            console.log('📤 Bildirimler isteniyor...');
            notificationSocket.send(JSON.stringify({
                'command': 'get_notifications'
            }));
        } else {
            console.warn('⚠️ WebSocket bağlı değil, bildirimler istenemedi');
            // WebSocket bağlı değilse, bağlanmayı dene
            connectWebSocket();
        }
    }      // Bildirimleri HTML olarak render et
    function renderNotifications(notifications) {
        if (!headerNotifications) return;
        
        console.log('🖌️ Bildirimler render ediliyor', notifications.length);
        
        // Filtrele ve okunmamış bildirim sayısını bul
        const unreadNotifications = notifications.filter(notification => !notification.is_read);
        console.log('📊 Okunmamış bildirim sayısı:', unreadNotifications.length);
        
        // Header'daki badge sayısını güncelle
        const headerCountBadge = document.querySelector('.badge-count');
        if (headerCountBadge) {
            if (unreadNotifications.length > 0) {
                headerCountBadge.textContent = `${unreadNotifications.length} Yeni`;
                headerCountBadge.classList.remove('d-none');
            } else {
                headerCountBadge.textContent = '';
                headerCountBadge.classList.add('d-none');
            }
        }
        
        // Tümünü okundu olarak işaretle butonunu güncelle
        const markAllReadBtn = document.querySelector('.dropdown-notifications-all');
        if (markAllReadBtn) {            if (unreadNotifications.length > 0) {
                markAllReadBtn.classList.remove('d-none');
            } else {
                markAllReadBtn.classList.add('d-none');
            }
        }

        // No notifications case
        if (notifications.length === 0) {
            headerNotifications.innerHTML = `
                <ul class="list-group list-group-flush">
<li class="list-group-item text-center py-3"><span class="text-muted">Okunmamış bildiriminiz yok</span></li>
                </ul>
            `;
            return;
        }

        // Generate the notifications list HTML
        let html = `
                <ul class="list-group list-group-flush">
        `;
        
        notifications.forEach(notification => {
            const readClass = notification.is_read ? 'marked-as-read' : 'notification-unread';
            
            let avatarContent = '';
            if (notification.avatar) {
                // Burada sender'ın avatar kullanıp kullanmadığını bilemeyeceğimiz için sadece initial gösterelim
                avatarContent = `<img src="${notification.avatar}" alt="{{ post.user.username }}" class="user-avatar">`;
            } else {
                avatarContent = `<div class="avatar-initial rounded-circle bg-label-primary">
                    <i class="icon-base ti ${notification.icon_class}"></i>
                </div>`;
            }
            

            html += `
                <li class="list-group-item list-group-item-action dropdown-notifications-item ${readClass} waves-effect cursor-pointer" 
                    data-id="${notification.id}" data-url="${notification.url || ''}">
                    <div class="d-flex">
                        <div class="flex-shrink-0 me-3">
                            <div class="avatar">
                                ${avatarContent}
                            </div>
                        </div>
                        <div class="flex-grow-1">
                            <h6 class="small mb-1">${notification.title}</h6>
                            <small class="mb-1 d-block text-body">${notification.text}</small>
                            <small class="text-body-secondary">${notification.created_at}</small>
                        </div>
                        <div class="flex-shrink-0 dropdown-notifications-actions">
                            ${!notification.is_read ? `
                                <a href="javascript:void(0)" class="dropdown-notifications-read mark-read" data-id="${notification.id}">
                                    <span class="badge badge-dot"></span>
                                </a>
                            ` : ''}
                        </div>
                    </div>
                </li>
            `;
        });
        
        html += `
                </ul>
        `;


        headerNotifications.innerHTML = html;

        // Tümünü okundu olarak işaretleme butonuna olay dinleyicisi ekle
        setupMarkAllAsRead();
        
        // Tek bildirim okundu olarak işaretleme butonlarına olay dinleyicisi ekle
        setupMarkAsRead();
        
        // Bildirimlere tıklama olay dinleyicisi ekle
        setupNotificationClicks();
    }
    
    // Bildirimlere tıklama işlevselliği ekle
    function setupNotificationClicks() {
        const notificationItems = document.querySelectorAll('.dropdown-notifications-item');
        notificationItems.forEach(item => {
            item.addEventListener('click', function(e) {
                // Eğer tıklanan yer "mark-read" butonuysa, sadece okundu olarak işaretle ama yönlendirme yapma
                if (e.target.closest('.mark-read') || e.target.closest('.dropdown-notifications-read')) {
                    e.stopPropagation();
                    return;
                }
                
                const notificationId = this.getAttribute('data-id');
                const url = this.getAttribute('data-url');
                
                // Önce bildirimi okundu olarak işaretle
                if (notificationSocket && notificationSocket.readyState === WebSocket.OPEN) {
                    notificationSocket.send(JSON.stringify({
                        'command': 'mark_as_read',
                        'notification_id': notificationId
                    }));
                }
                
                // Eğer URL varsa o sayfaya yönlendir
                if (url && url.trim() !== '') {
                    window.location.href = url;
                }
            });
        });
    }      // Yeni bildirim geldiğinde
    function handleNewNotification(notification) {
        // Badge'i direkt göster
        if (notificationBadge) {
            notificationBadge.classList.remove('d-none');
            console.log('🔴 Bildirim badge gösterildi!');
        }
        
        // Bildirim sayısını güncelle
        updateUnreadCount();
        
        // Bildirimleri yeniden yükle (her durumda)
        requestNotifications();
        
        // Opsiyonel: Tarayıcı bildirimi göster
        showBrowserNotification(notification);
    }
    
    // Bildirimi okundu olarak işaretlendiğinde
    function handleNotificationRead(notificationId) {
        const notificationItem = document.querySelector(`.dropdown-notifications-item[data-id="${notificationId}"]`);
        if (notificationItem) {
            notificationItem.classList.add('marked-as-read');
            notificationItem.classList.remove('notification-unread');
            const markReadBtn = notificationItem.querySelector('.mark-read');
            if (markReadBtn) {
                markReadBtn.style.display = 'none';
            }
        }
        updateUnreadCount();
    }
      // Tüm bildirimleri okundu olarak işaretleme yanıtı
    function handleAllNotificationsRead() {
        const notificationItems = document.querySelectorAll('.dropdown-notifications-item:not(.marked-as-read)');
        notificationItems.forEach(item => {
            item.classList.add('marked-as-read');
            item.classList.remove('notification-unread');
            const markReadBtn = item.querySelector('.mark-read');
            if (markReadBtn) {
                markReadBtn.style.display = 'none';
            }
        });
        
        updateUnreadCount();
        
        // Başlıktaki 'X Yeni' sayacını ve mark all read butonunu gizle
        const headerCountBadge = document.querySelector('.badge-count');
        const markAllReadBtn = document.querySelector('.dropdown-notifications-all');
        
        if (headerCountBadge) {
            headerCountBadge.textContent = '';
            headerCountBadge.classList.add('d-none');
        }
        
        if (markAllReadBtn) {
            markAllReadBtn.classList.add('d-none');
        }
        
        // Badge'i gizle
        if (notificationBadge) {
            notificationBadge.classList.add('d-none');
        }
        
        // "Okunmamış bildiriminiz yok" mesajını göster
        if (headerNotifications) {
            headerNotifications.innerHTML = `
                <ul class="list-group list-group-flush">
                    <li class="list-group-item text-center py-3"><span class="text-muted">Okunmamış bildiriminiz yok</span></li>
                </ul>
            `;
        }
    }
    
    // Tarayıcı bildirimi göster
    function showBrowserNotification(notification) {
        // Tarayıcı bildirimlerine izin verilip verilmediğini kontrol et
        if (Notification.permission === 'granted') {
            const title = notification.title || 'Yeni Bildirim';
            const options = {
                body: notification.text,
                icon: '/static/images/notification-icon.png', // Opsiyonel: bildirim ikonu
            };
            
            const browserNotification = new Notification(title, options);
            
            browserNotification.onclick = function() {
                // Bildirime tıklandığında, notification.url varsa o sayfaya yönlendir
                if (notification.url && notification.url.trim() !== '') {
                    window.open(notification.url, '_blank');
                }
                browserNotification.close();
            };
        }
        // İzin istenmediyse, izin iste
        else if (Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }
      // Okunmamış bildirim sayısını güncelle
    function updateUnreadCount() {
        if (!notificationBadge) return;
        
        if (notificationSocket && notificationSocket.readyState === WebSocket.OPEN) {
            console.log('📤 Okunmamış bildirim sayısı isteniyor...');
            notificationSocket.send(JSON.stringify({
                'command': 'get_unread_count'
            }));
        } else {
            console.warn('⚠️ WebSocket bağlı değil, okunmamış bildirim sayısı istenemedi');
            // WebSocket bağlı değilse, bağlanmayı dene
            connectWebSocket();
        }
    }    // Bildirim badge'ini güncelle
    function updateUnreadBadge(count) {
        if (!notificationBadge) return;
        
        if (count > 0) {
            notificationBadge.classList.remove('d-none');
            console.log('🔴 Badge gösteriliyor, okunmamış bildirim sayısı:', count);
        } else {
            notificationBadge.classList.add('d-none');
            console.log('⚪ Badge gizleniyor, okunmamış bildirim yok');
        }
        
        // Eğer dropdown açıksa, header'daki badge'i de güncelle
        const headerCountBadge = document.querySelector('.badge-count');
        const markAllReadBtn = document.querySelector('.dropdown-notifications-all');

        if (headerCountBadge) {
            if (count > 0) {
                headerCountBadge.textContent = `${count} Yeni`;
                headerCountBadge.classList.remove('d-none');
                
                if (markAllReadBtn) {
                    markAllReadBtn.classList.remove('d-none');
                }
            } else {
                headerCountBadge.textContent = '';
                headerCountBadge.classList.add('d-none');
                
                if (markAllReadBtn) {
                    markAllReadBtn.classList.add('d-none');
                }
            }
        }
    }
    
    // Tümünü okundu olarak işaretle butonunu ayarla
    function setupMarkAllAsRead() {
        const markAllReadBtn = document.querySelector('.mark-all-read');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', function(e) {
                e.preventDefault();
                
                if (notificationSocket && notificationSocket.readyState === WebSocket.OPEN) {
                    notificationSocket.send(JSON.stringify({
                        'command': 'mark_all_as_read'
                    }));
                    
                }
            });
        }
    }
    
    // Tek bildirimi okundu olarak işaretle butonlarını ayarla
    function setupMarkAsRead() {
        const markReadBtns = document.querySelectorAll('.mark-read');
        markReadBtns.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const notificationId = this.getAttribute('data-id');
                
                if (notificationSocket && notificationSocket.readyState === WebSocket.OPEN) {
                    notificationSocket.send(JSON.stringify({
                        'command': 'mark_as_read',
                        'notification_id': notificationId
                    }));
                }
            });
        });
    }    // Sayfa aktif hale geldiğinde sadece websocket bağlantısını kontrol et (sekme değişikliğinde)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            console.log('👁️ Sayfa aktif, Bildirim WebSocket kontrolü yapılıyor');
            // Sadece WebSocket bağlantı durumunu kontrol et, veri isteme
            if (!notificationSocket || notificationSocket.readyState !== WebSocket.OPEN) {
                connectWebSocket();
            }
        }
    });
    
    // Sayfa ilk yüklendiğinde bir kez veri iste
    updateUnreadCount();
      // WebSocket bağlantısını başlat
    connectWebSocket();
    
    // Her 30 saniyede bir bağlantıyı kontrol et
    setInterval(function() {
        if (!notificationSocket || notificationSocket.readyState !== WebSocket.OPEN) {
            console.log('⏱️ Periyodik kontrol: Bildirim WebSocket yeniden bağlanıyor');
            connectWebSocket();
        }
    }, 30000);
    
});