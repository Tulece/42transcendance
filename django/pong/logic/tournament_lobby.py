import uuid
from ..models import Tournament, Match, CustomUser
from .lobby import Lobby
import random

class TournamentLobby:
    def __init__(self):
        self.active_tournaments = {}
        self.match_ready = {}  # Dictionnaire : { match_id: { "player1": True, "player2": True } }

    def create_tournament(self, name, players):
        """Crée un nouveau tournoi et génère les matchs du premier tour."""
        tournament = Tournament.objects.create(name=name)
        tournament.players.set(players)
        tournament.save()

        # On stocke le tournoi dans un dict local, au cas où tu veux un usage in-memory
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

            match = Match.objects.create(
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
        """Enregistre le résultat d'un match et prépare le tour suivant si nécessaire."""
        match = Match.objects.get(id=match_id)
        # Si le match a déjà un vainqueur, on ne refait pas l'étape
        if match.winner:
            return  # ou lever une exception

        winner = CustomUser.objects.get(id=winner_id)
        match.winner = winner
        match.is_active = False
        match.save()

        tournament = match.tournament
        current_round = match.round_number
        current_round_matches = tournament.matches.filter(round_number=current_round)

        # Vérifie si tous les matches de ce round ont un winner
        if all(m.winner for m in current_round_matches):
            next_matches = self._prepare_next_round(tournament, current_round + 1)

            if not next_matches:  # S'il n'y a plus de match, fin du tournoi
                tournament.is_active = False
                tournament.save()

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
            match = Match.objects.create(
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
            match = Match.objects.create(
                tournament=tournament,
                player1=player1,
                player2=player2,
                round_number=next_round_number
            )
            matches.append(match)

        return matches
