# core/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import apps.notifications.routing
import apps.chat.routing  # Chat modülünün routing dosyasını içe aktarın

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# HTTP uygulamasını önce içe aktarın
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                apps.notifications.routing.websocket_urlpatterns +
                apps.chat.routing.websocket_urlpatterns  # Chat WebSocket URL'lerini ekleyin
            )
        )
    ),
})