/**
 * Bildirim sistemi için JavaScript fonksiyonları
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elementleri
    const notificationDropdown = document.querySelector('.dropdown-notifications');
    const notificationBadge = document.querySelector('.badge-notifications');
    const notificationsList = document.querySelector('.dropdown-notifications-list');
    
    // CSRF token alma fonksiyonu
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Bildirimleri yükle
    function loadNotifications() {
        if (!notificationsList) return;
        
        fetch('/notifications/dropdown/')
            .then(response => response.text())
            .then(html => {
                // Dropdown içeriğini güncelle
                notificationsList.innerHTML = html;
                
                // Tümünü okundu olarak işaretleme butonuna olay dinleyicisi ekle
                setupMarkAllAsRead();
                
                // Tek bildirim okundu olarak işaretleme butonlarına olay dinleyicisi ekle
                setupMarkAsRead();
            })
            .catch(error => console.error('Bildirimler yüklenemedi:', error));
    }
    
    // Okunmamış bildirim sayısını güncelle
    function updateUnreadCount() {
        if (!notificationBadge) return;
        
        fetch('/notifications/unread-count/')
            .then(response => response.json())
            .then(data => {
                if (data.count > 0) {
                    notificationBadge.classList.remove('d-none');
                    // Eğer numara göstermek istiyorsanız:
                    // notificationBadge.textContent = data.count;
                } else {
                    notificationBadge.classList.add('d-none');
                }
            })
            .catch(error => console.error('Bildirim sayısı alınamadı:', error));
    }
    
    // Tümünü okundu olarak işaretle butonunu ayarla
    function setupMarkAllAsRead() {
        const markAllReadBtn = document.querySelector('.mark-all-read');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', function(e) {
                e.preventDefault();
                
                fetch('/notifications/mark-all-read/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Bildirimleri tekrar yükle
                        loadNotifications();
                        // Bildirim sayısını güncelle
                        updateUnreadCount();
                    }
                })
                .catch(error => console.error('Bildirimler okundu olarak işaretlenemedi:', error));
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
                
                fetch(`/notifications/${notificationId}/mark-read/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Bildirimi okundu olarak işaretle (UI güncelleme)
                        const notificationItem = this.closest('.dropdown-notifications-item');
                        notificationItem.classList.remove('notification-unread');
                        this.style.display = 'none';
                        
                        // Bildirim sayısını güncelle
                        updateUnreadCount();
                    }
                })
                .catch(error => console.error('Bildirim okundu olarak işaretlenemedi:', error));
            });
        });
    }
    
    // Bildirim dropdown'ı açıldığında bildirimleri yükle
    if (notificationDropdown) {
        notificationDropdown.addEventListener('show.bs.dropdown', function() {
            loadNotifications();
        });
    }
    
    // Sayfa yüklendiğinde okunmamış bildirim sayısını güncelle
    updateUnreadCount();
    
    // Sayfa aktif hale geldiğinde bildirim sayısını güncelle (sekme değişikliğinde)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            updateUnreadCount();
        }
    });
    
    // Belirli aralıklarla bildirim sayısını güncelle (her 2 dakikada bir)
    setInterval(updateUnreadCount, 120000);
}); 