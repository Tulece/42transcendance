import uuid
import asyncio
from .game import Game
from .ai_player import AIPlayer, launch_ai

class Lobby:
    _instance = None

    @staticmethod
    def get_instance():
        """Retourne l'instance unique de Lobby."""
        if Lobby._instance is None:
            Lobby()
        return Lobby._instance

    def __init__(self):
        if Lobby._instance is not None:
            raise Exception("Lobby est un singleton, utilisez get_instance() pour y accéder.")
        Lobby._instance = self
        self.waiting_queue = []  # File d'attente des joueurs
        self.active_games = {}   # Dictionnaire {game_id: instance de Game}

    def get_queue_len(self):
        """Retourne la longueur de la file d'attente."""
        return len(self.waiting_queue)

    def add_player_to_queue(self, player_consumer):
        """Ajoute un joueur à la file d'attente."""
        self.waiting_queue.append(player_consumer)

    def remove_player_from_queue(self, player_consumer):
        """Retire un joueur de la file d'attente."""
        print("remove player from queue called", flush=True)
        if player_consumer in self.waiting_queue:
            print("remove player from lobby", flush=True)
            self.waiting_queue.remove(player_consumer)

    def remove_game(self, game_id):
        """Supprime une partie terminée."""
        if game_id in self.active_games:
            game = self.active_games.pop(game_id, None)
            if game:
                game.stop()
                print(f"Partie {game_id} supprimée.")

    async def create_game(self):
        """Crée une partie si deux joueurs sont disponibles."""
        if len(self.waiting_queue) >= 2:
            player1 = self.waiting_queue.pop(0)
            player2 = self.waiting_queue.pop(0)

            game_id = str(uuid.uuid4())

            game = Game(game_id, player1, player2)
            self.active_games[game_id] = game

            asyncio.create_task(game.start())

            return game_id, player1, player2
        return None, None, None
    
    async def create_solo_game(self, player_consumer):
        """Crée une partie si deux joueurs sont disponibles."""

        game_id = str(uuid.uuid4())

        ai_bot = asyncio.create_task(launch_ai("localhost", game_id))

        game = Game(game_id, player_consumer, ai_bot)
        self.active_games[game_id] = game

        asyncio.create_task(game.start())

        return game_id, player_consumer

    def get_game(self, game_id):
        """Récupère une instance de Game par son identifiant."""
        return self.active_games.get(game_id)
