# Generated by Django 5.2 on 2025-04-11 20:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0004_alter_userpostfilter_posts_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='post',
            old_name='author',
            new_name='user',
        ),
    ]
