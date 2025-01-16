from django.urls import re_path
from pong import consumers
from pong.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/game/(?P<game_id>\w+)/$', consumers.PongConsumer.as_asgi()),
    re_path(r'ws/chat/$', ChatConsumer.as_asgi()),
]
