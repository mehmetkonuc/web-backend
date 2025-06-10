# Göreceli Zaman Formatı Bileşeni

Bu bileşen, sosyal medya uygulamanızda tarih-saat değerlerini "şimdi", "5 dakika önce", "1 saat önce", "Dün", "Çarşamba", "1 ay önce" gibi göreceli zaman formatlarında göstermenizi sağlar.

## Özellikler

- Django template tag olarak kullanım
- Reusable component olarak kullanım (inclusion tag)
- Otomatik güncellenen JavaScript versiyonu
- Tooltip ile tam tarih gösterimi (isteğe bağlı)
- Özelleştirilebilir CSS sınıfları

## Kurulum

1. `time_tags.py` dosyası `apps/comment/templatetags/` klasörüne yerleştirilmiştir
2. `relative_time.html` şablonu `apps/comment/templates/components/` klasörüne yerleştirilmiştir
3. JavaScript dosyası `static/js/relative-time.js` klasörüne yerleştirilmiştir

## Kullanım

### 1. Template Tag Olarak Kullanım

Bu yöntem, sadece basit filtreleme istediğiniz durumlarda kullanışlıdır:

```html
{% load time_tags %}

<span>{{ post.created_at|relative_time }}</span>
```

### 2. Component Olarak Kullanım (Önerilen)

Bu yöntem, JavaScript güncelleme ve tooltip özellikleriyle birlikte kullanım için en iyi yöntemdir:

```html
{% load time_tags %}

{% display_time post.created_at %}

<!-- Tam tarih tooltip'i ile -->
{% display_time comment.created_at show_full_date=True %}

<!-- Özel CSS sınıfı ile -->
{% display_time message.sent_at css_class="small-text text-muted" %}
```

### 3. Tam Tarih Formatını Özelleştirme

Eğer `format_datetime` filtresiyle tam tarih formatını özelleştirmek isterseniz:

```html
{{ post.created_at|format_datetime:"d F Y, H:i" }}
```

### 4. JavaScript Güncellemeyi Aktifleştirme

Sayfanızın en altına aşağıdaki script etiketini ekleyin:

```html
{% load static %}
<script src="{% static 'js/relative-time.js' %}"></script>
```

## Örnek Kullanım Sayfaları

- `apps/comment/templates/examples/time_format_example.html`
- `apps/comment/templates/examples/time_format_example_updated.html`

## Uygulamada Kullanım

Bu bileşeni projenizin farklı kısımlarında kullanabilirsiniz:

### Post Listesi

```html
<div class="post-item">
  <div class="post-header">
    <div class="post-author">{{ post.author.username }}</div>
    {% display_time post.created_at show_full_date=True %}
  </div>
  <div class="post-content">{{ post.content }}</div>
</div>
```

### Mesajlaşma

```html
<div class="message-item">
  <div class="message-content">{{ message.content }}</div>
  {% display_time message.sent_at css_class="message-time" %}
</div>
```

### Yorumlar

```html
<div class="comment">
  <div class="comment-author">{{ comment.author.username }}</div>
  <div class="comment-content">{{ comment.content }}</div>
  {% display_time comment.created_at css_class="comment-time" %}
</div>
```

### Bildirimler

```html
<div class="notification-item">
  <div class="notification-content">{{ notification.message }}</div>
  {% display_time notification.created_at css_class="notification-time" %}
</div>
```
