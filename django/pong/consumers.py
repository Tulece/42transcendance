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
from channels.db import database_sync_to_async
from django.db import transaction
from pong.models import CustomUser
from datetime import datetime

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consommateur WebSocket pour le chat avec authentification basée sur la session et fonctionnalités avancées.
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

        # Charger les utilisateurs bloqués
        self.blocked_users_ids = await self.get_blocked_users_ids()
        self.blocked_by_ids = await self.get_blocked_by_ids()

        await self.accept()
        print(f"Connexion WebSocket acceptée pour l'utilisateur : {self.username}")

        # Définir les groupes
        self.room_group_name = "chat_room"
        self.personal_group = f"user_{self.user.id}"

        # Joindre les groupes
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        print(f"Utilisateur {self.username} ajouté au groupe {self.room_group_name}")
        await self.channel_layer.group_add(self.personal_group, self.channel_name)

        # Envoi d’un message de bienvenue
        await self.send(json.dumps({
            "type": "welcome",
            "message": f"Bienvenue, {self.username} !"
        }))

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if self.personal_group:
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)
        print(f"Déconnexion de l'utilisateur {self.username} - code: {close_code}")

    async def receive(self, text_data):
        print("Message reçu brut :", text_data)
        try:
            if not text_data:
                await self.send(json.dumps({"type": "error", "message": "Message vide"}))
                return

            data = json.loads(text_data)
            action = data.get("action")

            if action == "block_user":
                username_to_block = data.get("username_to_block")
                await self.block_user(username_to_block)
                return
            elif action == "unblock_user":
                username_to_unblock = data.get("username_to_unblock")
                await self.unblock_user(username_to_unblock)
                return

            message = data.get("message", "")
            target_username = data.get("target_username")
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if target_username:
                await self.send_private_message(target_username, message)
            else:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "sender_id": self.user.id,
                        "sender": self.username,
                        "message": message,
                        "timestamp": timestamp
                    }
                )
        except Exception as e:
            print(f"Erreur lors du traitement du message : {e}")
            await self.send(json.dumps({
                "type": "error",
                "message": "Erreur lors du traitement du message."
            }))

    async def chat_message(self, event):
        sender_id = event["sender_id"]
        if sender_id in self.blocked_users_ids:
            print(f"Message ignoré car l'utilisateur {sender_id} est bloqué.")
            return

        sender = event["sender"]
        message = event["message"]
        timestamp = event["timestamp"]

        await self.send(json.dumps({
            "type": "chat_message",
            "username": sender,
            "message": message,
            "timestamp": timestamp
        }))

    @database_sync_to_async
    def get_blocked_users_ids(self):
        return list(self.user.blocked_users.values_list('id', flat=True))

    @database_sync_to_async
    def get_blocked_by_ids(self):
        return list(self.user.blocked_by.values_list('id', flat=True))

    @database_sync_to_async
    def block_user_in_db(self, user_to_block_username):
        user_to_block = CustomUser.objects.get(username=user_to_block_username)
        self.user.blocked_users.add(user_to_block)
        return user_to_block

    @database_sync_to_async
    def unblock_user_in_db(self, user_to_unblock_username):
        user_to_unblock = CustomUser.objects.get(username=user_to_unblock_username)
        self.user.blocked_users.remove(user_to_unblock)
        return user_to_unblock

    async def send_private_message(self, target_username, message):
        try:
            found_user = await database_sync_to_async(CustomUser.objects.get)(username=target_username)
        except CustomUser.DoesNotExist:
            await self.send(json.dumps({
                "type": "error",
                "message": f"L'utilisateur '{target_username}' est introuvable."
            }))
            return

        target_group = f"user_{found_user.id}"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        await self.channel_layer.group_send(
            target_group,
            {
                "type": "private_message",
                "sender_id": self.user.id,
                "sender": self.username,
                "message": message,
                "timestamp": timestamp
            }
        )

    async def private_message(self, event):
        sender_id = event["sender_id"]
        if sender_id in self.blocked_users_ids:
            return

        sender = event["sender"]
        message = event["message"]
        timestamp = event["timestamp"]

        await self.send(json.dumps({
            "type": "private_message",
            "username": sender,
            "message": message,
            "timestamp": timestamp
        }))

    async def block_user(self, username_to_block):
        try:
            blocked_user = await self.block_user_in_db(username_to_block)
            self.blocked_users_ids.append(blocked_user.id)

            await self.send(json.dumps({
                "type": "system",
                "message": f"Vous avez bloqué {blocked_user.username}"
            }))
        except CustomUser.DoesNotExist:
            await self.send(json.dumps({
                "type": "error",
                "message": f"L’utilisateur {username_to_block} n’existe pas."
            }))

    async def unblock_user(self, username_to_unblock):
        try:
            unblocked_user = await self.unblock_user_in_db(username_to_unblock)
            if unblocked_user.id in self.blocked_users_ids:
                self.blocked_users_ids.remove(unblocked_user.id)

            await self.send(json.dumps({
                "type": "system",
                "message": f"Vous avez débloqué {unblocked_user.username}"
            }))
        except CustomUser.DoesNotExist:
            await self.send(json.dumps({
                "type": "error",
                "message": f"L’utilisateur {username_to_unblock} n’existe pas."
            }))


class LobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Gère la connexion d'un joueur au lobby."""
        self.lobby = Lobby.get_instance()
        self.player_id = str(uuid.uuid4())
        self.game_id = None

        await self.accept()
        print(f"Joueur {self.player_id} connecté au lobby.", flush=True)

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

    async def handle_find_game(self, mode, elo = 1000):
        """Gère la demande de recherche d'une partie en fonction de l'ELO."""
        if mode == 'solo':
            game_id, player1 = await self.lobby.create_solo_game(self)
            await player1.send(json.dumps({
                "type": "game_found",
                "game_id": game_id,
                "role": "player1"
            }))
        else:
            self.lobby.add_player_to_queue(self, elo)

            self.waiting_task = asyncio.create_task(self.send_waiting_messages())

            print(f"Joueur {self.player_id} en attente d'une partie (ELO {elo}).", flush=True)

    async def handle_quit_queue(self):
        """Gère la demande de quitter la file d'attente."""
        if self.waiting_task:
            self.waiting_task.cancel()

        self.lobby.remove_player_from_queue(self)
        await self.send(json.dumps({
            "type": "queue_left",
            "message": "Vous avez quitté la file d'attente."
        }))
        print(f"Joueur {self.player_id} a quitté la file d'attente.", flush=True)

    async def send_waiting_messages(self):
        """Envoie des messages de statut régulièrement."""
        try:
            while True:
                await self.send(json.dumps({
                    "type": "waiting",
                    "message": "En attente d'un adversaire"
                }))
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass


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
        self.is_ai = query_params.get('mode', ['human'])[0] == 'solo' and self.player_id == 'player2'

        if not self.is_ai:
            self.db_user = self.scope.get("user", None)

        if not self.player_id or self.player_id not in ["player1", "player2"]:
            await self.close()
            return

        await self.channel_layer.group_add(self.game_id, self.channel_name)

        await self.accept()
        print(f"Joueur {self.player_id} connecté à la partie {self.game_id}.", flush=True)

    async def disconnect(self, close_code):
        """Gère la déconnexion d'un joueur."""
        await self.channel_layer.group_discard(self.game_id, self.channel_name)
        print(f"Joueur {self.player_id} déconnecté de la partie {self.game_id}.", flush=True)

        if self.game:
            self.game.handle_player_disconnect(self.player_id)

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

    async def update_stats(self, go_message):
        db_user = self.scope.get("user", None)
        if db_user:
            if self.player_id in go_message:
                db_user.loses += 1
            else:
                db_user.wins += 1
            db_user.match_played += 1
            
            await database_sync_to_async(self._save_user)(db_user)

    @staticmethod
    @transaction.atomic
    def _save_user(user):
        user.save()

    async def game_update(self, event):
        """Envoie les mises à jour du jeu aux joueurs via WebSocket."""
        if event["message"]["type"] == "game_over" and not self.is_ai:
            await self.update_stats(event["message"]['message'])
        await self.send(json.dumps(event["message"]))



class TournamentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Récupère l'ID du tournoi depuis l'URL (définie dans le routing)
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.group_name = f'tournament_{self.tournament_id}'
        # On ajoute la connexion au groupe de ce tournoi
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print(f"Client connecté au tournoi {self.tournament_id}")

    async def disconnect(self, close_code):
        # On supprime la connexion du groupe
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"Client déconnecté du tournoi {self.tournament_id}")

    # Cette méthode sera appelée lors d'un group_send avec le type 'tournament_update'
    async def tournament_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))
