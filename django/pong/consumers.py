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
from pong.models import CustomUser, SimpleMatch
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import time
from .urls import INVITATIONS


class ChatConsumer(AsyncWebsocketConsumer):

    room_group_name = None

    async def start_cleanup_task(self):
        while True:
            expired_keys = []
            now = time.time()
            #invitations en cours
            for key, inv in list(INVITATIONS.items()):
                if inv["expires_at"] < now:
                    expired_keys.append(key)

            for key in expired_keys:
                invitation = INVITATIONS.pop(key, None)
                if invitation is None:
                    continue

                from_id = invitation["from_id"]
                to_id = invitation["to_id"]

                await self.channel_layer.group_send(
                    f"user_{from_id}",
                    {
                        "type": "invitation_expired",
                        "invite_id": key, #UUID from invitation
                    }
                )
                await self.channel_layer.group_send(
                    f"user_{to_id}",
                    {
                        "type": "invitation_expired",
                        "invite_id": key,
                    }
                )

            # Wait for 1s
            await asyncio.sleep(1)

    async def invitation_expired(self, event):
        invite_id = event["invite_id"]
        # On relaie au frontend
        await self.send(json.dumps({
            "type": "invitation_expired",
            "invite_id": invite_id
        }))


    async def connect(self):
        self.user = self.scope.get("user", None)

        if not self.user or not self.user.is_authenticated:
            print("Utilisateur non authentifié. Fermeture de la connexion.")
            await self.close(code=4003)
            return

        self.user_id = self.user.username
        await self.set_user_online_state(self.user_id, True)

        self.username = self.user.username or "Anonyme"

        # Charger les utilisateurs bloqués
        self.blocked_users_ids = await self.get_blocked_users_ids()

        await self.accept()
        print(f"Connexion WebSocket acceptée pour l'utilisateur : {self.username}")

        asyncio.create_task(self.start_cleanup_task())

        blocked_users = await self.get_blocked_users()
        await self.send(json.dumps({
            "type": "user_list",
            "blocked_users": blocked_users
        }))

        # Vérifier et définir les groupes
        self.room_group_name = "chat_room"

        self.personal_group = f"user_{self.user.id}"

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

        if hasattr(self, "room_group_name") and self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if hasattr(self, "personal_group"):
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)
        # Diffuser la liste actualisée aux utilisateurs
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "broadcast_user_list"}
        )
        print(f"Déconnexion de l'utilisateur {getattr(self, 'username', 'Inconnu')} - code: {close_code}")

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
            elif action == "accept_invitation":
                invite_id = data.get("invite_id")
                await self.accept_invitation(invite_id)
                return
            elif action == "removed" or action == "added":
                await self.user_list(data)
                return
            elif action == "invite_to_game":
                target_username = data.get("target_username")

                # # Check if invitation already sent & running
                # if any(inv["to"] == target_username for inv in INVITATIONS.values()):
                #     await self.send(json.dumps({
                #         "type": "error",
                #         "message": f"{target_username} a déjà une invitation en attente."
                #     }))
                #     return


                try:
                    target_user = await database_sync_to_async(CustomUser.objects.get)(username=target_username)
                except CustomUser.DoesNotExist:
                    print(f"Erreur : Utilisateur {target_username} introuvable.", flush=True)
                    return
                
                lobby_instance = Lobby.get_instance()
                existing_game_id = lobby_instance.get_game_id_by_player(target_username)

                if existing_game_id:
                    game_id = existing_game_id
                else:
                    game_id = await lobby_instance.API_start_game_async(self.scope["user"].username, target_username)

                # Vérifier si la partie existe bien dans le lobby
                if game_id not in lobby_instance.active_games:
                    print(f"Erreur : La partie {game_id} n'a pas été ajoutée au lobby.")
                    await self.send(json.dumps({
                        "type": "error",
                        "message": "Erreur lors de la création de la partie."
                    }))
                    return

                invite_id = str(uuid.uuid4()) # Stocker l'invit'
                expiration = time.time() + 30
                INVITATIONS[invite_id] = { # To stock these info in a dict.
                    "from": self.user.username,
                    "from_id": self.user.id,
                    "to": target_username,
                    "to_id": target_user.id,
                    "game_id": game_id,
                    "expires_at": expiration
                }

                # Notif' le dest. (send to the group dest)
                target_group = f"user_{target_user.id}"
                await self.channel_layer.group_send(
                    target_group,
                    {
                        "type": "private_message",
                        "sender_id": self.user.id,
                        "sender": self.user.username,
                        "message": "",
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "invitation": {
                            "invite_id": invite_id,
                            "game_id": game_id,
                            "expires_at": expiration,
                        },
                        "invite_type": "pong_invite",
                    }
                )

                print(f"✅ Envoi de l'invitation à {target_username} avec game_id={game_id}")

                # Validation envoi
                await self.send(json.dumps({
                    "type": "system",
                    "message": (
                        f"Invitation à jouer envoyée à {target_username}. "
                        f'<a href="/game?game_id={game_id}&mode=private&invite_id={invite_id}&role=player1" '
                        f'target="_blank" style="color:blue;">[lancer le jeu]</a>'
                    ),
                    "invite_id": invite_id
                }))

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
    def toggle_block_user_in_db(self, username, block=True):
        user = CustomUser.objects.get(username=username)
        if block:
            self.user.blocked_users.add(user)
        else:
            self.user.blocked_users.remove(user)
        return user

    @database_sync_to_async
    def get_blocked_users(self):
        return list(self.user.blocked_users.values("username"))

    # (CHANGED) set_user_online_state reçoit un user_id
    @database_sync_to_async
    def set_user_online_state(self, user_id, state: bool):
        try:
            user_obj = CustomUser.objects.get(username=user_id)  # get par l'ID
            user_obj.online_status = state
            user_obj.save()
        except CustomUser.DoesNotExist:
            print(f"[set_user_online_state] Introuvable pour user_id={user_id}")

    @database_sync_to_async
    def get_online_users(self):
        queryset = CustomUser.objects.filter(online_status=True).values("username")
        return list(queryset)

    @database_sync_to_async
    def reset_in_game_state(self):
        self.user.in_game = False
        self.user.save()


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
        if event.get("invite_type") == "pong_invite":
            invitation_data = event["invitation"]
            await self.send(json.dumps({
                "type": "game_invitation",
                "from": event["sender"],
                "game_id": invitation_data["game_id"],
                "invite_id": invitation_data["invite_id"],
                "expires_at": invitation_data["expires_at"],
            }))
            return

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

    async def block_user(self, username):
        blocked_user = await self.toggle_block_user_in_db(username, block=True)
        self.blocked_users_ids = await self.get_blocked_users_ids()
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
        online_users = await self.get_online_users()
        await self.send(json.dumps({
            "type": "user_list",
            "users": online_users,
        }))

    async def system(self, event):
        await self.send(json.dumps({
            "type": "system",
            "message": event["message"]
        }))

    async def user_list(self, event):
        action = event.get("action")
        username = event.get("username")

        await self.send(json.dumps({
            "type": "user_list",
            "action": action,
            "username": username
        }))




class LobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.lobby = Lobby.get_instance()
        self.player_id = str(uuid.uuid4())
        self.game_id = None
        self.user = self.scope.get("user", None)

        await self.accept()
        print(f"Joueur {self.player_id} connecté au lobby.", flush=True)

    async def disconnect(self, close_code):
        self.lobby.remove_player_from_queue(self)
        print(f"Joueur {self.player_id} déconnecté du lobby.", flush=True)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "find_game":
            await self.handle_find_game(data.get("mode"))
        elif action == "quit_queue":
            await self.handle_quit_queue()

    async def handle_find_game(self, mode):
        if mode == 'solo':
            game_id, player1 = await self.lobby.create_solo_game(self)
            await player1.send(json.dumps({
                "type": "game_found",
                "game_id": game_id,
                "role": "player1"
            }))
        elif mode == 'local':
            game_id, player = await self.lobby.create_local_game(self)
            await player.send(json.dumps({
                "type": "game_found",
                "game_id": game_id,
                "role": "local"
            }))
        else:
            user = self.scope["user"]
            ratio = user.wins / user.match_played if user.match_played > 0 else 0.5
            self.lobby.add_player_to_queue(self, ratio)
            print(f"Joueur {self.player_id} en attente d'une partie (Ratio : {ratio}).", flush=True)

    async def handle_quit_queue(self):
        if self.waiting_task:
            self.waiting_task.cancel()

        self.lobby.remove_player_from_queue(self)
        await self.send(json.dumps({
            "type": "queue_left",
            "message": "Vous avez quitté la file d'attente."
        }))
        print(f"Joueur {self.player_id} a quitté la file d'attente.", flush=True)



class PongConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.lobby = Lobby.get_instance()

        print(f"[PongConsumer] Tentative de connexion pour game_id: {self.game_id}")
        print(f"[PongConsumer] Jeux actifs: {list(self.lobby.active_games.keys())}")

        self.game = self.lobby.get_game(self.game_id)
        if not self.game:
            print(f"[PongConsumer] Game {self.game_id} introuvable, fermeture de la connexion.")
            await self.close()
            return

        query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        self.player_id = query_params.get('player_id', [None])[0]
        if self.player_id == "local":
            self.player_id = "player1"

        self.is_ai = query_params.get('mode', ['human'])[0] == 'solo' and self.player_id == 'player2'

        if not self.player_id or self.player_id not in ["player1", "player2"] and not self.player_id == 'local':
            print(f"[PongConsumer] Paramètre player_id invalide : {self.player_id}")
            await self.close()
            return

        await self.channel_layer.group_add(self.game_id, self.channel_name)
        await self.accept()
        print(f"[PongConsumer] Joueur {self.player_id} connecté à la partie {self.game_id}.", flush=True)
        self.game.set_player_connected(self.player_id)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.game_id, self.channel_name)
        player = getattr(self, "player_id", "unknown")
        print(f"[PongConsumer] Joueur {player} déconnecté de la partie {self.game_id}.", flush=True)
        if self.game:
            if hasattr(self, "player_id"):
                self.game.handle_player_disconnect(self.player_id)
            else:
                self.game.handle_player_disconnect("unknown")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            player_identifier = data.get('player', self.player_id)

            if not action:
                return
            if self.game:
                self.game.handle_player_action(player_identifier, action)
        except Exception as e:
            print(f"[PongConsumer] Erreur lors de la réception d'un message : {e}")

    async def game_update(self, event):
        if event["message"]["type"] == "game_over" and not self.is_ai:
            await self.update_stats(event["message"]['message'])
        await self.send(json.dumps(event["message"]))

    async def update_stats(self, go_message):
        db_user = self.scope.get("user", None)
        if db_user and db_user.is_authenticated:
            # (CHANGED) Utiliser l'id plutôt que le username
            user_id = db_user.id
            user_obj = await database_sync_to_async(CustomUser.objects.get)(pk=user_id)
            if user_obj:
                print(f"Enregistrement des statistiques pour {user_obj.username}")
                if self.player_id in go_message:
                    user_obj.loses += 1
                else:
                    user_obj.wins += 1
                user_obj.match_played += 1
                await database_sync_to_async(user_obj.save)()
            else:
                print("Utilisateur introuvable dans update_stats.")


class TournamentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.group_name = f'tournament_{self.tournament_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print(f"Client connecté au tournoi {self.tournament_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"Client déconnecté du tournoi {self.tournament_id}")

    async def tournament_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

class TournamentsGlobalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # On rejoint le groupe "tournaments"
        self.group_name = "tournaments"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print("Client connecté au flux global de tournois")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print("Client déconnecté du flux global de tournois")

    async def tournament_update(self, event):
        # event['message'] contient { "action": "new_tournament", ... }
        # On le renvoie tel quel au front
        await self.send(text_data=json.dumps(event["message"]))
