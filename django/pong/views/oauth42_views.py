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

from pong.models import CustomUser

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def auth_42_login(request):
    """
    Redirects the user to 42's OAuth authorization page.
    Uses the base URL (http://localhost:8000) as the redirect URI
    as required by 42's OAuth configuration.
    """
    redirect_uri = settings.OAUTH42['REDIRECT_URI']
    auth_url = f"{settings.OAUTH42['AUTH_URL']}?client_id={settings.OAUTH42['CLIENT_ID']}&redirect_uri={redirect_uri}&response_type=code"
    return redirect(auth_url)

@api_view(['GET'])
@permission_classes([AllowAny])
def auth_42_callback(request):
    """
    Handles the callback from 42's OAuth service.
    Exchanges the authorization code for an access token,
    retrieves user info, and creates or updates the user.
    
    This function is designed to work both as a direct endpoint 
    and when called from the root_view function for the base URL callback.
    """
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
    expires_in = token_info.get('expires_in', 7200)  # Default to 2 hours if not provided

    # Get user info using the access token
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

    # Get or create user
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
            # Update existing user
            user.access_token = access_token
            user.refresh_token = refresh_token
            user.token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            user.save()
        else:
            # Create new user - for new users, we'll try to get their avatar
            avatar_url = user_info.get('image', {}).get('link')
            avatar_image = None
            
            # Only try to download avatar if we have a valid URL
            if avatar_url:
                try:
                    # Validate URL format
                    parsed_url = urlparse(avatar_url)
                    if not parsed_url.scheme or not parsed_url.netloc:
                        raise ValueError("Invalid URL format")
                    
                    # Download the avatar image
                    avatar_response = requests.get(avatar_url, timeout=10)
                    avatar_response.raise_for_status()
                    
                    # Prepare the file path and content
                    avatar_filename = f"{username}.jpg"
                    avatar_content = ContentFile(avatar_response.content)
                    logger.info(f"Successfully downloaded avatar for user {username}")
                    
                except (requests.exceptions.RequestException, ValueError) as e:
                    # Log the error but continue with user creation
                    logger.warning(f"Failed to download avatar for user {username}: {str(e)}")
            # Create the user
            user = CustomUser.objects.create(
                username=username,
                email=email,
                intra_id=intra_id,
                is_42_user=True,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            )
            
            # Set the avatar if we successfully downloaded it
            if avatar_url and 'avatar_content' in locals():
                try:
                    # Save the avatar to the user's avatar field
                    # No need to include 'avatars/' as that's handled by the upload_to parameter of the ImageField
                    user.avatar.save(avatar_filename, avatar_content, save=True)
                    logger.info(f"Successfully saved avatar for user {username}")
                except Exception as e:
                    logger.error(f"Failed to save avatar to user record for {username}: {str(e)}")
    except Exception as e:
        error_msg = f"Failed to create or update user: {str(e)}"
        logger.error(error_msg)
        return Response(
            {"error": error_msg},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Log the user in to Django's session system
    django_login(request, user)
    
    # Generate JWT token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    # Create cookies
    response = HttpResponseRedirect('/')  # Redirect to home page instead of using undefined FRONTEND_URL
    response.set_cookie(
        'access_token',
        access_token,
        max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
        httponly=True,
        samesite='Lax',
        secure=settings.DEBUG is False
    )
    
    # Add refresh token cookie
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
    """
    Handle both the home page and OAuth callback at the root level.
    If there's a 'code' parameter in the request, handle it as an OAuth callback.
    Otherwise, redirect to the home view.
    
    This view is necessary because the 42 OAuth service only accepts 
    http://localhost:8000 as a valid redirect URI, not a more specific path.
    """
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if code or error:
        # If there's a code or error parameter, handle it as an OAuth callback
        # Pass request._request which is the original HttpRequest, not the DRF Request
        return auth_42_callback(request._request)
    else:
        # Otherwise, redirect to the home view
        from pong.views.main_views import home_view
        return home_view(request)

