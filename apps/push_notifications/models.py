from django.db import models
from django.contrib.auth.models import User


class PushToken(models.Model):
    """
    Kullanıcıların Expo Push Token'larını saklar
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='push_token')
    expo_token = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'push_tokens'
        verbose_name = 'Push Token'
        verbose_name_plural = 'Push Tokens'
    
    def __str__(self):
        return f"{self.user.username} - {self.expo_token[:20]}..."
