from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
import os
from datetime import datetime
import re
from django.utils import timezone
from apps.dataset.models import University, Department
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage
from django.contrib.contenttypes.models import ContentType

def post_image_upload_path(instance, filename):
    """Upload path for post images organized by date and post ID"""
    # Hibrit yaklaşım: Tarih bazında ana klasörleme + post ID klasörü + dosyalar
    now = datetime.now()
    post_id = instance.post.id if hasattr(instance, 'post') and instance.post else 'temp'
    
    # Format: posts/2025/07/15/100/post_100_image.webp
    path = os.path.join(
        'posts',
        str(now.year),
        str(now.month).zfill(2),
        str(now.day).zfill(2),
        str(post_id),
        f'post_{post_id}_{filename}'
    )
    return path

class Hashtag(models.Model):
    """Model for hashtags in posts"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Hashtag")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    
    class Meta:
        verbose_name = "Hashtag"
        verbose_name_plural = "Hashtagler"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.name}"
    
    def get_absolute_url(self):
        return reverse('post:hashtag_posts', kwargs={'hashtag': self.name})
    
    @property
    def post_count(self):
        """Returns the number of posts using this hashtag"""
        return self.posts.count()
    
    @property
    def post_count_last_24h(self):
        """Returns the number of posts using this hashtag in the last 24 hours"""
        last_24h = timezone.now() - timezone.timedelta(hours=24)
        return self.posts.filter(created_at__gte=last_24h).count()
    
    @classmethod
    def get_trending_hashtags(cls, limit=10):
        """Returns trending hashtags based on usage in the last 24 hours"""
        last_24h = timezone.now() - timezone.timedelta(hours=24)
        trending = cls.objects.filter(posts__created_at__gte=last_24h) \
                    .annotate(count=models.Count('posts')) \
                    .order_by('-count')[:limit]
        return trending

class Post(models.Model):
    """Model for user posts similar to Twitter"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name="Yazar")
    content = models.TextField(max_length=280, verbose_name="İçerik")  # Twitter-style 280 character limit
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")
    hashtags = models.ManyToManyField(Hashtag, related_name='posts', blank=True, verbose_name="Hashtagler")
    
    class Meta:
        verbose_name = "Gönderi"
        verbose_name_plural = "Gönderiler"
        ordering = ['-created_at']
    
    def __str__(self):
        # return f"{self.user.username}: {self.content[:50]}..."
        return f"Gönderi: {self.content[:60]}..."
    
    def get_absolute_url(self):
        return reverse('post:post_detail', kwargs={'pk': self.pk})
    
    def get_images(self):
        """Returns all images associated with this post"""
        return self.images.all()
    
    @property
    def image_count(self):
        """Returns the number of images attached to this post"""
        return self.images.count()
    
    def get_like_count(self):
        """Returns the number of likes this post has"""
        from apps.like.models import Like
        content_type = ContentType.objects.get_for_model(self)
        return Like.objects.filter(content_type=content_type, object_id=self.id).count()
    
    def is_liked_by(self, user):
        """Checks if this post is liked by the given user"""
        if not user or not user.is_authenticated:
            return False
        
        from apps.like.models import Like
        content_type = ContentType.objects.get_for_model(self)
        return Like.objects.filter(content_type=content_type, object_id=self.id, user=user).exists()
    
    def get_bookmark_count(self):
        """Returns the number of bookmarks this post has"""
        from apps.bookmark.models import Bookmark
        content_type = ContentType.objects.get_for_model(self)
        return Bookmark.objects.filter(content_type=content_type, object_id=self.id).count()

    def is_bookmarked_by(self, user):
        """Checks if this post is bookmarked by the given user"""
        if not user or not user.is_authenticated:
            return False
        
        from apps.bookmark.models import Bookmark
        content_type = ContentType.objects.get_for_model(self)
        return Bookmark.objects.filter(content_type=content_type, object_id=self.id, user=user).exists()
    
    def save(self, *args, **kwargs):
        """Override save to extract and save hashtags"""
        # First save the post
        super().save(*args, **kwargs)
        
        # Extract hashtags
        hashtags_in_content = re.findall(r'#(\w+)', self.content)
        
        # Clear existing hashtags
        self.hashtags.clear()
        
        # Add each hashtag
        for tag_name in hashtags_in_content:
            tag, created = Hashtag.objects.get_or_create(name=tag_name.lower())
            self.hashtags.add(tag)

