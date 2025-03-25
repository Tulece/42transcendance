import os
import requests
import json
import datetime
import logging
from urllib.parse import urlparse
from pathlib import Path
from django.core.files.base import ContentFile
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import login as django_login
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.files.storage import FileSystemStorage


from pong.models import CustomUser

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def auth_42_login(request):
    redirect_uri = settings.OAUTH42['REDIRECT_URI']
    auth_url = f"{settings.OAUTH42['AUTH_URL']}?client_id={settings.OAUTH42['CLIENT_ID']}&redirect_uri={redirect_uri}&response_type=code"
    return redirect(auth_url)

@api_view(['GET'])
@permission_classes([AllowAny])
def auth_42_callback(request):
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error or not code:
        return Response(
            {"error": error or "No authorization code provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    token_data = {
        'grant_type': 'authorization_code',
        'client_id': settings.OAUTH42['CLIENT_ID'],
        'client_secret': settings.OAUTH42['CLIENT_SECRET'],
        'code': code,
        'redirect_uri': settings.OAUTH42['REDIRECT_URI']
    }

    try:
        token_response = requests.post(settings.OAUTH42['TOKEN_URL'], data=token_data)
        token_response.raise_for_status()
        token_info = token_response.json()
    except requests.exceptions.RequestException as e:
        return Response(
            {"error": f"Failed to obtain access token: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    access_token = token_info.get('access_token')
    refresh_token = token_info.get('refresh_token')
    expires_in = token_info.get('expires_in', 7200)

    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        user_response = requests.get(f"{settings.OAUTH42['API_URL']}/me", headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()
    except requests.exceptions.RequestException as e:
        return Response(
            {"error": f"Failed to retrieve user information: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    intra_id = user_info.get('id')
    email = user_info.get('email')
    username = user_info.get('login')
    
    if not intra_id or not email or not username:
        return Response(
            {"error": "Incomplete user information received from 42 API"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.filter(intra_id=intra_id).first()
        
        if user:
            user.access_token = access_token
            user.refresh_token = refresh_token
            user.token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            user.save()
        else:
            avatar_url = user_info.get('image', {}).get('link')
            avatar_image = None
            
            if avatar_url:
                try:
                    parsed_url = urlparse(avatar_url)
                    if not parsed_url.scheme or not parsed_url.netloc:
                        raise ValueError("Invalid URL format")
                    
                    avatar_response = requests.get(avatar_url, timeout=10)
                    avatar_response.raise_for_status()
                    
                    avatar_filename = f"{username}.jpg"
                    avatar_content = ContentFile(avatar_response.content)
                    logger.info(f"Successfully downloaded avatar for user {username}")
                    
                except (requests.exceptions.RequestException, ValueError) as e:
                    logger.warning(f"Failed to download avatar for user {username}: {str(e)}")
            user = CustomUser.objects.create(
                username=username,
                email=email,
                intra_id=intra_id,
                is_42_user=True,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            )
            
            if avatar_url and 'avatar_content' in locals():
                try:
                    fs = FileSystemStorage(location='media/avatars/')
                    avatar_filename = fs.save(f"{username}.jpg", avatar_content)
                    user.avatar_url = "/media/avatars/" + avatar_filename
                    user.save()
                    logger.info(f"Successfully saved avatar for user {username}")
                except Exception as e:
                    logger.error(f"Failed to save avatar to user record for {username}: {str(e)}")
            else:
                user.avatar_url = "/media/avatars/default.jpg"
                user.save()
    except Exception as e:
        error_msg = f"Failed to create or update user: {str(e)}"
        logger.error(error_msg)
        return Response(
            {"error": error_msg},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    django_login(request, user)
    
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    response = HttpResponseRedirect('/')
    response.set_cookie(
        'access_token',
        access_token,
        max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
        httponly=True,
        samesite='Lax',
        secure=settings.DEBUG is False
    )
    
    response.set_cookie(
        'refresh_token',
        str(refresh),
        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
        httponly=True,
        samesite='Lax',
        secure=settings.DEBUG is False
    )
    
    return response

@api_view(['GET'])
@permission_classes([AllowAny])
def root_view(request):
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if code or error:
        return auth_42_callback(request._request)
    else:
        from pong.views.main_views import home_view
        return home_view(request)

