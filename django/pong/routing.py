from django.urls import re_path
from pong import consumers

websocket_urlpatterns = [
	re_path(r'ws/matchmaking/$', consumers.LobbyConsumer.as_asgi()),
    re_path(r'^ws/game/(?P<game_id>[0-9a-f-]+)/$', consumers.PongConsumer.as_asgi()),
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'^ws/tournament/(?P<tournament_id>\d+)/$', consumers.TournamentConsumer.as_asgi()),
]
