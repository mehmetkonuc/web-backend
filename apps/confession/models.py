from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage
from apps.dataset.models import University
from apps.comment.models import Comment
from apps.like.models import Like
from apps.bookmark.models import Bookmark
from datetime import datetime
import os


def confession_image_upload_path(instance, filename):
    """Upload path for post images organized by date and post ID"""
    # Hibrit yaklaşım: Tarih bazında ana klasörleme + confession ID klasörü + dosyalar
    now = datetime.now()
    confession_id = instance.confession.id if hasattr(instance, 'confession') and instance.confession else 'temp'

    # Format: confessions/2025/07/15/100/confession_100_image.webp
    path = os.path.join(
        'confessions',
        str(now.year),
        str(now.month).zfill(2),
        str(now.day).zfill(2),
        str(confession_id),
        f'confession_{confession_id}_{filename}'
    )
    return path


class ConfessionCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Kategori Adı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    
    class Meta:
        verbose_name = "İtiraf Kategorisi"
        verbose_name_plural = "İtiraf Kategorileri"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),  # Kategori adına göre hızlı arama için
        ]

    def __str__(self):
        return self.name
    
    def get_confession_count(self):
        """Returns the number of confessions in this category"""
        return self.confessions.count()
    
    def get_active_confession_count(self):
        """Returns the number of active confessions in this category"""
        return self.confessions.filter(is_active=True).count()
    
    @classmethod
    def get_popular_categories(cls, limit=10):
        """Returns categories with most confessions"""
        from django.db.models import Count
        return cls.objects.annotate(
            confession_count=Count('confessions')
        ).order_by('-confession_count')[:limit]


class ConfessionImage(models.Model):
    """Model for images attached to confessions, up to 4 per confession with multiple sizes"""
    confession = models.ForeignKey('ConfessionModel', on_delete=models.CASCADE, related_name='images', verbose_name="İtiraf")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='confession_images', verbose_name="Yazar")
    
    # Original image (mobil taraftan gelen sıkıştırılmış resim)
    image = models.ImageField(upload_to=confession_image_upload_path, verbose_name="Orijinal Resim")
    
    # Multiple optimized sizes (backend tarafından oluşturulan)
    thumbnail = models.ImageField(upload_to=confession_image_upload_path, blank=True, null=True, verbose_name="Thumbnail (150x150)")
    medium = models.ImageField(upload_to=confession_image_upload_path, blank=True, null=True, verbose_name="Medium (600x600)")
    large = models.ImageField(upload_to=confession_image_upload_path, blank=True, null=True, verbose_name="Large (1200x1200)")
    
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
        verbose_name = "İtiraf Resmi"
        verbose_name_plural = "İtiraf Resimleri"
        ordering = ['order']
        indexes = [
            models.Index(fields=['hash']),  # Duplicate detection için
            models.Index(fields=['processed']),  # İşlenmemiş resimleri bulmak için
        ]
    
    def __str__(self):
        return f"Image {self.order+1} for confession {self.confession.pk}"
    
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
    
    @property
    def image_url(self):
        """Template'de kullanmak için medium boyut URL'i"""
        return self.get_best_image_url('medium')
    
    @property
    def large_image_url(self):
        """Template'de kullanmak için large boyut URL'i"""
        return self.get_best_image_url('large')
    
    @property
    def thumbnail_url(self):
        """Template'de kullanmak için thumbnail boyut URL'i"""
        return self.get_best_image_url('thumbnail')


class ConfessionModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='confessions', verbose_name="Yazar")
    content = models.TextField(verbose_name="İtiraf Metni")
    category = models.ForeignKey(ConfessionCategory, on_delete=models.CASCADE, related_name='confessions', verbose_name="Kategori")
    comments = GenericRelation(Comment)
    likes = GenericRelation(Like)
    bookmarks = GenericRelation(Bookmark)
    university = models.ForeignKey(University, on_delete=models.CASCADE, verbose_name="Üniversite")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    is_privacy = models.BooleanField(default=True, verbose_name="Gizlilik")

    class Meta:
        verbose_name = "İtiraf"
        verbose_name_plural = "İtiraflar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),  # Tarih bazlı sıralama için
            models.Index(fields=['category', 'created_at']),  # Kategoriye göre filtreleme için
            models.Index(fields=['university', 'created_at']),  # Üniversiteye göre filtreleme için
            models.Index(fields=['user', 'created_at']),  # Kullanıcı confesionları için
            models.Index(fields=['is_active', 'created_at']),  # Aktif confessionlar için
            models.Index(fields=['is_privacy', 'created_at']),  # Gizlilik durumuna göre filtreleme için
            models.Index(fields=['university', 'is_privacy', 'created_at']),  # Üniversite + gizlilik filtreleme için
        ]

    def __str__(self):
        return f"{self.content[:50]}... - {self.category.name}"
    
    def delete(self, *args, **kwargs):
        self.comments.all().delete()  # İlişkili yorumları sil
        self.likes.all().delete()  # İlişkili beğenileri sil
        self.bookmarks.all().delete()  # İlişkili yer imlerini sil
        super().delete(*args, **kwargs)  # Sonra itirafı sil
        
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('confession:confession_detail', kwargs={'pk': self.pk})
    
    def get_images(self):
        """Returns all images associated with this confession"""
        return self.images.all()
    
    @property
    def image_count(self):
        """Returns the number of images attached to this confession"""
        return self.images.count()
    
    def get_like_count(self):
        """Returns the number of likes this confession has"""
        return self.likes.count()
    
    def is_liked_by(self, user):
        """Checks if this confession is liked by the given user"""
        if not user or not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()
    
    def get_bookmark_count(self):
        """Returns the number of bookmarks this confession has"""
        return self.bookmarks.count()

    def is_bookmarked_by(self, user):
        """Checks if this confession is bookmarked by the given user"""
        if not user or not user.is_authenticated:
            return False
        return self.bookmarks.filter(user=user).exists()
    
    def get_comment_count(self):
        """Returns the number of comments this confession has"""
        return self.comments.count()
    
    def is_visible_to_user(self, user):
        """Checks if this confession is visible to the given user"""
        # Aktif confession'lar herkese görünür
        return self.is_active
    
    def is_anonymous(self):
        """Checks if this confession is anonymous (author identity hidden)"""
        return self.is_privacy
    
    def get_author_info(self):
        """Returns author information based on privacy setting"""
        if self.is_privacy:
            # Gizli confession - yazar bilgisi gizli
            return {
                'is_anonymous': True,
                'display_name': 'Anonim',
                'username': None,
                'avatar': None,
                'university': self.university.name if self.university else None,
            }
        else:
            # Açık confession - yazar bilgisi görünür
            return {
                'is_anonymous': False,
                'display_name': f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username,
                'username': self.user.username,
                'avatar': self.user.profile.avatar.url if hasattr(self.user, 'profile') and self.user.profile.avatar else None,
                'university': self.university.name if self.university else None,
            }
    
    @classmethod
    def get_public_confessions(cls, limit=None):
        """Returns all active confessions (all are public, privacy only affects author identity)"""
        queryset = cls.objects.filter(
            is_active=True
        ).select_related('user', 'category', 'university')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @classmethod
    def get_anonymous_confessions(cls, limit=None):
        """Returns confessions with hidden author identity"""
        queryset = cls.objects.filter(
            is_active=True,
            is_privacy=True
        ).select_related('user', 'category', 'university')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @classmethod
    def get_open_confessions(cls, limit=None):
        """Returns confessions with visible author identity"""
        queryset = cls.objects.filter(
            is_active=True,
            is_privacy=False
        ).select_related('user', 'category', 'university')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @classmethod
    def get_trending_confessions(cls, limit=10):
        """Returns confessions with most likes in the last 24 hours"""
        from django.utils import timezone
        from django.db.models import Count
        
        last_24h = timezone.now() - timezone.timedelta(hours=24)
        return cls.objects.filter(
            created_at__gte=last_24h,
            is_active=True
        ).annotate(
            like_count=Count('likes')
        ).order_by('-like_count')[:limit]
    
    @classmethod
    def get_confessions_by_university(cls, university, limit=None):
        """Returns confessions from a specific university"""
        queryset = cls.objects.filter(
            university=university,
            is_active=True
        ).select_related('user', 'category', 'university')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @classmethod
    def get_confessions_by_category(cls, category, limit=None):
        """Returns confessions from a specific category"""
        queryset = cls.objects.filter(
            category=category,
            is_active=True
        ).select_related('user', 'category', 'university')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset


class ConfessionFilter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='confession_filter', verbose_name="Kullanıcı")
    category = models.ForeignKey(ConfessionCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kategori")
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Üniversite")
    sort_by = models.CharField(max_length=255, blank=True, null=True)
    last_used = models.DateTimeField(auto_now=True, verbose_name="Son Kullanım Tarihi")
    
    class Meta:
        verbose_name = "Kullanıcı İtiraf Filtresi"
        verbose_name_plural = "Kullanıcı İtiraf Filtreleri"

    def __str__(self):
        return f"{self.user.username}'s Confession Filter"


@receiver(post_delete, sender=ConfessionImage)
def delete_confession_image_files(sender, instance, **kwargs):
    """Confession resmi silindiğinde tüm boyutları sil"""
    for field_name in ['image', 'thumbnail', 'medium', 'large']:
        field = getattr(instance, field_name)
        if field and default_storage.exists(field.name):
            default_storage.delete(field.name)


@receiver(post_save, sender=ConfessionImage)
def process_confession_image(sender, instance, created, **kwargs):
    """
    Confession resmi kaydedildiğinde otomatik olarak işle
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
                    context='confession'
                )
                
                # Save processed images to model fields
                from datetime import datetime
                now = datetime.now()
                date_path = f'confessions/{now.year}/{now.month:02d}/{now.day:02d}/{instance.confession.pk}/'
                
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
            logger.error(f"Confession image processing failed: {e}")
            # İşleme başarısız olursa orijinal resmi kullan