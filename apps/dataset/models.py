from django.db import models

# Create your models here.
class University(models.Model):
    name = models.CharField(max_length=255, verbose_name="Üniversite Adı")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Üniversite"
        verbose_name_plural = "Üniversiteler"
        ordering = ['name']


class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name="Bölüm Adı")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Bölüm"
        verbose_name_plural = "Bölümler"
        ordering = ['name']


class GraduationStatus(models.Model):  
    name = models.CharField(max_length=255, verbose_name="Bölüm Adı")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Mezuniyet Durumu"
        verbose_name_plural = "Mezuniyet Durumları"
