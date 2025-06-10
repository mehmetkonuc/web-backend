/**
 * Relative Time Updater
 * 
 * Bu script, sayfadaki göreceli zaman gösterimlerini periyodik olarak günceller.
 * Örneğin, "2 dakika önce" görüntüsünü sayfayı yenilemeden "3 dakika önce" olarak günceller.
 * 
 * Kullanım:
 * 1. Bu dosyayı static/js/relative-time.js olarak kaydedin
 * 2. Template'inize ekleyin: <script src="{% static 'js/relative-time.js' %}"></script>
 * 3. Zaman gösterimlerini şu data attribute ile işaretleyin: data-timestamp="2025-04-10T18:03:04.510113+03:00"
 *    <span class="relative-time" data-timestamp="{{ post.created_at|date:'c' }}">{{ post.created_at|relative_time }}</span>
 */

document.addEventListener('DOMContentLoaded', function() {
  // Her 60 saniyede bir zaman etiketlerini güncelle
  setInterval(updateRelativeTimes, 60000);
  
  // Sayfa yüklendiğinde ilk güncellemeyi yap
  updateRelativeTimes();
  
  function updateRelativeTimes() {
    const timeElements = document.querySelectorAll('.relative-time[data-timestamp]');
    const now = new Date();
    
    timeElements.forEach(element => {
      const timestamp = new Date(element.getAttribute('data-timestamp'));
      element.textContent = getRelativeTimeString(timestamp, now);
    });
  }
  
  function getRelativeTimeString(date, now) {
    // İki tarih arasındaki farkı hesapla (milisaniye cinsinden)
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    // Şimdi (1 dakikadan az)
    if (diffMin < 1) {
      return 'şimdi';
    }
    
    // Dakika (1 saatten az)
    if (diffHour < 1) {
      return `${diffMin} dakika önce`;
    }
    
    // Saat (1 günden az)
    if (diffDay < 1) {
      return `${diffHour} saat önce`;
    }
    
    // Dün
    if (diffDay === 1) {
      return 'Dün';
    }
    
    // Hafta içi (7 günden az)
    if (diffDay < 7) {
      const days = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
      return days[date.getDay()];
    }
    
    // Hafta (4 haftadan az)
    if (diffDay < 28) {
      const weeks = Math.floor(diffDay / 7);
      return `${weeks} hafta önce`;
    }
    
    // Ay (12 aydan az)
    if (diffDay < 365) {
      const months = Math.floor(diffDay / 30);
      return `${months} ay önce`;
    }
    
    // Yıl
    const years = Math.floor(diffDay / 365);
    return `${years} yıl önce`;
  }
});
