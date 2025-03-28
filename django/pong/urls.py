from django.contrib import admin
from django.urls import path, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenBlacklistView
from .views.main_views import register_view
from .logic.game import *
from django.conf import settings
from django.conf.urls.static import static
from pong.views.main_views import home_view, game_view, update_a2f, account_view, chat_view, get_user_info, login_view, CookieTokenRefreshView, logout_view, get_player_matches, update_avatar_view, change_password_view, get_player_matches, change_username_view
from pong.views import oauth42_views
from pong.views.oauth42_views import auth_42_callback, auth_42_login
from pong.views.friend_views import (
    send_friend_request,
    accept_friend_request,
    cancel_friend_request,
    decline_friend_request,
    get_friendship_status,
    received_friend_requests,
    delete_friend,
    delete_friend,
)
from .views.tournament_views import (
    create_tournament_view,
    get_tournament_detail_view,
    start_match_game_view,
    list_tournaments_view,
    report_match_result_view,
    choose_tournament_alias_view,
    get_blockchain_tournament,
    blockchain_tournaments_view,
)

INVITATIONS = {}

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({"message": "Vous êtes authentifié !"})

urlpatterns = [
    path('', oauth42_views.root_view, name='root'),
    path('register/', register_view, name='register'),
    path('game/', game_view, name='game'),
    path('chat/', chat_view, name='chat'),
    path('account/', account_view, name='account'),
    path('account/<str:username>/', account_view, name='account_other'),
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/revoke/', TokenBlacklistView.as_view(), name='token_revoke'),
    path('api/user_info/', get_user_info, name='get_user_info'),
    path('login/', login_view, name='login'),
    path("api/logout/", logout_view, name="logout"),
    path('api/account/update_a2f/', update_a2f, name='update_a2f'),
    path('tournaments/create/', create_tournament_view, name='create_tournament'),
    path('tournaments/<int:tournament_id>/', get_tournament_detail_view, name='tournament_detail_json'),
    path('tournaments/match/<int:match_id>/start_game/', start_match_game_view, name='start_match_game'),
    path('tournaments/list/', list_tournaments_view, name='list_tournaments'),
    path('tournaments/match/<int:match_id>/report_result/', report_match_result_view, name='report_match_result'),
    path('tournaments/<int:tournament_id>/choose_alias/', choose_tournament_alias_view, name='choose_tournament_alias'),
    path('api/friends/send/<str:username>/', send_friend_request, name="send_friend_request"),
    path('api/friends/accept/<int:request_id>/', accept_friend_request, name="accept_friend_request"),
    path('api/friends/decline/<int:request_id>/', decline_friend_request, name="decline_friend_request"),
    path('api/friends/cancel/<int:request_id>/', cancel_friend_request, name="cancel_friend_request"),
    path('api/friends/delete/<str:username>/', delete_friend, name="delete_friend"),
    path('api/friends/status/<str:username>/', get_friendship_status, name="get_friendship_status"),
    path('api/friends/received/', received_friend_requests, name='received_friend_requests'),
    # OAuth42 routes
    path('auth/42/', auth_42_login, name='auth_42_login'),
    path('auth/42/callback', auth_42_callback, name='auth_42_callback'),
    path('api/matches/<str:username>/', get_player_matches, name='get_player_matches'),
    path('update-avatar/', update_avatar_view, name='update_avatar'),
    path('change-password/', change_password_view, name='change_password'),
    path('change-username/', change_username_view, name='change_username'),
    re_path(r'^api/blockchain/tournament/(?P<tournament_id>-?\d+)/$', get_blockchain_tournament, name='blockchain_tournament'),
    path('tournaments/blockchain/', blockchain_tournaments_view, name='blockchain_tournaments'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


