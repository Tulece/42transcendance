import uuid
from ..models import Tournament, TournamentMatch, CustomUser, TournamentParticipation
from ..blockchain.tournament_contract import store_tournament_result
from .lobby import Lobby
import random
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class TournamentLobby:
    def __init__(self):
        self.active_tournaments = {}
        self.match_ready = {}  # Dictionnaire : { match_id: { "player1": True, "player2": True } }

    def create_tournament(self, name, player_ids):
        if len(player_ids) < 2:
            raise ValueError("Il faut au minimum deux joueurs pour créer un tournoi.")

        players = CustomUser.objects.filter(id__in=player_ids, online_status=True)

        if players.count() < 2:
            raise ValueError("Il faut au minimum 2 joueurs connectés pour créer un tournoi.")

        tournament = Tournament.objects.create(name=name)

        # Crée la participation pour chaque joueur (le créateur pourra par exemple se voir attribuer un alias par défaut ou être invité à le choisir)
        for player in players:
            # Par défaut, on peut laisser tournament_alias vide ou lui assigner une valeur par défaut
            TournamentParticipation.objects.create(tournament=tournament, player=player, tournament_alias=None)

        tournament.save()

        self.active_tournaments[tournament.id] = {
            "tournament": tournament,
            "matches": self._generate_matches(tournament)
        }
        return tournament



    def _generate_matches(self, tournament):
        """Génère les matchs pour le premier tour."""
        players = list(tournament.players.all())
        matches = []
        round_number = 1

        while players:
            player1 = players.pop(0)
            player2 = players.pop(0) if players else None

            match = TournamentMatch.objects.create(
                tournament=tournament,
                player1=player1,
                player2=player2,
                round_number=round_number
            )

            # Bye automatique
            if player2 is None:
                match.winner = player1
                match.save()

            # IMPORTANT : on ajoute le match à la liste à chaque itération
            matches.append(match)

        return matches


    def get_next_match(self, tournament_id):
        """Retourne le prochain match qui n'a pas de vainqueur."""
        tournament_data = self.active_tournaments.get(tournament_id)
        if not tournament_data:
            return None

        for match in tournament_data["matches"]:
            if not match.winner:
                return match
        return None

    def report_match_result(self, match_id, winner_id):
        match = TournamentMatch.objects.get(id=match_id)
        # Si le match a déjà un vainqueur, on ne refait rien
        if match.winner:
            return

        winner = CustomUser.objects.get(id=winner_id)
        match.winner = winner
        match.is_active = False
        match.save()

        tournament = match.tournament
        current_round = match.round_number
        current_round_matches = tournament.matches.filter(round_number=current_round)

        # Si tous les matchs du round courant ont un vainqueur
        if all(m.winner for m in current_round_matches):
            next_matches = self._prepare_next_round(tournament, current_round + 1)

            if next_matches:
                # Annonce du début d'un nouveau round
                channel_layer = get_channel_layer()
                message = f"Attention : Nouveau round {current_round + 1} commence. Merci de respecter les règles."
                for player in tournament.players.all():
                    async_to_sync(channel_layer.group_send)(
                        f"user_{player.id}",
                        {
                            "type": "system",
                            "message": message
                        }
                    )
            else:
                # Aucun round suivant : le tournoi est terminé
                tournament.is_active = False
                tournament.save()
                # Récupérer le match final (celui avec le plus grand round_number)
                final_match = tournament.matches.order_by("-round_number").first()
                if final_match and final_match.winner:
                    channel_layer = get_channel_layer()
                    message = f"Le tournoi est terminé ! Le gagnant final est {final_match.winner.username}."
                    
                    # Store tournament result in blockchain
                    if final_match and final_match.winner:
                        blockchain_id = store_tournament_result(
                            tournament.name,
                            final_match.winner.username
                        )
                        if blockchain_id:
                            message += f" Tournament stored in blockchain with ID: {blockchain_id}"
                    for player in tournament.players.all():
                        async_to_sync(channel_layer.group_send)(
                            f"user_{player.id}",
                            {
                                "type": "system",
                                "message": message
                            }
                        )


    def _prepare_next_round(self, tournament, next_round_number):
        """
        Prépare les matchs pour le tour suivant en prenant en compte les vainqueurs
        et en attribuant un bye aléatoirement si le nombre de joueurs qualifiés est impair.
        """
        # Récupère tous les matchs du tour précédent
        previous_round_matches = tournament.matches.filter(round_number=next_round_number - 1)

        # Récupère les identifiants des joueurs ayant gagné leurs matchs
        winners = list(previous_round_matches.values_list("winner", flat=True))

        # Si moins de 2 joueurs sont qualifiés, le tournoi est terminé.
        if len(winners) < 2:
            return []

        matches = []

        # Si le nombre de gagnants est impair, sélectionne aléatoirement un joueur pour le bye
        if len(winners) % 2 == 1:
            bye_player_id = random.choice(winners)
            winners.remove(bye_player_id)
            bye_player = CustomUser.objects.get(id=bye_player_id)
            match = TournamentMatch.objects.create(
                tournament=tournament,
                player1=bye_player,
                player2=None,
                round_number=next_round_number
            )
            # Attribue automatiquement ce joueur comme vainqueur du match bye
            match.winner = bye_player
            match.save()
            matches.append(match)

        # Forme les matchs restants par paires
        while winners:
            player1_id = winners.pop(0)
            player2_id = winners.pop(0)
            player1 = CustomUser.objects.get(id=player1_id)
            player2 = CustomUser.objects.get(id=player2_id)
            match = TournamentMatch.objects.create(
                tournament=tournament,
                player1=player1,
                player2=player2,
                round_number=next_round_number
            )
            matches.append(match)

        return matches
