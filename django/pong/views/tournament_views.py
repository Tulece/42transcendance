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
    """Crée un tournoi et renvoie un JSON avec l'ID du tournoi."""
    if request.method == "GET":
        users = CustomUser.objects.all()
        return render(request, "tournaments/create_tournament.html", {"users": users})
    name = request.POST.get("name")
    player_ids = request.POST.getlist("players")  # liste d'IDs
    players = CustomUser.objects.filter(id__in=player_ids)

    # Utilise la logique du TournamentLobby
    tournament = lobby.create_tournament(name, players)

    return JsonResponse({
        "success": True,
        "tournament_id": tournament.id,
        "message": "Tournoi créé avec succès."
    }, status=201)

@require_GET
@csrf_exempt
def get_tournament_detail_view(request, tournament_id):
    """
    Renvoie les détails d'un tournoi sous forme JSON
    (nom, matches, joueurs, etc.).
    """
    tournament = get_object_or_404(Tournament, id=tournament_id)
    matches = tournament.matches.order_by("round_number", "created_at")

    # Construire une structure de données (liste) pour les matches
    matches_data = []
    for m in matches:
        matches_data.append({
            "match_id": m.id,
            "player1": m.player1.username,
            "player1_id": m.player1.id,
            "player2": m.player2.username if m.player2 else None,
            "player2_id": m.player2.id if m.player2 else None,
            "winner": m.winner.username if m.winner else None,
            "round_number": m.round_number
        })

    return JsonResponse({
        "success": True,
        "tournament": {
            "id": tournament.id,
            "name": tournament.name,
            "is_active": tournament.is_active,
            "matches": matches_data
        }
    })

@csrf_exempt
@require_http_methods(["POST"])
async def start_match_game_view(request, match_id):
    try:
        match = await sync_to_async(Match.objects.get)(id=match_id)
    except Match.DoesNotExist:
        return JsonResponse({"success": False, "error": "Match non trouvé"}, status=404)

    lobby_instance = Lobby.get_instance()
    # Appel de la méthode asynchrone et attente du résultat
    game_id = await lobby_instance.API_start_game_async()
    return JsonResponse({"success": True, "game_id": game_id})
