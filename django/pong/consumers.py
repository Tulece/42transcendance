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
from pong.models import CustomUser
from datetime import datetime

class ChatConsumer(AsyncWebsocketConsumer):

    room_group_name = None

    async def connect(self):
        self.user = self.scope.get("user", None)

        if not self.user or not self.user.is_authenticated:
            print("Utilisateur non authentifié. Fermeture de la connexion.")
            await self.close(code=4003)
            return
        
        # Mettre is_online = True
        await self.set_user_online_state(self.user, True)

        self.username = self.user.username or "Anonyme"

        # Charger les utilisateurs bloqués
        self.blocked_users_ids = await self.get_blocked_users_ids()

        await self.accept()
        print(f"Connexion WebSocket acceptée pour l'utilisateur : {self.username}")
        
        blocked_users = await self.get_blocked_users()
        await self.send(json.dumps({ 
            "type": "user_list",
            "blocked_users": blocked_users
        }))

        # Définir les groupes
        self.room_group_name = "chat_room"
        self.personal_group = f"user_{self.user.id}"

        # Joindre les groupes
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        print(f"Utilisateur {self.username} ajouté au groupe {self.room_group_name}")
        await self.channel_layer.group_add(self.personal_group, self.channel_name)
        
        # Diffuser la liste actualisée
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "broadcast_user_list"}
        )

        # Envoi d’un message de bienvenue
        await self.send(json.dumps({
            "type": "welcome",
            "message": f"Bienvenue, {self.username} !"
        }))

    async def disconnect(self, close_code):

        
        if self.user.is_authenticated:
            await self.set_user_online_state(self.user, False)

        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if self.personal_group:
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)
        
        # Diffuser la liste actualisée
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "broadcast_user_list"}
        )
        
        print(f"Déconnexion de l'utilisateur {self.username} - code: {close_code}")

    async def receive(self, text_data):
        
        try:
            if not text_data:
                await self.send(json.dumps({"type": "error", "message": "Message vide"}))
                return

            data = json.loads(text_data)
            action = data.get("action")
            print(f"🔍 Reçu action={action}, username_to_block={data.get('username_to_block')}, username_to_unblock={data.get('username_to_unblock')}")

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

    @database_sync_to_async # This one & get_blocked_users() give blocked users but not with the same format
    def get_blocked_users_ids(self): # utilisée en interne pour filtrer les messages dans chat_message()
        return list(self.user.blocked_users.values_list('id', flat=True))

    @database_sync_to_async
    def toggle_block_user_in_db(self, username, block=True):
        user = CustomUser.objects.get(username=username)
        if block:
            self.user.blocked_users.add(user)
        else:
            self.user.blocked_users.remove(user)
        return user
    
    @database_sync_to_async
    def get_blocked_users(self): #utilisée pour envoyer la liste des bloqués au frontend
        """Retourne la liste des users bloqués"""
        return list(self.user.blocked_users.values("username"))
    
    @database_sync_to_async
    def set_user_online_state(self, user, state: bool): # Modifier un user en BFF
        """MAJ du champ online_status en DB."""
        user.online_status = state
        user.save()
    
    @database_sync_to_async
    def get_online_users(self): # read la liste des users qui sont online
        """Retourne la liste des users online."""
        queryset = CustomUser.objects.filter(online_status=True).values("username")
        return list(queryset)




    async def send_private_message(self, target_username, message):
        try:
            found_user = await database_sync_to_async(CustomUser.objects.get)(username=target_username)
        except CustomUser.DoesNotExist:
            await self.send(json.dumps({
                "type": "error",
                "message": f"L'utilisateur '{target_username}' est introuvable."
            }))
            return

        #Check si expéditeur is blocked
        is_blocked = await database_sync_to_async(found_user.blocked_users.filter(id=self.user.id).exists)()
        if is_blocked:
            # Send error only à l'expéditeur
            await self.send(json.dumps({
                "type": "error_private",
                "message": f"Impossible d'envoyer un message privé à {target_username}, car vous avez été bloqué."
            }))
            return

        target_group = f"user_{found_user.id}"
        sender_group = self.personal_group
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

        await self.channel_layer.group_send(
            sender_group,
            {
                "type": "private_message",
                "sender_id": self.user.id,
                "sender": self.username,
                "target_username": target_username,
                "message": message,
                "timestamp": timestamp
            }
        )

    async def private_message(self, event):
        sender_id = event["sender_id"]

        sender = event["sender"]
        message = event["message"]
        timestamp = event["timestamp"]

        await self.send(json.dumps({
            "type": "private_message",
            "username": sender,
            "message": message,
            "timestamp": timestamp
        }))
    
    async def block_user(self, username): # ADD USER ERROR
        blocked_user = await self.toggle_block_user_in_db(username, block=True)
        self.blocked_users_ids = await self.get_blocked_users_ids() # HOW MAJ ???
        await self.send_blocked_users_list()
        await self.send_user_list()
        await self.send(json.dumps({"type": "system", "message": f"Vous avez bloqué {blocked_user.username}"}))

    async def unblock_user(self, username):
        unblocked_user = await self.toggle_block_user_in_db(username, block=False)
        self.blocked_users_ids = await self.get_blocked_users_ids()
        await self.send_blocked_users_list()
        await self.send_user_list()
        await self.send(json.dumps({"type": "system", "message": f"Vous avez débloqué {unblocked_user.username}"}))

    async def broadcast_user_list(self, event):
    # Charger la liste des users online_status = True
        online_users = await self.get_online_users()

    # Envoyer par WebSocket
        await self.send(json.dumps({
            "type": "user_list",
            "users": online_users,
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

