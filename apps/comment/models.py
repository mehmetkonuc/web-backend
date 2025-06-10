from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import datetime
import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
from apps.notifications.services import NotificationService
from django.urls import reverse

def post_image_upload_path(instance, filename):
    """Upload path for post images organized by year/month"""
    now = datetime.now()
    path = os.path.join('comments', str(now.year), str(now.month).zfill(2))
    return os.path.join(path, filename)

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

class CommentImage(models.Model):
    """Model for images attached to posts, up to 4 per post"""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='images', verbose_name="Yorum")
    image = models.ImageField(upload_to=post_image_upload_path, verbose_name="Resim")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Sıralama")
    
    class Meta:
        verbose_name = "Yorum Resmi"
        verbose_name_plural = "Yorum Resimleri"
        ordering = ['order']
    
    def __str__(self):
        return f"Image {self.order+1} for post {self.comment.id}"


@receiver(post_delete, sender=CommentImage)
def delete_photo_file(sender, instance, **kwargs):
    if instance.image:
        if default_storage.exists(instance.image.name):
            default_storage.delete(instance.image.name)

@receiver(post_delete, sender=Comment)
def delete_comment_notification(sender, instance, **kwargs):
    """
    Signal handler to delete notification when a comment is deleted
    """
    # Yorumla ilgili bildirimleri NotificationService aracılığıyla sil
    NotificationService.delete_notification_by_object(instance)