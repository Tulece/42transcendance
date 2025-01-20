from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken
from urllib.parse import parse_qs
from jwt import decode as jwt_decode
from django.conf import settings
from .logic.game import *
from .logic.ai_player import launch_ai
import json
from .logic.lobby import Lobby
import uuid
import asyncio

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consommateur WebSocket pour le chat avec authentification basée sur la session.
    """
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            print("Utilisateur non authentifié, fermeture de la connexion.")
            await self.close(code=4003)
            return
        self.username = user.username or "Anonyme"
        await self.accept()
        await self.send(json.dumps({
            "type": "welcome",
            "message": f"Bienvenue, {self.username} !"
        }))

        try:
            payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            self.username = payload.get('username', 'Anonyme')
            print(f"Utilisateur authentifié : {self.username}")
            await self.accept()
            await self.send(json.dumps({"type": "welcome", "message": f"Bienvenue, {self.username} !"}))
        except InvalidToken as e:
            print(f"Token invalide : {e}")
            await self.close(code=4003)
        except Exception as e:
            print(f"Erreur inattendue lors de la validation du token : {e}")
            await self.close(code=4003)

    async def disconnect(self, close_code):
        print(f"Déconnecté : {self.username} (code {close_code})", flush=True)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get("message")
            print(f"Message reçu de {self.username} : {message}")
            await self.send(json.dumps({
                "type": "chat_message",
                "username": self.username,
                "message": message
            }))
        except Exception as e:
            print(f"Erreur lors du traitement du message : {e}")
            await self.send(json.dumps({"type": "error", "message": "Erreur lors du traitement du message."}))


class LobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Gère la connexion d'un joueur au lobby."""
        self.lobby = Lobby.get_instance()
        self.player_id = str(uuid.uuid4())
        self.game_id = None

        await self.accept()
        print(f"Joueur {self.player_id} connecté au lobby.")

    async def disconnect(self, close_code):
        """Gère la déconnexion d'un joueur du lobby."""
        self.lobby.remove_player_from_queue(self)
        print(f"Joueur {self.player_id} déconnecté du lobby.", flush=True)

    async def receive(self, text_data):
        """Traite les messages reçus du client."""
        data = json.loads(text_data)
        action = data.get("action")

        if action == "find_game":
            await self.handle_find_game(data.get("mode"))
        elif action == "quit_queue":
            await self.handle_quit_queue()

    async def handle_find_game(self, mode):
        """Gère la demande de recherche d'une partie."""
        if mode == 'solo':
            game_id, player1 = await self.lobby.create_solo_game(self)
            await player1.send(json.dumps({
                "type": "game_found",
                "game_id": game_id,
                "role": "player1"
            }))
            return
        self.lobby.add_player_to_queue(self)
        print(f"Joueur {self.player_id} en attente d'une partie.")

        if self.lobby.get_queue_len() >= 2:
            game_id, player1, player2 = await self.lobby.create_game()

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

    async def handle_quit_queue(self):
        """Gère la demande de quitter la file d'attente."""
        self.lobby.remove_player_from_queue(self)
        await self.send(json.dumps({
            "type": "queue_left",
            "message": "Vous avez quitté la file d'attente."
        }))
        print(f"Joueur {self.player_id} a quitté la file d'attente.")


class PongConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Gère la connexion d'un joueur à une partie."""
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.lobby = Lobby.get_instance()
        self.game = self.lobby.get_game(self.game_id)

        if not self.game:
            await self.close()
            return

        query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        self.player_id = query_params.get('player_id', [None])[0]

        if not self.player_id or self.player_id not in ["player1", "player2"]:
            await self.close()
            return

        await self.channel_layer.group_add(self.game_id, self.channel_name)

        await self.accept()
        print(f"Joueur {self.player_id} connecté à la partie {self.game_id}.")

    async def disconnect(self, close_code):
        """Gère la déconnexion d'un joueur."""
        await self.channel_layer.group_discard(self.game_id, self.channel_name)
        print(f"Joueur {self.player_id} déconnecté de la partie {self.game_id}.")

        # Si nécessaire, notifier la classe Game ou le Lobby
        # if self.game:
        #     self.game.handle_player_disconnect(self.player_id)

    async def receive(self, text_data):
        """Reçoit les actions des joueurs et les transmet à la classe Game."""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if not action:
                return

            if self.game:
                self.game.handle_player_action(self.player_id, action)
        except Exception as e:
            print(f"Erreur lors de la réception d'un message : {e}")

    async def game_update(self, event):
        """Envoie les mises à jour du jeu aux joueurs via WebSocket."""
        await self.send(json.dumps(event["message"]))

