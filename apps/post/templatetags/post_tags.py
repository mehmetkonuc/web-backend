from django import template
import re
from django.utils.safestring import mark_safe
from django.urls import reverse

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Sözlükte bir anahtarla ilişkili değeri alır.
    Örnek: {{ trending_posts|get_item:hashtag.id }}
    """
    if not dictionary or not key:
        return None
    
    return dictionary.get(str(key)) or dictionary.get(key)

@register.filter
def linkify_hashtags(text):
    """
    Metin içerisindeki hashtag'leri (#örnek gibi) bulur ve onları 
    ilgili hashtag sayfasına yönlendiren link haline getirir.
    Örnek: {{ post.content|linkify_hashtags|safe }}
    """
    pattern = r'#(\w+)'
    
    def replace_hashtag(match):
        hashtag = match.group(1)
        url = reverse('post:hashtag_posts', kwargs={'hashtag': hashtag.lower()})
        return f'<a href="{url}" class="hashtag-link text-primary">#<span class="fw-bold">{hashtag}</span></a>'
    
    linked_text = re.sub(pattern, replace_hashtag, text)
    return mark_safe(linked_text)

@register.filter
def map_posts_to_images(posts):
    """
    Extract all images from a list of posts.
    Returns a flat list of all PostImage objects.
    """
    all_images = []
    for post in posts:
        for image in post.images.all():
            all_images.append(image)
    return all_images