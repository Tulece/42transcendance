# main_views.py
from django.shortcuts import render, redirect, get_object_or_404
from pong.models import CustomUser as User
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
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlparse
import json
import pyotp
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_a2f(request):
    """Met à jour le statut de l'A2F pour l'utilisateur authentifié"""
    user = request.user
    is_a2f_enabled = request.data.get("is_a2f_enabled")

    if is_a2f_enabled is None:
        return JsonResponse({"success": False, "error": "Paramètre 'is_a2f_enabled' manquant."}, status=400)

    user.is_a2f_enabled = is_a2f_enabled
    user.save()

    return JsonResponse({"success": True, "message": "Paramètres de l'A2F mis à jour."})

# Modèle pour stocker les codes OTP temporaires
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
    """Génère et envoie un code OTP par email"""
    try:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, interval=300)  # 5 minutes
        otp_code = totp.now()

        subject = 'Code de vérification pour votre connexion'
        message = f'Votre code de vérification est : {otp_code}\nCe code est valide pendant 5 minutes.'
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [user.email]

        print(f"Tentative d'envoi d'email à {user.email}")  # Debug, à enlever en production
        print(f"From: {from_email}")  # Debug, à enlever en production

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
    """Vérifie le code OTP"""
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
    """
    Ne garde que le path (ex: /game), ignore toute query string
    qui entraînerait un double-encodage (ex: ?csrfmiddlewaretoken=...).
    """
    parsed = urlparse(next_url)
    return parsed.path or "/"

@csrf_exempt
def login_view(request):
    """Vue de login avec A2F et gestion améliorée des erreurs"""
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

        # Vérifications initiales
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

        # Si la 2FA n'est pas activée, connecter l'utilisateur directement
        if not user.is_a2f_enabled:
            # Connecter l'utilisateur sans demander de code OTP
            django_login(request, user)
            refresh = RefreshToken.for_user(user)

            response = JsonResponse({
                "success": True,
                "message": "Connexion réussie !",
                "redirect": next_url
            })

            # Configuration des cookies JWT
            response.set_cookie(
                "access_token",
                str(refresh.access_token),
                httponly=True,
                secure=False,  # Mettre à True en production avec HTTPS
                samesite="Lax",
                max_age=3600
            )
            response.set_cookie(
                "refresh_token",
                str(refresh),
                httponly=True,
                secure=False,  # Mettre à True en production avec HTTPS
                samesite="Lax",
                max_age=7 * 24 * 3600
            )
            return response

        # Première étape : envoi de l'OTP si aucun code fourni
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

        # Vérification du code OTP fourni
        if verify_otp(user.id, otp_code):
            django_login(request, user)
            refresh = RefreshToken.for_user(user)

            response = JsonResponse({
                "success": True,
                "message": "Connexion réussie !",
                "redirect": next_url
            })

            # Configuration des cookies JWT
            response.set_cookie(
                "access_token",
                str(refresh.access_token),
                httponly=True,
                secure=False,  # Mettre à True en production avec HTTPS
                samesite="Lax",
                max_age=3600
            )
            response.set_cookie(
                "refresh_token",
                str(refresh),
                httponly=True,
                secure=False,  # Mettre à True en production avec HTTPS
                samesite="Lax",
                max_age=7 * 24 * 3600
            )
            return response
        else:
            return JsonResponse({
                "success": False,
                "error": "Code de vérification incorrect ou expiré"
            }, status=401)

    # Méthode non autorisée
    return JsonResponse({
        "success": False,
        "error": "Méthode non autorisée"
    }, status=405)


def home_view(request):
    """Gère la page d'accueil et les fragments AJAX pour la SPA."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'home.html')
    context = {"initial_fragment": "home.html"}
    return render(request, 'base.html', context)

def register_view(request):
    """Gère l'inscription d'un utilisateur"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")
        avatar = request.FILES.get("avatar")

        # Validation des données
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

        # Sauvegarde de l'avatar
        avatar_name = None
        if avatar:
            fs = FileSystemStorage(location='media/avatars/')
            avatar_name = fs.save(avatar.name, avatar)

        # Création de l'utilisateur
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )

        # Génération des tokens JWT (optionnel si on veut auto-connecter l’utilisateur après l’inscription)
        refresh = RefreshToken.for_user(user)

        # Réponse pour les requêtes AJAX (SPA)
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

        # Redirection normale pour les requêtes non AJAX
        return redirect('home')

    # Gestion des requêtes GET
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'register.html')

    context = {"initial_fragment": "register.html"}
    return render(request, "base.html", context)

def game_view(request):
    """Gère la vue pour le jeu Pong - nécessite authentification."""
    if not request.user.is_authenticated:
        # Si la requête est AJAX, renvoyer 403 ; sinon rediriger vers home
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden()
        else:
            return redirect('/')  # redirige vers la page d'accueil
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'pong.html')  # Fragment AJAX
    return render(request, 'base.html', {"initial_fragment": "pong.html"})

def account_view(request, username=None):
    """Access to account"""
    if not request.user.is_authenticated:
        # Si la requête est AJAX, renvoyer 403 ; sinon rediriger vers home
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden("Vous devez être connecté pour voir ce profil.")
        else:
            return redirect('/')  # redirige vers la page d'accueil
    
    if username is None or username == request.user.username:
        user_profile = request.user
    else:
        user_profile = get_object_or_404(User, username=username)

    context = {
        "user_profile": user_profile
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'account.html', context)  # Fragment AJAX
    return render(request, 'base.html', {"initial_fragment": "account.html", "user_profile":user_profile})

def chat_view(request):
    """Vue pour tester JWT et WebSocket - nécessite authentification."""
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden()
        else:
            return redirect('/')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "chat.html")  # Fragment AJAX
    return render(request, "base.html", {"initial_fragment": "chat.html"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Géré par DRF : session OU JWT
def get_user_info(request):
    """Endpoint DRF protégé par la permission IsAuthenticated."""
    user = request.user
    return Response({
        "username": user.username,
        "avatar_url": f"/media/avatars/{user.username}.jpg" if user.username else None
    })

class CookieTokenRefreshView(TokenRefreshView):
    """Vue pour actualiser le token d'accès à partir du refresh token en cookie"""
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return JsonResponse({"error": "Refresh token manquant."}, status=401)

        request.data["refresh"] = refresh_token
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Met à jour le cookie d'access token
            access_token = response.data.get("access")
            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                secure=False,  # True si HTTPS
                samesite="Lax",
                max_age=3600
            )

        return response

class ProtectedView(APIView):
    """Exemple de vue DRF protégée par IsAuthenticated"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Données sécurisées accessibles uniquement aux utilisateurs authentifiés."})

@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Session ou JWT
def logout_view(request):
    """Se déconnecter : supprime la session et les cookies JWT"""
    logout(request)  # Supprime la session Django
    response = JsonResponse({"success": True, "message": "Déconnexion réussie !"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
