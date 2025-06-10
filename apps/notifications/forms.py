from django import forms
from .models import NotificationType

class NotificationPreferencesForm(forms.Form):
    """Kullanıcıların bildirim tercihlerini ayarlamak için form"""
    
    def __init__(self, *args, **kwargs):
        # Kullanıcı modelini al
        user = kwargs.pop('user', None)
        super(NotificationPreferencesForm, self).__init__(*args, **kwargs)
        
        # Tüm bildirim türlerini dinamik olarak forma ekle
        notification_types = NotificationType.objects.all()
        
        for notification_type in notification_types:
            field_name = f"notification_{notification_type.code}"
            self.fields[field_name] = forms.BooleanField(
                label=notification_type.name,
                help_text=notification_type.description,
                required=False,
                initial=True  # Varsayılan olarak tüm bildirimler açık
            )
