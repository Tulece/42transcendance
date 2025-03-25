import uuid
from ..models import Tournament, TournamentMatch, CustomUser, TournamentParticipation
from ..blockchain.tournament_contract import store_tournament_result
import random
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from threading import Thread


class TournamentLobby:
    def __init__(self):
        self.active_tournaments = {}
        self.match_ready = {}

    def create_tournament(self, name, player_ids):
        if len(player_ids) < 2:
            raise ValueError("Il faut au minimum deux joueurs pour créer un tournoi.")

        players = CustomUser.objects.filter(id__in=player_ids, online_status=True)

        if players.count() < 2:
            raise ValueError("Il faut au minimum 2 joueurs connectés pour créer un tournoi.")

        tournament = Tournament.objects.create(name=name)

        for player in players:
            TournamentParticipation.objects.create(tournament=tournament, player=player, tournament_alias=None)

        tournament.save()

        self.active_tournaments[tournament.id] = {
            "tournament": tournament,
            "matches": self._generate_matches(tournament)
        }
        return tournament

    def _generate_matches(self, tournament):
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

            if player2 is None:
                match.winner = player1
                match.save()

            matches.append(match)

        return matches

    def get_next_match(self, tournament_id):
        tournament_data = self.active_tournaments.get(tournament_id)
        if not tournament_data:
            return None

        for match in tournament_data["matches"]:
            if not match.winner:
                return match
        return None

    def store_result_async(self, tournament_name, winner_name):
        def async_task():
            blockchain_id = store_tournament_result(tournament_name, winner_name)
            tournament = Tournament.objects.get(name=tournament_name)
            tournament.blockchain_id = blockchain_id
            tournament.save()

            channel_layer = get_channel_layer()
            message = f"Tournoi {tournament_name} sauvegardé sur la blockchain (ID: {blockchain_id})"
            for player in tournament.players.all():
                async_to_sync(channel_layer.group_send)(
                    f"user_{player.id}",
                    {"type": "system", "message": message}
                )

        Thread(target=async_task).start()

    def report_match_result(self, match_id, winner_id):
        match = TournamentMatch.objects.get(id=match_id)
        if match.winner:
            return

        winner = CustomUser.objects.get(id=winner_id)
        match.winner = winner
        match.is_active = False
        match.save()

        tournament = match.tournament
        current_round = match.round_number
        current_round_matches = tournament.matches.filter(round_number=current_round)

        if all(m.winner for m in current_round_matches):
            next_matches = self._prepare_next_round(tournament, current_round + 1)

            if next_matches:
                channel_layer = get_channel_layer()
                message = f"Attention : Nouveau round {current_round + 1} commence. Merci de respecter les règles."
                for player in tournament.players.all():
                    async_to_sync(channel_layer.group_send)(
                        f"user_{player.id}",
                        {"type": "system", "message": message}
                    )
            else:
                tournament.is_active = False
                tournament.save()
                final_match = tournament.matches.order_by("-round_number").first()
                if final_match and final_match.winner:
                    self.store_result_async(tournament.name, final_match.winner.username)

                    channel_layer = get_channel_layer()
                    message = f"Le tournoi est terminé ! Le gagnant final est {final_match.winner.username}. Résultat blockchain en cours de sauvegarde..."
                    for player in tournament.players.all():
                        async_to_sync(channel_layer.group_send)(
                            f"user_{player.id}",
                            {"type": "system", "message": message}
                        )

    def _prepare_next_round(self, tournament, next_round_number):
        previous_round_matches = tournament.matches.filter(round_number=next_round_number - 1)

        winners = list(previous_round_matches.values_list("winner", flat=True))
        if len(winners) < 2:
            return []

        matches = []

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
            match.winner = bye_player
            match.save()
            matches.append(match)

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
