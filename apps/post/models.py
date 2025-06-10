from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
import os
from datetime import datetime
import re
from django.utils import timezone
from apps.dataset.models import University, Department
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
from django.contrib.contenttypes.models import ContentType

def post_image_upload_path(instance, filename):
    """Upload path for post images organized by year/month"""
    now = datetime.now()
    path = os.path.join('posts', str(now.year), str(now.month).zfill(2))
    return os.path.join(path, filename)

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
    """Model for images attached to posts, up to 4 per post"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images', verbose_name="Gönderi")
    image = models.ImageField(upload_to=post_image_upload_path, verbose_name="Resim")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Sıralama")
    
    class Meta:
        verbose_name = "Gönderi Resmi"
        verbose_name_plural = "Gönderi Resimleri"
        ordering = ['order']
    
    def __str__(self):
        return f"Image {self.order+1} for post {self.post.id}"


@receiver(post_delete, sender=PostImage)
def delete_photo_file(sender, instance, **kwargs):
    if instance.image:
        if default_storage.exists(instance.image.name):
            default_storage.delete(instance.image.name)


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
