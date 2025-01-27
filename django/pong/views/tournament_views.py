from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from ..models import Tournament, Match, CustomUser
from ..logic.tournament_lobby import TournamentLobby
from django.views.decorators.csrf import csrf_exempt

lobby = TournamentLobby()  # On instancie 1 lobby global (optionnel)

@require_POST
@csrf_exempt
def create_tournament_view(request):
    """Crée un tournoi et renvoie un JSON avec l'ID du tournoi."""
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
            "player2": m.player2.username if m.player2 else None,
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

@require_POST
@csrf_exempt
def report_match_result_view(request, match_id):
    """
    Reporte le vainqueur d'un match et génère le round suivant si nécessaire.
    Renvoie du JSON (success/error).
    """
    winner_id = request.POST.get("winner_id")
    if not winner_id:
        return JsonResponse({"success": False, "error": "winner_id manquant"}, status=400)

    # On s’appuie sur la logique du TournamentLobby
    try:
        lobby.report_match_result(match_id, winner_id)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"success": True, "message": "Résultat enregistré."})
