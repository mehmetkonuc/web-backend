from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    # Bildirim listesi sayfası
    path("", views.notification_list, name="list"),
    
    # Bildirim detay sayfası
    path("<int:notification_id>/", views.notification_detail, name="detail"),
    
    # Okunma işlemleri
    path("<int:notification_id>/mark-read/", views.mark_as_read, name="mark_as_read"),
    path("mark-all-read/", views.mark_all_as_read, name="mark_all_as_read"),
    
    # AJAX istekleri için
    path("unread-count/", views.get_unread_count, name="unread_count"),
    path("dropdown/", views.notifications_dropdown, name="dropdown"),
]