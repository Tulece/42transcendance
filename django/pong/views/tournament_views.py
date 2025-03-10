# tournament_views.py

from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from ..models import Tournament, TournamentMatch, CustomUser
from ..logic.tournament_lobby import TournamentLobby
from django.views.decorators.csrf import csrf_exempt
from pong.logic.lobby import Lobby
from asgiref.sync import sync_to_async
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


lobby = TournamentLobby() # Instance globale pour la gestion des tournois

@csrf_exempt
def create_tournament_view(request):
    users = CustomUser.objects.all()
    if request.method == "GET":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            # Requête AJAX, renvoyer uniquement le fragment
            return render(request, "tournaments/create_tournament.html", {"users": users})
        else:
            # Requête classique, renvoyer la page complète via base.html
            return render(request, "base.html", {
                "initial_fragment": "tournaments/create_tournament.html",
                "users": users
            })

    name = request.POST.get("name")
    player_ids = request.POST.getlist("players")
    players = CustomUser.objects.filter(id__in=player_ids)
    tournament = lobby.create_tournament(name, players)
    channel_layer = get_channel_layer()
    for player in players:
        async_to_sync(channel_layer.group_send)(
            f"user_{player.id}",
            {
                "type": "system",  # déclenche la méthode system dans le consumer
                "message": "Attention : Vous avez été ajouté à un tournoi. Merci de respecter les règles."
            }
        )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "tournament_id": tournament.id,
            "message": "Tournoi créé avec succès."
        }, status=201)
    else:
        return redirect("list_tournaments")


@require_GET
@csrf_exempt
def get_tournament_detail_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    # Si le tournoi est terminé, redirige vers la page d'accueil
    if not tournament.is_active:
        return redirect("/")  # Assurez-vous que l'URL nommée "home" est définie
    matches = tournament.matches.order_by("round_number", "created_at")
    context = {"tournament": tournament, "matches": matches}
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "tournaments/tournament_detail.html", context)
    else:
        return render(request, "base.html", {
            "initial_fragment": "tournaments/tournament_detail.html",
            "tournament": tournament,
            "matches": matches
        })


@csrf_exempt
@require_http_methods(["POST"])
async def start_match_game_view(request, match_id):
  try:
    match = await sync_to_async(TournamentMatch.objects.get)(id=match_id)
  except TournamentMatch.DoesNotExist:
    return JsonResponse({"success": False, "error": "Match non trouvé"}, status=404)

  # Si le match est déjà terminé, on refuse de le relancer
  if match.winner:
    return JsonResponse({"success": False, "error": "Match terminé"}, status=400)

  user_id = await sync_to_async(lambda: request.user.id)()

  # Accès asynchrone aux valeurs liées
  match_player1_id = await sync_to_async(lambda: match.player1.id)()
  match_player2_id = await sync_to_async(lambda: match.player2.id if match.player2 else None)()

  if user_id not in [match_player1_id, match_player2_id]:
    return JsonResponse({"success": False, "error": "Vous n'êtes pas participant de ce match."}, status=403)

  # Déterminer le rôle en fonction de l'identifiant de l'utilisateur connecté
  role = "player1" if user_id == match_player1_id else "player2"

  user1 = match.player1.username
  user2 = match.player2.username

  if not match.game_id:
    lobby_instance = Lobby.get_instance()  
    new_game_id = await lobby_instance.API_start_game_async(user1, user2)
    match.game_id = new_game_id
    await sync_to_async(match.save)()
  else:
    new_game_id = match.game_id

  return JsonResponse({
    "success": True,
    "game_id": new_game_id,
    "role": role,
    "player1_id": match_player1_id,
    "player2_id": match_player2_id,
  })

@csrf_exempt
def list_tournaments_view(request):
  tournaments = Tournament.objects.filter(is_active=True)
  context = {"tournaments": tournaments}
  if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    return render(request, "tournaments/list_tournaments.html", context)
  else:
    return render(request, "base.html", {
      "initial_fragment": "tournaments/list_tournaments.html",
      "tournaments": tournaments
    })

@require_POST
@csrf_exempt
def report_match_result_view(request, match_id):
    try:
        match = TournamentMatch.objects.get(id=match_id)
    except TournamentMatch.DoesNotExist:
        return JsonResponse({"success": False, "error": "Match introuvable."}, status=404)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    winner_id = data.get("winner_id")
    if not winner_id:
        return JsonResponse({"success": False, "error": "Pas de vainqueur indiqué."}, status=400)
    valid_winner_ids = []
    if match.player1:
        valid_winner_ids.append(str(match.player1.id))
    if match.player2:
        valid_winner_ids.append(str(match.player2.id))
    if winner_id not in valid_winner_ids:
        return JsonResponse({"success": False, "error": "winner_id invalide."}, status=400)
    from ..logic.tournament_lobby import TournamentLobby
    tlobby = TournamentLobby()
    tlobby.report_match_result(match.id, winner_id)
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"tournament_{match.tournament.id}",
        {"type": "tournament_update", "message": {"success": True, "message": "Tournoi mis à jour !"}}
    )
    tournament = match.tournament
    return JsonResponse({
        "success": True,
        "message": "Match mis à jour, round suivant préparé si nécessaire.",
        "tournament_active": tournament.is_active
    })



