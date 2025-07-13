from django.db import models
from django.contrib.auth.models import User


class FCMToken(models.Model):
    """
    Kullanıcıların Firebase FCM Token'larını saklar
    """
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens')
    fcm_token = models.CharField(max_length=500, unique=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    device_info = models.JSONField(default=dict, blank=True)  # Platform version, device model vs.
    device_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fcm_tokens'
        verbose_name = 'FCM Token'
        verbose_name_plural = 'FCM Tokens'
        unique_together = ['user', 'platform']  # Her kullanıcı her platform için tek token
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['fcm_token']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.platform} - {self.fcm_token[:20]}..."


class NotificationLog(models.Model):
    """
    Gönderilen bildirimlerin loglarını tutar
    """
    STATUS_CHOICES = [
        ('success', 'Başarılı'),
        ('failed', 'Başarısız'),
        ('pending', 'Beklemede'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_logs')
    fcm_token = models.ForeignKey(FCMToken, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification_logs'
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.status}"
