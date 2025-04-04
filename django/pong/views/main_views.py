# main_views.py
from django.shortcuts import render, redirect, get_object_or_404
from pong.models import CustomUser as User
from pong.models import SimpleMatch
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login as django_login, logout
from urllib.parse import urlparse
import json
import pyotp
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
import os
from django.core.files.base import ContentFile

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_a2f(request):
    user = request.user
    is_a2f_enabled = request.data.get("is_a2f_enabled")

    if is_a2f_enabled is None:
        return JsonResponse({"success": False, "error": "Paramètre 'is_a2f_enabled' manquant."}, status=400)

    user.is_a2f_enabled = is_a2f_enabled
    user.save()

    return JsonResponse({"success": True, "message": "Paramètres de l'A2F mis à jour."})

class OTPStore:
    _store = {}

    @classmethod
    def save_otp(cls, user_id, otp_secret):
        cls._store[user_id] = {
            'secret': otp_secret,
            'created': datetime.now()
        }

    @classmethod
    def get_otp(cls, user_id):
        return cls._store.get(user_id)

    @classmethod
    def remove_otp(cls, user_id):
        if user_id in cls._store:
            del cls._store[user_id]

def generate_and_send_otp(user):
    try:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, interval=300)
        otp_code = totp.now()

        subject = 'Code de vérification pour votre connexion'
        message = f'Votre code de vérification est : {otp_code}\nCe code est valide pendant 5 minutes.'
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [user.email]

        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False
        )

        OTPStore.save_otp(user.id, secret)
        return True

    except Exception as e:
        print(f"Erreur détaillée lors de l'envoi de l'email: {str(e)}")
        return False

def verify_otp(user_id, otp_code):
    otp_data = OTPStore.get_otp(user_id)
    if not otp_data:
        return False

    secret = otp_data['secret']
    created = otp_data['created']

    if datetime.now() - created > timedelta(minutes=5):
        OTPStore.remove_otp(user_id)
        return False

    totp = pyotp.TOTP(secret, interval=300)
    is_valid = totp.verify(otp_code)
    if is_valid:
        OTPStore.remove_otp(user_id)
    return is_valid

def safe_next_url(next_url: str):
    parsed = urlparse(next_url)
    return parsed.path or "/"


def login_view(request):
    if request.method == "GET":
        raw_next = request.GET.get("next", "/")
        next_url = safe_next_url(raw_next)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(request, "login.html", {"next_url": next_url})
        return render(request, "base.html", {
            "initial_fragment": "login.html",
            "next_url": next_url
        })

    elif request.method == "POST":
        content_type = request.headers.get('Content-Type', '')

        if 'application/json' not in content_type:
            return JsonResponse({
                "success": False,
                "error": "Type de contenu non supporté"
            }, status=400)

        try:
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")
            otp_code = data.get("otp_code")
            raw_next = data.get("next", "/")
            next_url = safe_next_url(raw_next)
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Données JSON invalides"
            }, status=400)

        if not username or not password:
            return JsonResponse({
                "success": False,
                "error": "Nom d'utilisateur et mot de passe requis"
            }, status=400)

        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({
                "success": False,
                "error": "Identifiants incorrects"
            }, status=401)

        if not user.email:
            return JsonResponse({
                "success": False,
                "error": "Cet utilisateur n'a pas d'adresse email configurée"
            }, status=400)

        if not user.is_a2f_enabled:
            django_login(request, user)
            refresh = RefreshToken.for_user(user)

            response = JsonResponse({
                "success": True,
                "message": "Connexion réussie !",
                "redirect": next_url
            })

            response.set_cookie(
                "access_token",
                str(refresh.access_token),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=3600
            )
            response.set_cookie(
                "refresh_token",
                str(refresh),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=7 * 24 * 3600
            )
            return response

        if not otp_code:
            if generate_and_send_otp(user):
                return JsonResponse({
                    "success": True,
                    "requires_otp": True,
                    "message": f"Code de vérification envoyé à {user.email}"
                })
            else:
                return JsonResponse({
                    "success": False,
                    "error": "Erreur lors de l'envoi du code de vérification. Vérifiez la configuration email."
                }, status=500)

        if verify_otp(user.id, otp_code):
            django_login(request, user)
            refresh = RefreshToken.for_user(user)

            response = JsonResponse({
                "success": True,
                "message": "Connexion réussie !",
                "redirect": next_url
            })

            response.set_cookie(
                "access_token",
                str(refresh.access_token),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=3600
            )
            response.set_cookie(
                "refresh_token",
                str(refresh),
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=7 * 24 * 3600
            )
            return response
        else:
            return JsonResponse({
                "success": False,
                "error": "Code de vérification incorrect ou expiré"
            }, status=401)

    return JsonResponse({
        "success": False,
        "error": "Méthode non autorisée"
    }, status=405)


def home_view(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'home.html')
    return render(request, 'base.html', { "initial_fragment": "home.html" })


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")
        avatar = request.FILES.get("avatar")

        if not username or not password or not email:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"error": "Tous les champs sont obligatoires."}, status=400)
            context = {
                "error_message": "Tous les champs sont obligatoires.",
                "initial_fragment": "register.html"
            }
            return render(request, "base.html", context)

        if User.objects.filter(username=username).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"error": "Nom d'utilisateur déjà pris."}, status=400)
            context = {
                "error_message": "Nom d'utilisateur déjà pris.",
                "initial_fragment": "register.html"
            }
            return render(request, "base.html", context)

        avatar_name = None
        if avatar:
            fs = FileSystemStorage(location='media/avatars/')
            avatar_name = fs.save(f"{username}.jpg", avatar)

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            avatar_url = '/media/avatars/' + avatar_name if avatar_name else '/media/avatars/default.jpg'
        )

        refresh = RefreshToken.for_user(user)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                "success": True,
                "message": "Inscription réussie !",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                },
                "redirect": "/"
            }, status=201)

        return redirect('/')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'register.html')

    context = {"initial_fragment": "register.html"}
    return render(request, "base.html", context)

