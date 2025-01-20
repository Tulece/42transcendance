from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from urllib.parse import parse_qs
from jwt import decode as jwt_decode
from django.conf import settings
from .logic.game import *
from .logic.ai_player import launch_ai
from datetime import datetime
import json
from .logic.lobby import Lobby
import uuid
import asyncio


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consommateur WebSocket pour un chat global
    """
    room_group_name = None

    async def connect(self):
        print("Tentative de connexion WebSocket.")
        self.user = self.scope.get("user", None)

        if not self.user or not self.user.is_authenticated:
            print("Utilisateur non authentifié. Fermeture de la connexion.")
            await self.close(code=4003)
            return

        self.username = self.user.username or "Anonyme"
        await self.accept()
        print(f"Connexion WebSocket acceptée pour l'utilisateur : {self.username}")

        self.room_group_name = "chat_room"
        self.personal_group = f"user_{self.user.id}"

        # Joindre le groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        print(f"Utilisateur {self.username} ajouté au groupe {self.room_group_name}")

        # Add au groupe perso.
        await self.channel_layer.group_add(
            self.personal_group,
            self.channel_name
        )

        # Envoi d’un message de bienvenue
        await self.send(json.dumps({
            "type": "welcome",
            "message": f"Bienvenue, {self.username} !"
        }))

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        if self.personal_group:
            await self.channel_layer.group_discard(
                self.personal_group,
                self.channel_name
            )
        print(f"Déconnexion de l'utilisateur {self.username} - code: {close_code}")

    async def receive(self, text_data):
        print("Message reçu brut :", text_data)
        try:
            if not text_data:
                await self.send(text_data=json.dumps({"error": "Message vide"}))
                return

            data = json.loads(text_data)
            message = data.get("message", "")
            target_username = data.get("target_username")
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if target_username:
                await self.send_private_message(target_username, message)
            else:
                # Diffuser le message à tout le monde dans le groupe
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "sender": self.username,
                        "message": message,
                        "timestamp": timestamp
                    }
                )
        except Exception as e:
            print(f"Erreur lors du traitement du message : {e}", flush = True)
            await self.send(json.dumps({
                "type": "error",
                "message": "Erreur lors du traitement du message."
            }))

    async def chat_message(self, event):
        """
        Méthode appelée quand on fait `group_send(..., {"type": "chat_message", ...})`.
        """
        sender = event["sender"]
        message = event["message"]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Envoyer ce message au client WebSocket
        await self.send(json.dumps({
            "type": "chat_message",
            "username": sender,
            "message": message,
            "timestamp": timestamp
        }))
    
    @database_sync_to_async
    def get_user_by_username(self, username):
        return User.objects.get(username=username)

    async def send_private_message(self, target_username, message):
        """
        Cherche l'utilisateur ayant ce 'target_username',
        et envoie un 'private_message' à son groupe perso : 'user_<id>'.
        """
        try:
            found_user = await self.get_user_by_username(target_username)
        except User.DoesNotExist:
            await self.send(json.dumps({
                "type": "error",
                "message": f"L'utilisateur '{target_username}' est introuvable."
            }))
            return

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        target_group = f"user_{found_user.id}"
        await self.channel_layer.group_send(
            target_group,
            {
                "type": "private_message",
                "sender": self.username,
                "message": message,
                "timestamp": timestamp
            }
        )


    # Gestion envoi messages privés
    async def private_message(self, event):
        sender = event["sender"]
        message = event["message"]
        timestamp = event.get("timestamp") # récupéré du group_send
        await self.send(json.dumps({
            "type": "private_message",
            "username": sender,
            "message": message,
            "timestamp": timestamp
        }))




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
        print(f"Joueur {self.player_id} déconnecté du lobby.")

    async def receive(self, text_data):
        """Traite les messages reçus du client."""
        data = json.loads(text_data)
        action = data.get("action")

        if action == "find_game":
            await self.handle_find_game()
        elif action == "quit_queue":
            await self.handle_quit_queue()

    async def handle_find_game(self):
        """Gère la demande de recherche d'une partie."""
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

