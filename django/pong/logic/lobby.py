import uuid
import asyncio
import time
import json
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
        self.waiting_queue = {}  # File d'attente des joueurs
        self.active_games = {}   # Dictionnaire {game_id: instance de Game}
        #Launch a matchmaking loop, that will check elapsed_time and elo for each_player in queue, and 
        asyncio.create_task(self.matchmaking())

    def get_queue_len(self):
        """Retourne la longueur de la file d'attente."""
        return len(self.waiting_queue)

    def add_player_to_queue(self, player_consumer, elo):
        """Ajoute un joueur avec son ELO et le timestamp d'entrée dans la file d'attente."""
        self.waiting_queue[player_consumer] = {
            "elo": elo,
            "timestamp": time.time()
        }

    def remove_player_from_queue(self, player_consumer):
        """Retire un joueur de la file d'attente."""
        if player_consumer in self.waiting_queue:
            del self.waiting_queue[player_consumer]

    def remove_game(self, game_id):
        """Supprime une partie terminée."""
        if game_id in self.active_games:
            game = self.active_games.pop(game_id, None)
            if game:
                game.stop()
                print(f"Partie {game_id} supprimée.")

     
    async def matchmaking(self):
        """Effectue un matchmaking progressif basé sur l'ELO."""
        while True:
            if len(self.waiting_queue) < 2:
                await asyncio.sleep(5)
                continue

            current_time = time.time()

            for player1, data1 in list(self.waiting_queue.items()):
                elo1, timestamp1 = data1["elo"], data1["timestamp"]

                for player2, data2 in list(self.waiting_queue.items()):
                    if player1 == player2:
                        continue

                    elo2, timestamp2 = data2["elo"], data2["timestamp"]
                    elapsed_time = current_time - timestamp1

                    # Critères progressifs de matchmaking
                    if elapsed_time < 10 and abs(elo1 - elo2) <= 100:
                        await self.start_game(player1, player2)
                    elif elapsed_time < 20 and abs(elo1 - elo2) <= 200:
                        await self.start_game(player1, player2)
                    elif elapsed_time >= 20:
                        await self.start_game(player1, player2)

            await asyncio.sleep(1)

    async def start_game(self, player1, player2):
        """Démarre une partie entre deux joueurs déjà identifiés."""
        if player1 not in self.waiting_queue or player2 not in self.waiting_queue:
            print("Un ou plusieurs joueurs ne sont plus dans la file d'attente.", flush=True)
            return None

        game_id = str(uuid.uuid4())

        game = Game(game_id, player1, player2)
        self.active_games[game_id] = game
        self.remove_player_from_queue(player1)
        self.remove_player_from_queue(player2)

        asyncio.create_task(game.start())

        await player1.send(json.dumps({
            "type": "game_found",
            "game_id": game_id,
            "role": "player1"
        }))
        await player2.send(json.dumps({
            "type": "game_found",
            "game_id": game_id,
            "role": "player2"
        }))

        print(f"Partie créée avec l'ID {game_id} entre {player1} et {player2}", flush=True)
        return game_id



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
