"""
URL configuration for pong project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenBlacklistView
from .views.main_views import register_view
from .logic.game import *
from django.conf import settings
from django.conf.urls.static import static
from pong.views.main_views import home_view, game_view, update_a2f, account_view, chat_view, get_user_info, login_view, CookieTokenRefreshView, logout_view
from .views.tournament_views import (
    create_tournament_view,
    get_tournament_detail_view,
    start_match_game_view,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({"message": "Vous êtes authentifié !"})

urlpatterns = [
    path('', home_view, name='home'),
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
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


