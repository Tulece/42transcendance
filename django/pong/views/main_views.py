from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login as django_login, logout
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseForbidden
from urllib.parse import urlparse
import json

def home_view(request):
    """
    Gère la page d'accueil et les fragments AJAX pour la SPA.
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'home.html')
    context = {"initial_fragment": "home.html"}
    return render(request, 'base.html', context)


def register_view(request):
    """
    Gère l'inscription d'un utilisateur
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        avatar = request.FILES.get("avatar")

        # Validation des données
        if not username or not password:
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
    """
    Gère la vue pour le jeu Pong - nécessite authentification.
    """
    if not request.user.is_authenticated:
        # Si la requête est AJAX, renvoyer 403 ; sinon rediriger vers home
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden()
        else:
            return redirect('/')  # redirige vers la page d'accueil
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'pong.html')  # Fragment AJAX
    return render(request, 'base.html', {"initial_fragment": "pong.html"})


def chat_view(request):
    """
    Vue pour tester JWT et WebSocket - nécessite authentification.
    """
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
    """
    Endpoint DRF protégé par la permission IsAuthenticated.
    - Soit via la session (sessionid),
    - Soit via le cookie 'access_token' (JWT).
    """
    user = request.user
    return Response({
        "username": user.username,
        "avatar_url": f"/media/avatars/{user.username}.jpg" if user.username else None
    })


def safe_next_url(next_url: str):
    """
    Ne garde que le path (ex: /game), ignore toute query string
    qui entraînerait un double-encodage (ex: ?csrfmiddlewaretoken=...).
    """
    parsed = urlparse(next_url)
    return parsed.path or "/"

@csrf_exempt
def login_view(request):
    """
    Vue de login :
    - lit ?next dans l'URL, le nettoie via safe_next_url
    - si POST JSON, identifie l'utilisateur et renvoie un JsonResponse
      { success, redirect }, sinon redirige (ou rejette) les forms classiques
    """
    if request.method == "GET":
        raw_next = request.GET.get("next", "/")
        next_url = safe_next_url(raw_next)
        # Si c’est une requête AJAX, on renvoie directement `login.html`
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return render(request, "login.html", {"next_url": next_url})
        # Sinon, on sert le shell 'base.html'
        return render(request, "base.html", {
            "initial_fragment": "login.html",
            "next_url": next_url
        })

    elif request.method == "POST":
        content_type = request.headers.get('Content-Type', '')
        # On attend un POST JSON via AJAX
        if 'application/json' in content_type:
            try:
                data = json.loads(request.body)
                username = data.get("username")
                password = data.get("password")
                raw_next = data.get("next", "/")
                next_url = safe_next_url(raw_next)
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "error": "Données invalides."}, status=400)
        else:
            # Si quelqu'un envoie un form classique => on redirige ou on rejette
            return redirect("/")

        # Vérification
        if not username or not password:
            return JsonResponse({"success": False, "error": "Nom d'utilisateur et mot de passe requis."}, status=400)

        # Authentification
        user = authenticate(request, username=username, password=password)
        if user:
            django_login(request, user)
            refresh = RefreshToken.for_user(user)

            response = JsonResponse({
                "success": True,
                "message": "Connexion réussie !",
                "redirect": next_url
            })
            # Dépose les cookies JWT
            response.set_cookie(
                "access_token",
                str(refresh.access_token),
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=3600
            )
            response.set_cookie(
                "refresh_token",
                str(refresh),
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=7 * 24 * 3600
            )
            return response
        else:
            return JsonResponse({"success": False, "error": "Identifiants incorrects."}, status=401)

    # Méthode non autorisée
    return JsonResponse({"success": False, "error": "Méthode non autorisée."}, status=405)



class CookieTokenRefreshView(TokenRefreshView):
    """
    Vue pour actualiser le token d'accès à partir du refresh token en cookie
    """
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
    """
    Exemple de vue DRF protégée par IsAuthenticated
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Données sécurisées accessibles uniquement aux utilisateurs authentifiés."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])  # Session ou JWT
def logout_view(request):
    """
    Se déconnecter :
    - Supprime la session
    - Supprime les cookies JWT
    """
    logout(request)  # Supprime la session Django
    response = JsonResponse({"success": True, "message": "Déconnexion réussie !"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
