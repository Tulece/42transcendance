from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from ..models import Tournament, TournamentMatch, CustomUser, TournamentParticipation
from ..models import Tournament, TournamentMatch, CustomUser, TournamentParticipation
from ..logic.tournament_lobby import TournamentLobby
from ..logic.lobby import Lobby
from ..blockchain.tournament_contract import get_tournament_info
from asgiref.sync import sync_to_async
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.decorators import login_required


lobby = TournamentLobby()


def create_tournament_view(request):
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden()
        else:
            return redirect('/')

    if request.method == 'GET':
        users = CustomUser.objects.filter(online_status=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(request, "tournaments/create_tournament.html", {"users": users})
        else:
            return render(request, "base.html", {
                "initial_fragment": "tournaments/create_tournament.html",
                "users": users
            })

    elif request.method == 'POST':
        name = request.POST.get("name")
        player_ids = request.POST.getlist("players")

        if len(player_ids) < 2:
            error_message = "Un tournoi doit comporter au minimum 2 joueurs."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error_message})
            else:
                return render(request, "base.html", {
                    "initial_fragment": "tournaments/create_tournament.html",
                    "error": error_message,
                    "users": CustomUser.objects.filter(online_status=True)
                }, status=400)

        players = CustomUser.objects.filter(id__in=player_ids, online_status=True)
        if players.count() < 2:
            error_message = "Vous devez sélectionner au moins 2 joueurs connectés."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error_message}, status=400)
            else:
                return render(request, "base.html", {
                    "initial_fragment": "tournaments/create_tournament.html",
                    "error": error_message,
                    "users": CustomUser.objects.filter(online_status=True)
                })

        tournament = lobby.create_tournament(name=name, player_ids=[player.id for player in players])

        channel_layer = get_channel_layer()

        for player in players:
            async_to_sync(channel_layer.group_send)(
                f'user_{player.id}',
                {
                    "type": "system",
                    "message": f"Attention : Vous avez été ajouté au tournoi '{tournament.name}'. Merci de respecter les règles."
                }
            )

        async_to_sync(channel_layer.group_send)(
            'tournaments',
            {
                "type": "tournament_update",
                "message": {
                    "action": "new_tournament",
                    "tournament_id": tournament.id,
                    "tournament_name": tournament.name
                }
            }
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "tournament_id": tournament.id,
                "message": f"Tournoi '{tournament.name}' créé avec succès."
            }, status=201)

        return redirect("/tournaments/list/")



@require_GET

def get_tournament_detail_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    if not tournament.is_active:
        return redirect("/")

    if request.user.is_authenticated:
        participation = TournamentParticipation.objects.filter(tournament=tournament, player=request.user).first()
        if participation and not participation.tournament_alias:
            return redirect("choose_tournament_alias", tournament_id=tournament.id)

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




@require_http_methods(["POST"])
async def start_match_game_view(request, match_id):
  try:
    match = await sync_to_async(TournamentMatch.objects.get)(id=match_id)
  except TournamentMatch.DoesNotExist:
    return JsonResponse({"success": False, "error": "Match non trouvé"}, status=404)

  if match.winner:
    return JsonResponse({"success": False, "error": "Match terminé"}, status=400)

  user_id = await sync_to_async(lambda: request.user.id)()

  match_player1_id = await sync_to_async(lambda: match.player1.id)()
  match_player2_id = await sync_to_async(lambda: match.player2.id if match.player2 else None)()

  if user_id not in [match_player1_id, match_player2_id]:
    return JsonResponse({"success": False, "error": "Vous n'êtes pas participant de ce match."}, status=403)

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


def list_tournaments_view(request):
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseForbidden()
        else:
            return redirect('/')

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
    lobby.report_match_result(match.id, winner_id)
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

@login_required
def choose_tournament_alias_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    participation = get_object_or_404(TournamentParticipation, tournament=tournament, player=request.user)

    if request.method == "POST":
        alias = request.POST.get("tournament_alias", "").strip()
        if not alias:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "L'alias ne peut pas être vide."})
            else:
                return render(request, "tournaments/choose_alias.html", {
                    "tournament": tournament,
                    "error": "L'alias ne peut pas être vide."
                })
        if TournamentParticipation.objects.filter(tournament=tournament, tournament_alias=alias).exists():
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Cet alias est déjà pris dans ce tournoi."})
            else:
                return render(request, "tournaments/choose_alias.html", {
                    "tournament": tournament,
                    "error": "Cet alias est déjà pris dans ce tournoi."
                })
        participation.tournament_alias = alias
        participation.save()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            from django.urls import reverse
            redirect_url = reverse("tournament_detail_json", args=[tournament.id])
            return JsonResponse({
                "success": True,
                "message": "Alias enregistré.",
                "redirect_url": redirect_url
            })
        else:
            return redirect("tournament_detail_json", tournament_id=tournament.id)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "tournaments/choose_alias.html", {
            "tournament": tournament
        })
    else:
        return render(request, "base.html", {
            "initial_fragment": "tournaments/choose_alias.html",
            "tournament": tournament
        })



def get_blockchain_tournament(request, tournament_id):
    try:
        # Vérification que l'ID du tournoi est >= 0
        tournament_id = int(tournament_id)
        if tournament_id < 0:
            return JsonResponse({
                'success': False,
                'error': 'The minimum is 0'
            })

        # Récupération des informations du tournoi sur la blockchain
        name, winner = get_tournament_info(tournament_id)

        if name:
            return JsonResponse({
                'success': True,
                'data': {
                    'tournament_id': tournament_id,
                    'name': name,
                    'winner': winner
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Tournament not found in blockchain'
            }, status=404)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET
def blockchain_tournaments_view(request):
    context = {}
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('fragment'):
        return render(request, 'tournaments/blockchain_tournaments.html', context)
    else:
        return render(request, 'base.html', {
            'initial_fragment': 'tournaments/blockchain_tournaments.html',
            **context
        })