class PostImage(models.Model):
    """Model for images attached to posts, up to 4 per post with multiple sizes"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images', verbose_name="Gönderi")
    
    # Original image (mobil taraftan gelen sıkıştırılmış resim)
    image = models.ImageField(upload_to=post_image_upload_path, verbose_name="Orijinal Resim")
    
    # Multiple optimized sizes (backend tarafından oluşturulan)
    thumbnail = models.ImageField(upload_to=post_image_upload_path, blank=True, null=True, verbose_name="Thumbnail (150x150)")
    medium = models.ImageField(upload_to=post_image_upload_path, blank=True, null=True, verbose_name="Medium (600x600)")
    large = models.ImageField(upload_to=post_image_upload_path, blank=True, null=True, verbose_name="Large (1200x1200)")
    
    # Metadata fields
    original_width = models.PositiveIntegerField(null=True, blank=True, verbose_name="Orijinal Genişlik")
    original_height = models.PositiveIntegerField(null=True, blank=True, verbose_name="Orijinal Yükseklik")
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name="Dosya Boyutu (bytes)")
    format = models.CharField(max_length=10, blank=True, null=True, verbose_name="Format (WEBP/JPEG)")
    hash = models.CharField(max_length=32, blank=True, null=True, verbose_name="MD5 Hash", help_text="Duplicate detection için")
    
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Sıralama")
    processed = models.BooleanField(default=False, verbose_name="İşlenmiş", help_text="Resim backend tarafından işlendi mi?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    
    class Meta:
        verbose_name = "Gönderi Resmi"
        verbose_name_plural = "Gönderi Resimleri"
        ordering = ['order']
        indexes = [
            models.Index(fields=['hash']),  # Duplicate detection için
            models.Index(fields=['processed']),  # İşlenmemiş resimleri bulmak için
        ]
    
    def __str__(self):
        return f"Image {self.order+1} for post {self.post.pk}"
    
    def get_best_image_url(self, size='medium'):
        """
        En uygun resim URL'ini döndür.
        
        Args:
            size: 'thumbnail', 'medium', 'large', 'original'
        """
        if size == 'thumbnail' and self.thumbnail:
            return self.thumbnail.url
        elif size == 'medium' and self.medium:
            return self.medium.url
        elif size == 'large' and self.large:
            return self.large.url
        elif size == 'original' and self.image:
            return self.image.url
        else:
            # Fallback: En yakın boyutu döndür
            if self.medium:
                return self.medium.url
            elif self.large:
                return self.large.url
            elif self.thumbnail:
                return self.thumbnail.url
            elif self.image:
                return self.image.url
            return None
    
    def get_all_sizes(self):
        """Mevcut tüm boyutları döndür"""
        sizes = {}
        if self.thumbnail:
            sizes['thumbnail'] = self.thumbnail.url
        if self.medium:
            sizes['medium'] = self.medium.url
        if self.large:
            sizes['large'] = self.large.url
        if self.image:
            sizes['original'] = self.image.url
        return sizes


@receiver(post_delete, sender=PostImage)
def delete_post_image_files(sender, instance, **kwargs):
    """Post resmi silindiğinde tüm boyutları sil"""
    for field_name in ['image', 'thumbnail', 'medium', 'large']:
        field = getattr(instance, field_name)
        if field and default_storage.exists(field.name):
            default_storage.delete(field.name)


@receiver(post_save, sender=PostImage)
def process_post_image(sender, instance, created, **kwargs):
    """
    Post resmi kaydedildiğinde otomatik olarak işle
    """
    if created and not instance.processed:
        # Asenkron işleme için Celery task'i çağırabilir
        # Şimdilik basit synchronous işleme yapıyoruz
        try:
            from apps.common.utils.image_processor import ImageProcessor
            from PIL import Image
            
            # Original image'ı aç
            if instance.image:
                processor = ImageProcessor()
                
                # Image bilgilerini kaydet
                with Image.open(instance.image.path) as img:
                    instance.original_width = img.width
                    instance.original_height = img.height
                    instance.file_size = instance.image.size
                    instance.format = 'WEBP' if processor.webp_supported else 'JPEG'
                
                # Process image
                processed_images = processor.process_image(
                    instance.image,
                    size_presets=['thumbnail', 'medium', 'large'],
                    context='post'
                )
                
                # Save processed images to model fields - same date-based path as original
                from datetime import datetime
                now = datetime.now()
                # Create same path structure as original: posts/2025/07/15/post_100/
                date_path = f'posts/{now.year}/{now.month:02d}/{now.day:02d}/{instance.post.pk}/'
                
                saved_files = processor.save_processed_images(
                    processed_images,
                    instance.image.name,
                    date_path
                )
                
                # Update model fields
                if 'thumbnail' in saved_files:
                    instance.thumbnail.name = saved_files['thumbnail']
                if 'medium' in saved_files:
                    instance.medium.name = saved_files['medium']
                if 'large' in saved_files:
                    instance.large.name = saved_files['large']
                
                instance.processed = True
                instance.save(update_fields=[
                    'thumbnail', 'medium', 'large', 'processed',
                    'original_width', 'original_height', 'file_size', 'format'
                ])
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Post image processing failed: {e}")
            # İşleme başarısız olursa orijinal resmi kullan


class UserPostFilter(models.Model):
    """Model to store user's post filter preferences"""
    POSTS_TYPE_CHOICES = [
        ('all', 'Bütün Gönderiler'),
        ('following', 'Sadece Takip Ettiklerim'),
        ('verified', 'Sadece Doğrulanmış Hesaplar'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='post_filter', verbose_name="Kullanıcı")
    posts_type = models.CharField(max_length=10, choices=POSTS_TYPE_CHOICES, default='all', verbose_name="Gönderi Tipi")
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Üniversite")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bölüm")
    last_used = models.DateTimeField(auto_now=True, verbose_name="Son Kullanım Tarihi")
    
    class Meta:
        verbose_name = "Kullanıcı Gönderi Filtresi"
        verbose_name_plural = "Kullanıcı Gönderi Filtreleri"
    
    def __str__(self):
        return f"{self.user.username}'s Post Filter"
