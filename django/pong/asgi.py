import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pong.settings')
django.setup()  # <-- Make sure to call this BEFORE importing any code that needs Django

import pong.routing  # This import loads your websocket_urlpatterns, consumers, etc.

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(pong.routing.websocket_urlpatterns)
    ),
})