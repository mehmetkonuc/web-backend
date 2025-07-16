from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import datetime
import os
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage
from apps.notifications.services import NotificationService
from django.urls import reverse

def comment_image_upload_path(instance, filename):
    """Upload path for comment images organized by date and comment ID"""
    # Hibrit yaklaşım: Tarih bazında ana klasörleme + comment ID klasörü + dosyalar
    now = datetime.now()
    comment_id = instance.comment.id if hasattr(instance, 'comment') and instance.comment else 'temp'
    
    # Format: comments/2025/07/15/100/comment_100_image.webp
    path = os.path.join(
        'comments',
        str(now.year),
        str(now.month).zfill(2),
        str(now.day).zfill(2),
        str(comment_id),
        f'comment_{comment_id}_{filename}'
    )
    return path

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    
    # Generic relation fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        # return f"Comment by {self.user.username} on {self.content_object}"
        return f"Yorum: {self.body[:60]}"

    def get_absolute_url(self):
        return reverse('comment:comment_detail', kwargs={'comment_id': self.pk})

    def get_replies(self):
        """Get all active replies to this comment"""
        return self.replies.filter(is_active=True)
    
    @property
    def is_parent(self):
        """Check if this comment is a parent comment"""
        return self.parent is None

    def get_like_count(self):
        """Returns the number of likes this post has"""
        from apps.like.models import Like
        content_type = ContentType.objects.get_for_model(self)
        return Like.objects.filter(content_type=content_type, object_id=self.pk).count()
    
    def is_liked_by(self, user):
        """Checks if this post is liked by the given user"""
        if not user or not user.is_authenticated:
            return False
        
        from apps.like.models import Like
        content_type = ContentType.objects.get_for_model(self)
        return Like.objects.filter(content_type=content_type, object_id=self.pk, user=user).exists()

    def get_bookmark_count(self):
        """Returns the number of bookmarks this post has"""
        from apps.bookmark.models import Bookmark
        content_type = ContentType.objects.get_for_model(self)
        return Bookmark.objects.filter(content_type=content_type, object_id=self.pk).count()

    def is_bookmarked_by(self, user):
        """Checks if this post is bookmarked by the given user"""
        if not user or not user.is_authenticated:
            return False
        
        from apps.bookmark.models import Bookmark
        content_type = ContentType.objects.get_for_model(self)
        return Bookmark.objects.filter(content_type=content_type, object_id=self.pk, user=user).exists()

class CommentImage(models.Model):
    """Model for images attached to comments, up to 4 per comment with multiple sizes"""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='images', verbose_name="Yorum")
    
    # Original image (mobil taraftan gelen sıkıştırılmış resim)
    image = models.ImageField(upload_to=comment_image_upload_path, verbose_name="Orijinal Resim")
    
    # Multiple optimized sizes (backend tarafından oluşturulan) - Comment için daha küçük boyutlar
    thumbnail = models.ImageField(upload_to=comment_image_upload_path, blank=True, null=True, verbose_name="Thumbnail (150x150)")
    small = models.ImageField(upload_to=comment_image_upload_path, blank=True, null=True, verbose_name="Small (300x300)")
    
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
        verbose_name = "Yorum Resmi"
        verbose_name_plural = "Yorum Resimleri"
        ordering = ['order']
        indexes = [
            models.Index(fields=['hash']),  # Duplicate detection için
            models.Index(fields=['processed']),  # İşlenmemiş resimleri bulmak için
        ]
    
    def __str__(self):
        return f"Image {self.order+1} for comment {self.comment.pk}"
    
    def get_best_image_url(self, size='small'):
        """
        En uygun resim URL'ini döndür.
        
        Args:
            size: 'thumbnail', 'small', 'original'
        """
        if size == 'thumbnail' and self.thumbnail:
            return self.thumbnail.url
        elif size == 'small' and self.small:
            return self.small.url
        elif size == 'original' and self.image:
            return self.image.url
        else:
            # Fallback: En yakın boyutu döndür
            if self.small:
                return self.small.url
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
        if self.small:
            sizes['small'] = self.small.url
        if self.image:
            sizes['original'] = self.image.url
        return sizes


@receiver(post_delete, sender=CommentImage)
def delete_comment_image_files(sender, instance, **kwargs):
    """Comment resmi silindiğinde tüm boyutları sil"""
    for field_name in ['image', 'thumbnail', 'small']:
        field = getattr(instance, field_name)
        if field and default_storage.exists(field.name):
            default_storage.delete(field.name)


@receiver(post_save, sender=CommentImage)
def process_comment_image(sender, instance, created, **kwargs):
    """
    Comment resmi kaydedildiğinde otomatik olarak işle
    """
    if created and not instance.processed:
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
                
                # Process image (comment için küçük boyutlar)
                processed_images = processor.process_image(
                    instance.image,
                    size_presets=['thumbnail', 'small'],
                    context='comment'
                )
                
                # Save processed images to model fields - same date-based path as original
                from datetime import datetime
                now = datetime.now()
                # Create same path structure as original: comments/2025/07/15/100/
                date_path = f'comments/{now.year}/{now.month:02d}/{now.day:02d}/{instance.comment.pk}/'
                
                saved_files = processor.save_processed_images(
                    processed_images,
                    instance.image.name,
                    date_path
                )
                
                # Update model fields
                if 'thumbnail' in saved_files:
                    instance.thumbnail.name = saved_files['thumbnail']
                if 'small' in saved_files:
                    instance.small.name = saved_files['small']
                
                instance.processed = True
                instance.save(update_fields=[
                    'thumbnail', 'small', 'processed',
                    'original_width', 'original_height', 'file_size', 'format'
                ])
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Comment image processing failed: {e}")
            # İşleme başarısız olursa orijinal resmi kullan

@receiver(post_delete, sender=Comment)
def delete_comment_notification(sender, instance, **kwargs):
    """
    Signal handler to delete notification when a comment is deleted
    """
    # Yorumla ilgili bildirimleri NotificationService aracılığıyla sil
    NotificationService.delete_notification_by_object(instance)