def game_view(request):
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden()
        else:
            return redirect('/')

    mode = request.GET.get('mode', 'solo')

    context = {'mode': mode}
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "pong.html", context)
    else:
        return render(request, "base.html", {
            "initial_fragment": "pong.html",
            "mode": mode
        })

def account_view(request, username=None):
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden("Vous devez être connecté pour voir ce profil.")
        else:
            return redirect('/')

    if username is None or username == request.user.username:
        viewed_user = request.user
    else:
        viewed_user = get_object_or_404(User, username=username)

    is_friend = request.user.friends.filter(id=viewed_user.id).exists()

    if request.headers.get("Accept") == "application/json":
        friend_list = []
        if viewed_user == request.user or is_friend:
            friend_list = [
                {
                    "username": friend.username,
                    "online_status": friend.online_status,
                    "avatar_url": friend.avatar_url,
                }
                for friend in viewed_user.friends.all()
            ]
        return JsonResponse({
            "username": viewed_user.username,
            "online_status": viewed_user.online_status,
            "is_friend": is_friend,
            "friend_list": friend_list,
        })

    context = {
        "viewed_user": viewed_user,
        "is_friend": is_friend,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('fragment') == '1':
        return render(request, 'account.html', context)  # Fragment AJAX

    return render(request, 'base.html', {"initial_fragment": "account.html", "viewed_user": viewed_user})


def chat_view(request):
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden()
        else:
            return redirect('/')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "chat.html")
    return redirect('/')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    user = request.user
    return Response({
        "username": user.username,
        "avatar_url": user.avatar_url
    })

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return JsonResponse({"error": "Refresh token manquant."}, status=401)

        request.data["refresh"] = refresh_token
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get("access")
            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=3600
            )

        return response

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Données sécurisées accessibles uniquement aux utilisateurs authentifiés."})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)  # Supp la session Django
    response = JsonResponse({"success": True, "message": "Déconnexion réussie !"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

def get_player_matches(request, username):
    matches = SimpleMatch.objects.filter(player1__username=username) | SimpleMatch.objects.filter(player2__username=username)
    matches_data = []
    user = User.objects.get(username=username)
    global_stats = []
    global_stats.append({
        'total_matches': user.match_played,
        'total_wins': user.wins,
        'total_loses': user.loses,
    })
    for match in matches:
        match_data = {
            'id': match.id,
            'player1_username': match.player1.username,
            'player2_username': match.player2.username if match.player2 else None,
            'game_id': match.game_id,
            'winner': match.winner if match.winner else None,
            'created_at': match.created_at,
        }
        matches_data.append(match_data)
    data = {
        'stats': global_stats,
        'matches': matches_data,
    }
    return JsonResponse(data, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_avatar_view(request):
    if 'avatar' not in request.FILES:
        return JsonResponse({"success": False, "error": "No image file provided"}, status=400)

    avatar_file = request.FILES['avatar']
    allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    if avatar_file.content_type not in allowed_types:
        return JsonResponse({"success": False, "error": "Invalid file type. Only JPEG, PNG, and GIF are allowed."}, status=400)

    if avatar_file.size > 5 * 1024 * 1024:
        return JsonResponse({"success": False, "error": "File too large. Maximum size is 5MB."}, status=400)

    try:
        user = request.user

        file_ext = os.path.splitext(avatar_file.name)[1].lower() or '.jpg'
        avatar_filename = f"{user.username}{file_ext}"

        fs = FileSystemStorage(location='media/avatars/')

        if fs.exists(avatar_filename):
            fs.delete(avatar_filename)

        fs.save(avatar_filename, avatar_file)

        user.avatar_url = f"/media/avatars/{avatar_filename}"
        user.save()

        return JsonResponse({
            "success": True,
            "message": "Avatar updated successfully",
            "avatar_url": user.avatar_url
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Failed to update avatar: {str(e)}"
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    user = request.user
    if user.is_42_user:
        return JsonResponse({"success": False, "error": "42 users cannot change their password."}, status=403)
    current_password = request.POST.get('current_password')
    new_password = request.POST.get('new_password')
    if not current_password or not new_password:
        return JsonResponse({"success": False, "error": "Both current and new passwords are required."}, status=400)
    if len(new_password) < 8:
        return JsonResponse({"success": False, "error": "New password must be at least 8 characters long."}, status=400)
    if not authenticate(username=user.username, password=current_password):
        return JsonResponse({"success": False, "error": "Current password is incorrect."}, status=401)
    try:
        user.password = make_password(new_password)
        user.save()
        return JsonResponse({"success": True, "message": "Password changed successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Failed to change password: {str(e)}"}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_username_view(request):
    user = request.user
    new_username = request.data.get('new_username')
    if not new_username:
        return JsonResponse({"success": False, "error": "New username is required."}, status=400)
    if User.objects.filter(username=new_username).exclude(id=user.id).exists():
        return JsonResponse({"success": False, "error": "This username is already taken."}, status=400)
    try:
        user.username = new_username
        user.save()
        return JsonResponse({"success": True, "message": "Username changed successfully.", "username": new_username})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Failed to change username: {str(e)}"}, status=500)

