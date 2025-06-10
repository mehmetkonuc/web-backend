from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver
from apps.notifications.services import NotificationService

class Like(models.Model):
    """Generic like model that can be used for any object"""
    user = models.ForeignKey(User, related_name='likes', on_delete=models.CASCADE)
    
    # Generic relation fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
        unique_together = ['user', 'content_type', 'object_id']
    
    def __str__(self):
        return f"{self.user.username} likes {self.content_object}"
    
    def save(self, *args, **kwargs):
        # Check if this is a new like (not an update)
        is_new = self.pk is None
        
        # Save the like
        super().save(*args, **kwargs)
        
        # Send notification only if this is a new like and not from the content owner
        if is_new:
            # NotificationService kullanarak bildirim gönder
            NotificationService.create_like_notification(
                user=self.user,
                like_obj=self
            )


@receiver(post_delete, sender=Like)
def delete_like_notification(sender, instance, **kwargs):
    """
    Signal handler to delete notification when a like is deleted
    """
    # NotificationService kullanarak bildirim sil
    NotificationService.delete_notification_by_object(instance)
