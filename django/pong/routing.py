from django.urls import re_path
from pong import consumers  # À créer

websocket_urlpatterns = [
    re_path(r'ws/somepath/$', consumers.MyConsumer.as_asgi()),
]
