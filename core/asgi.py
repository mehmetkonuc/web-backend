import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()  # ÖNEMLİ: Django'yu settings ile yükleyin

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Django ASGI uygulaması
django_asgi_app = get_asgi_application()

# WebSocket yönlendirme modülünü import et
from apps.chat import routing as chat_routing
from apps.notifications import routing as notification_routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            chat_routing.websocket_urlpatterns +
            notification_routing.websocket_urlpatterns
        )
    ),
})