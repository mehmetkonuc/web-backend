# Generated by Django 5.2 on 2025-04-09 23:27

import apps.profiles.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dataset', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to=apps.profiles.models.avatar_upload_path, verbose_name='Profil Fotoğrafı')),
                ('is_private', models.BooleanField(default=False, verbose_name='Gizli Profil')),
                ('is_verified', models.BooleanField(default=False, verbose_name='Doğrulanmış Hesap')),
                ('bio', models.TextField(blank=True, max_length=400, null=True, verbose_name='Hakkında')),
                ('blocked', models.ManyToManyField(blank=True, related_name='blocked_by', to='profiles.profile', verbose_name='Engellenenler')),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dataset.department', verbose_name='Bölüm')),
                ('following', models.ManyToManyField(blank=True, related_name='followers', to='profiles.profile', verbose_name='Takip Edilenler')),
                ('graduation_status', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dataset.graduationstatus', verbose_name='Mezuniyet Durumu')),
                ('university', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dataset.university', verbose_name='Üniversite')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='Kullanıcı')),
            ],
            options={
                'verbose_name': 'Kullanıcı Profili',
                'verbose_name_plural': 'Kullanıcı Profilleri',
            },
        ),
        migrations.CreateModel(
            name='FollowRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Beklemede'), ('accepted', 'Kabul Edildi'), ('rejected', 'Reddedildi')], default='pending', max_length=10, verbose_name='Durum')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Zamanı')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Güncellenme Zamanı')),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_follow_requests', to='profiles.profile', verbose_name='İsteği Gönderen')),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_follow_requests', to='profiles.profile', verbose_name='İsteği Alan')),
            ],
            options={
                'verbose_name': 'Takip İsteği',
                'verbose_name_plural': 'Takip İstekleri',
                'unique_together': {('from_user', 'to_user')},
            },
        ),
    ]
