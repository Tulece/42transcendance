import uuid
from ..models import Tournament, Match, CustomUser
from .lobby import Lobby

class TournamentLobby:
    def __init__(self):
        self.active_tournaments = {}

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
        match.save()

        tournament = match.tournament
        current_round = match.round_number
        current_round_matches = tournament.matches.filter(round_number=current_round)

        # Vérifie si tous les matches de ce round ont un winner
        if all(m.winner for m in current_round_matches):
            self._prepare_next_round(tournament, current_round + 1)

    def _prepare_next_round(self, tournament, next_round_number):
        """Prépare les matchs pour le tour suivant."""
        winners = tournament.matches.filter(round_number=next_round_number - 1).values_list("winner", flat=True)
        players = list(winners)

        # Si < 2 joueurs, ça ne sert à rien de créer un round de plus
        if len(players) < 2:
            return []  # On sort directement, pas de nouveau match

        matches = []
        while players:
            player1_id = players.pop(0)
            player2_id = players.pop(0) if players else None

            player1 = CustomUser.objects.get(id=player1_id)
            player2 = CustomUser.objects.get(id=player2_id) if player2_id else None

            match = Match.objects.create(
                tournament=tournament,
                player1=player1,
                player2=player2,
                round_number=next_round_number
            )

            # Bye automatique si player2 == None
            if player2 is None:
                match.winner = player1
                match.save()

            matches.append(match)

        return matches
