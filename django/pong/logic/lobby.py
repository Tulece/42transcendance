import uuid
import asyncio
import time
import json
from ..models import SimpleMatch, CustomUser
from .game import Game
from .ai_player import AIPlayer, launch_ai
from channels.db import database_sync_to_async

class Lobby:
    _instance = None

    @staticmethod
    def get_instance():
        if Lobby._instance is None:
            Lobby()
        return Lobby._instance

    def __init__(self):
        if Lobby._instance is not None:
            raise Exception("Lobby est un singleton, utilisez get_instance() pour y accéder.")
        Lobby._instance = self
        self.waiting_queue = {}
        self.active_games = {}
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.matchmaking())
        except RuntimeError:
            print("Aucune boucle d'événements active lors de l'instanciation de Lobby.")

    async def API_start_game_async(self, player_id1, player_id2):
        game_id = str(uuid.uuid4())
        game = await Game.create(game_id, player_id1, player_id2)
        self.active_games[game_id] = game
        asyncio.create_task(game.start())
        return game_id

    def get_queue_len(self):
        return len(self.waiting_queue)

    def add_player_to_queue(self, player_consumer, ratio):
        for existing_consumer in self.waiting_queue.keys():
            if hasattr(existing_consumer, 'user') and hasattr(player_consumer, 'user'):
                if existing_consumer.user.username == player_consumer.user.username:
                    print(f"L'utilisateur {player_consumer.user.username} est déjà dans la file.")
                    return
        self.waiting_queue[player_consumer] = {
            "ratio": ratio,
            "timestamp": time.time()
        }


    def remove_player_from_queue(self, player_consumer):
        if player_consumer in self.waiting_queue:
            del self.waiting_queue[player_consumer]

    def remove_game(self, game_id):
        if game_id in self.active_games:
            game = self.active_games.pop(game_id, None)
            if game:
                game.stop()
                print(f"Partie {game_id} supprimée.")

    async def matchmaking(self):
        while True:
            if len(self.waiting_queue) < 2:
                for player in self.waiting_queue:
                    await player.send(json.dumps({"type": "waiting", "message": "En attente d'un adversaire"}))
                await asyncio.sleep(1)
                continue

            current_time = time.time()

            for player1, data1 in list(self.waiting_queue.items()):
                ratio1, timestamp1 = data1["ratio"], data1["timestamp"]
                best_match = None
                best_match_time = float('inf')

                for player2, data2 in list(self.waiting_queue.items()):
                    if player1 == player2:
                        continue

                    ratio2, timestamp2 = data2["ratio"], data2["timestamp"]
                    elapsed_time = current_time - timestamp1
                    ratio_diff = abs(ratio1 - ratio2)

                    if (elapsed_time < 10 and ratio_diff <= 0.1) or \
                       (10 <= elapsed_time < 20 and ratio_diff <= 0.2) or \
                       (elapsed_time >= 20):

                        if timestamp2 < best_match_time:
                            best_match = player2
                            best_match_time = timestamp2

                if best_match:
                    await self.start_game(player1, best_match)
                else:
                    await player1.send(json.dumps({"type": "waiting", "message": "En attente d'un adversaire"}))
            await asyncio.sleep(1)

    async def start_game(self, player1, player2):
        if player1 not in self.waiting_queue or player2 not in self.waiting_queue:
            print("Un ou plusieurs joueurs ne sont plus dans la file d'attente.", flush=True)
            return None

        game_id = str(uuid.uuid4())

        game = await Game.create(game_id, player1.scope["user"].username, player2.scope["user"].username)
        self.active_games[game_id] = game
        self.remove_player_from_queue(player1)
        self.remove_player_from_queue(player2)

        asyncio.create_task(game.start())

        await player1.send(json.dumps({
            "type": "game_found",
            "game_id": game_id,
            "role": "player1",
            "mode": "online"
        }))
        await player2.send(json.dumps({
            "type": "game_found",
            "game_id": game_id,
            "role": "player2",
            "mode": "online"
        }))

        return game_id

    async def create_solo_game(self, player_consumer):
        game_id = str(uuid.uuid4())

        game = await Game.create(game_id, player_consumer.scope['user'].username)
        
        ai_bot = asyncio.create_task(launch_ai("localhost", game_id))

        self.active_games[game_id] = game

        asyncio.create_task(game.start())

        return game_id, player_consumer


    async def create_local_game(self, player_consumer):

        game_id = str(uuid.uuid4())
        game_id = game_id[4:]
        game_id = "aaaa" + game_id

        game = await Game.create(game_id, player_consumer.scope['user'].username)

        self.active_games[game_id] = game

        asyncio.create_task(game.start())

        return game_id, player_consumer


    def get_game(self, game_id):
        return self.active_games.get(game_id)

