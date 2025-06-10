from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.urls import reverse


class Bookmark(models.Model):
    """Generic bookmark model that can be used for any content object"""
    # User who bookmarked the content
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks', verbose_name="Kullanıcı")
    
    # Generic relation fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="İçerik Tipi")
    object_id = models.PositiveIntegerField(verbose_name="Nesne ID")
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Oluşturulma Zamanı")
    
    class Meta:
        verbose_name = "Yer İmi"
        verbose_name_plural = "Yer İmleri"
        ordering = ['-created_at']
        # Ensure a user can bookmark an object only once
        unique_together = ['user', 'content_type', 'object_id']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.content_object}"
    
    @classmethod
    def toggle_bookmark(cls, user, content_object):
        """
        Toggle bookmark status for an object - if bookmarked, remove it, otherwise add it
        Returns a tuple (is_bookmarked, created)
        """
        content_type = ContentType.objects.get_for_model(content_object)
        bookmark, created = cls.objects.get_or_create(
            user=user,
            content_type=content_type,
            object_id=content_object.id,
        )
        
        if not created:
            # If bookmark already exists, remove it
            bookmark.delete()
            return False, False
        
        return True, True
    
    @classmethod
    def is_bookmarked(cls, user, content_object):
        """Check if an object is bookmarked by a user"""
        if not user or not user.is_authenticated:
            return False
            
        content_type = ContentType.objects.get_for_model(content_object)
        return cls.objects.filter(
            user=user,
            content_type=content_type,
            object_id=content_object.id
        ).exists()
    
    def get_content_model_name(self):
        """Returns the model name of the bookmarked content"""
        return self.content_type.model
    
    def get_bookmark_url(self):
        """Get URL to the bookmarked item if available"""
        # Try to use get_absolute_url if the content object has it
        if hasattr(self.content_object, 'get_absolute_url'):
            return self.content_object.get_absolute_url()
        return None