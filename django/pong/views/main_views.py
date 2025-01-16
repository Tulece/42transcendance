from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse, HttpResponse

def home_view(request):
    """
    Gère la page d'accueil et les fragments AJAX pour la SPA
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Renvoyer uniquement le fragment de home
        return render(request, 'home.html')

    # Renvoyer le shell principal avec home comme contenu initial
    context = {"initial_fragment": "home.html"}
    return render(request, 'base.html', context)

def register_view(request):
    """
    Gère l'inscription d'un utilisateur
    """
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
        if avatar:
            fs = FileSystemStorage(location='media/avatars/')
            avatar_name = fs.save(avatar.name, avatar)
        else:
            avatar_name = None

        # Création de l'utilisateur
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )

        # Génération des tokens JWT
        refresh = RefreshToken.for_user(user)

        # Ajout des tokens dans la session
        request.session['access_token'] = str(refresh.access_token)
        request.session['refresh_token'] = str(refresh)

        # Réponse en mode SPA pour les requêtes AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"success": True, "redirect": "/"}, status=200)

        # Sinon, redirection normale vers la home
        return redirect('home')

    # Gestion des requêtes GET
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'register.html')

    context = {"initial_fragment": "register.html"}
    return render(request, "base.html", context)


def game_view(request):
    """
    Gère la vue pour le jeu Pong
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'pong.html')  # Fragment AJAX

    # Retourner le shell principal avec pong comme contenu initial
    context = {"initial_fragment": "pong.html"}
    return render(request, 'base.html', context)


def chat_view(request):
    """
    Vue pour tester JWT et WebSocket
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "chat.html")  # Fragment AJAX

    # Retourner le shell principal avec chat comme contenu initial
    context = {"initial_fragment": "chat.html"}
    return render(request, "base.html", context)
