from django import template
from django.utils import timezone
from datetime import datetime, timedelta
from django.utils.translation import gettext as _
from django.template.loader import render_to_string

register = template.Library()

@register.filter
def relative_time(value):
    """
    Bir datetime nesnesini göreceli zaman formatına dönüştürür.
    Örnek: "şimdi", "5 dakika önce", "1 saat önce", "Dün", "Çarşamba", "1 ay önce" vb.
    
    Kullanım: {{ post.created_at|relative_time }}
    """
    if not value:
        return ""
    
    # Timezone-aware değilse, şu anki timezone'u ekle
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    
    now = timezone.now()
    diff = now - value
    
    # Saniye farkı
    seconds_diff = diff.total_seconds()
    
    # Şimdi veya az önce (1 dakikadan az)
    if seconds_diff < 60:
        return _("şimdi")
    
    # Dakika önce (1 saatten az)
    if seconds_diff < 3600:
        minutes = int(seconds_diff // 60)
        return _("{} dk").format(minutes)
    
    # Saat önce (1 günden az)
    if seconds_diff < 86400:
        hours = int(seconds_diff // 3600)
        return _("{} sa").format(hours)
    # Dün
    yesterday = now - timedelta(days=1)
    if value.date() == yesterday.date():
        return _("Dün")
    
    # Bu hafta içinde (7 günden az)
    if seconds_diff < 604800:
        # Haftanın günü isimlerini türkçe olarak tanımlayalım
        days_tr = [_("Pazartesi"), _("Salı"), _("Çarşamba"), 
                  _("Perşembe"), _("Cuma"), _("Cumartesi"), _("Pazar")]
        return days_tr[value.weekday()]
    
    # Bir aydan az
    if diff.days < 30:
        weeks = diff.days // 7
        return _("{} hf").format(weeks)
    
    # Bir yıldan az
    if diff.days < 365:
        months = diff.days // 30
        return _("{} ay").format(months)
    
    # Bir yıldan fazla
    years = diff.days // 365
    return _("{} y").format(years)

@register.filter
def format_datetime(value, format_string=None):
    """
    Bir datetime nesnesini özel bir formata dönüştürür.
    Eğer format_string belirtilmezse, varsayılan olarak 'd F Y, H:i' kullanılır (örn. "10 Nisan 2025, 18:03").
    
    Kullanım: {{ post.created_at|format_datetime }} veya {{ post.created_at|format_datetime:"d F Y" }}
    """
    if not value:
        return ""
    
    if format_string is None:
        format_string = "d F Y, H:i"
    
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return value
    
    # Türkçe ay isimleri
    months_tr = {
        "January": "Ocak", "February": "Şubat", "March": "Mart", "April": "Nisan",
        "May": "Mayıs", "June": "Haziran", "July": "Temmuz", "August": "Ağustos",
        "September": "Eylül", "October": "Ekim", "November": "Kasım", "December": "Aralık"
    }
    
    # Django'nun date filter'ını kullanarak tarih formatını oluştur
    formatted_date = value.strftime(format_string)
    
    # Ay isimlerini Türkçe'ye çevir
    for eng, tr in months_tr.items():
        formatted_date = formatted_date.replace(eng, tr)
    
    return formatted_date

@register.inclusion_tag('components/relative_time.html')
def display_time(timestamp, show_full_date=False, css_class=''):
    """
    Göreceli zamanı gösteren bir bileşen renderlama.
    
    Args:
        timestamp: datetime nesnesi veya ISO formatında tarih-saat stringi
        show_full_date: Tam tarihi tooltip olarak gösterip göstermeme
        css_class: Bileşene uygulanacak ek CSS sınıfları
    
    Kullanım:
    {% load time_tags %}
    {% display_time post.created_at %}
    {% display_time comment.created_at show_full_date=True css_class="small-text" %}
    """
    
    # String ise datetime'a çevir
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    relative = relative_time(timestamp)
    full_date = format_datetime(timestamp) if show_full_date else None
    iso_date = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
    
    return {
        'timestamp': timestamp,
        'relative_time': relative,
        'full_date': full_date,
        'iso_date': iso_date,
        'css_class': css_class,
        'show_full_date': show_full_date
    }
