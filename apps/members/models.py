from django.db import models
from django.contrib.auth.models import User
from apps.dataset.models import University, Department, GraduationStatus

class UserMemberFilter(models.Model):
    """Model to store user's member filter preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_filter', verbose_name="Kullanıcı")
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Üniversite")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bölüm")
    graduation_status = models.ForeignKey(GraduationStatus, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mezuniyet Durumu")
    is_verified = models.BooleanField(null=True, blank=True, verbose_name="Doğrulanmış Hesap")
    last_used = models.DateTimeField(auto_now=True, verbose_name="Son Kullanım Tarihi")
    
    class Meta:
        verbose_name = "Kullanıcı Üye Filtresi"
        verbose_name_plural = "Kullanıcı Üye Filtreleri"
    
    def __str__(self):
        return f"{self.user.username}'in Üye Filtresi"
