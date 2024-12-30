from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
from rest_framework_simplejwt.tokens import RefreshToken

def home(request):
    return render(request, 'home.html')

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        avatar = request.FILES.get("avatar")

        # Validation des données
        if not username or not password:
            return render(request, "register.html", {"error_message": "Tous les champs sont obligatoires."})
        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {"error_message": "Nom d'utilisateur déjà pris."})

        # Sauvegarde de l'avatar
        if avatar:
            fs = FileSystemStorage(location='media/avatars/')
            avatar_name = fs.save(avatar.name, avatar)
        else:
            avatar_name = None

        # Création de l'utilisateur
        user = User.objects.create(
            username=username,
            password=make_password(password)
        )

        # Génération des tokens JWT
        refresh = RefreshToken.for_user(user)

        # Ajout des tokens dans la session
        request.session['access_token'] = str(refresh.access_token)
        request.session['refresh_token'] = str(refresh)

        # Redirection vers la page d'accueil
        return redirect('home')  # 'home' est le nom de la vue pour home.html dans vos URL

    return render(request, "register.html")
