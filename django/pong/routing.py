from django.urls import re_path
from pong import consumers

websocket_urlpatterns = [
    re_path(r'ws/somepath/$', consumers.menuConsumer.as_asgi()),
]
