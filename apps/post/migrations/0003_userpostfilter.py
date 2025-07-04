# Generated by Django 5.2 on 2025-04-10 12:32

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dataset', '0001_initial'),
        ('post', '0002_hashtag_post_hashtags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPostFilter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('posts_type', models.CharField(choices=[('all', 'Bütün Gönderiler'), ('following', 'Sadece Takip Ettiklerim')], default='all', max_length=10, verbose_name='Gönderi Tipi')),
                ('last_used', models.DateTimeField(auto_now=True, verbose_name='Son Kullanım Tarihi')),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dataset.department', verbose_name='Bölüm')),
                ('university', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dataset.university', verbose_name='Üniversite')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='post_filter', to=settings.AUTH_USER_MODEL, verbose_name='Kullanıcı')),
            ],
            options={
                'verbose_name': 'Kullanıcı Gönderi Filtresi',
                'verbose_name_plural': 'Kullanıcı Gönderi Filtreleri',
            },
        ),
    ]
