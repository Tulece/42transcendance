from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from ..models import Tournament, Match, CustomUser
from ..logic.tournament_lobby import TournamentLobby
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from pong.logic.lobby import Lobby
from asgiref.sync import sync_to_async

lobby = TournamentLobby()  # On instancie 1 lobby global (optionnel)

@csrf_exempt
def create_tournament_view(request):
    """
    Crée un tournoi.
    Si la requête est AJAX, renvoie du JSON.
    Sinon, affiche une alerte puis redirige vers la liste des tournois.
    """
    if request.method == "GET":
        users = CustomUser.objects.all()
        return render(request, "tournaments/create_tournament.html", {"users": users})

    name = request.POST.get("name")
    player_ids = request.POST.getlist("players")
    players = CustomUser.objects.filter(id__in=player_ids)

    tournament = lobby.create_tournament(name, players)

    # Vérifier si c'est une requête AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "tournament_id": tournament.id,
            "message": "Tournoi créé avec succès."
        }, status=201)
    else:
        # Pour une requête classique, on redirige
        from django.shortcuts import redirect
        # Vous pouvez aussi afficher un message en session ou dans l'URL
        return redirect("list_tournaments")


@require_GET
@csrf_exempt
def get_tournament_detail_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    matches = tournament.matches.order_by("round_number", "created_at")
    context = {
        "tournament": tournament,
        "matches": matches
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # On renvoie uniquement le fragment (sans header)
        return render(request, "tournaments/tournament_detail.html", context)
    else:
        # On renvoie la page "complète" (base.html), qui inclura ton fragment
        return render(request, "base.html", {
            "initial_fragment": "tournaments/tournament_detail.html",
            "tournament": tournament,
            "matches": matches
        })

@csrf_exempt
@require_http_methods(["POST"])
async def start_match_game_view(request, match_id):
    try:
        match = await sync_to_async(Match.objects.get)(id=match_id)
    except Match.DoesNotExist:
        return JsonResponse({"success": False, "error": "Match non trouvé"}, status=404)

    user_id = await sync_to_async(lambda: request.user.id)()

    # Vérifier que l'utilisateur fait partie du match
    if user_id not in [match.player1_id, match.player2_id]:
        return JsonResponse({"success": False, "error": "Vous n'êtes pas participant de ce match."}, status=403)

    # Regarder si on a déjà un game_id
    if not match.game_id:
        # Pas de partie encore créée -> on la crée
        lobby_instance = Lobby.get_instance()
        new_game_id = await lobby_instance.API_start_game_async()

        # On enregistre dans le Match
        match.game_id = new_game_id
        await sync_to_async(match.save)()
    else:
        # Partie déjà en cours
        new_game_id = match.game_id

    return JsonResponse({"success": True, "game_id": new_game_id})



@csrf_exempt
def list_tournaments_view(request):
    tournaments = Tournament.objects.filter(is_active=True)
    context = {"tournaments": tournaments}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # On renvoie le fragment direct (sans extends)
        return render(request, "tournaments/list_tournaments.html", context)
    else:
        # On renvoie la structure globale (base.html)
        # qui inclut le fragment via initial_fragment
        return render(request, "base.html", {
            "initial_fragment": "tournaments/list_tournaments.html",
            "tournaments": tournaments
        })

@require_POST
@csrf_exempt
def report_match_result_view(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
    except Match.DoesNotExist:
        return JsonResponse({"success": False, "error": "Match introuvable."}, status=404)

    winner_id = request.POST.get("winner_id")  # ex: 'player1'
    if not winner_id:
        return JsonResponse({"success": False, "error": "Pas de vainqueur indiqué."}, status=400)

    # Vérifier que le winner_id correspond bien à match.player1 ou match.player2
    valid_winner_ids = []
    if match.player1:
        valid_winner_ids.append(str(match.player1.id))
    if match.player2:
        valid_winner_ids.append(str(match.player2.id))

    if winner_id not in valid_winner_ids:
        return JsonResponse({"success": False, "error": "winner_id invalide."}, status=400)

    # Appel de la méthode du TournamentLobby
    from ..logic.tournament_lobby import TournamentLobby
    tlobby = TournamentLobby()
    tlobby.report_match_result(match.id, winner_id)

    return JsonResponse({"success": True, "message": "Match mis à jour, round suivant préparé si nécessaire."})
