from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken
from jwt import decode as jwt_decode
from urllib.parse import parse_qs
from django.conf import settings
from datetime import datetime
import asyncio
import json
from .logic.game import *
from .logic.ai_player import launch_ai

class menuConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = None
        query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        token = query_params.get('token', [None])[0]
        if not token:
            print("Token manquant, fermeture de la connexion.")
            await self.close(code=4003)
            return

        try:
            payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            self.username = payload.get('username', 'Anonyme')
            print(f"Utilisateur authentifié : {self.username}")
            await self.accept()
        except InvalidToken as e:
            print(f"Token invalide : {e}")
            await self.close(code=4003)
        except Exception as e:
            print(f"Erreur inattendue lors de la validation du token : {e}")
            await self.close(code=4003)

    async def disconnect(self, close_code):
        print(f"Déconnecté : {self.username} (code {close_code})")

    async def receive(self, text_data):
        print(f"Message reçu de {self.username}: {text_data}")
        await self.send(text_data=f"Echo: {text_data}")



class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        # Check si le user est authentifié
        token = self.scope['query_string'].decode().split('token=')[-1] # Infos sur la co WebSocket (headers, user, query string, etc.)
        try:
            access_token = AccessToken(token)
            self.user = await database_sync_to_async(User.objects.get)(id=access_token['user_id'])
        
        except Exception as e:
            await self.close()
            print(f"Invalid WebSocket connection attempt: {e}")
            return

        try:
            self.blocked_users = await database_sync_to_async(
                lambda: list(self.user.profile.blocked_users.values_list('id', flat=True))
            )  # Liste des IDs des users bloqués
            self.users_who_blocked_me = await database_sync_to_async(
                lambda: list(self.user.blocked_by.values_list('id', flat=True))
            )  # Liste des IDs des users qui ont bloqué ce user

        except Exception as e:
            print(f"Error retrieving blocked users for {self.user.username}: {e}")
            return

        #self.user = self.scope.get('user')
        #if not self.user or not self.user.is_authenticated:
        #    await self.close()
        #    print("Unauthorized WebSocket connection attempt.")
        #    return

        # Nom du groupe général de chat
        self.room_name = 'chat'
        self.room_group_name = f'chat_{self.room_name}'

        # Groupe individuel pour chq user
        self.personal_group = f"user_{self.user.id}"

        # Add le user au groupe Websocket général
        await self.channel_layer.group_add( # Interface pour send des messages entre consommateurs.
            self.room_group_name,
            self.channel_name # ID unique de la co WebSocket
        )

        # Add au groupe perso.
        await self.channel_layer.group_add(
            self.personal_group,
            self.channel_name
        )

        # Accepter la connexion WebSocket
        await self.accept(
            print("WebSocket connection accepted."),
            print(f"User {self.user.username} connected to groups: {self.room_group_name}, {self.personal_group}")
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Retirer du groupe perso.
        await self.channel_layer.group_discard(
            self.personal_group,
            self.channel_name
        )
        print(f"User {self.user.username} disconnected from groups.")


    async def receive(self, text_data):
        try:
            if not text_data:
                await self.send(text_data=json.dumps({"error": "Message vide"}))
                return

            # Convertir les données JSON en dict. Python
            data = json.loads(text_data)
            message = data.get("message")
            target_user_id = data.get("target_user_id") # Id user cible

            if target_user_id: # Gestion message direct
                if int(target_user_id) in self.blocked_users:
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "Vous avez bloqué cet utilisateur."
                    }))
                    return

                if int(target_user_id) in self.users_who_blocked_me:
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "Cet utilisateur vous a bloqué."
                    }))
                    return
                
                
                target_group = f"user_{target_user_id}" # Groupe perso du user cible

                # Send le message au groupe perso du user cible
                await self.channel_layer.group_send(
                    target_group,
                    {
                        "type": "chat_message", # Indique à Django C. quelle méthode utiliser pour gérer l'évent !
                        "message": message,
                        "sender": self.user.username
                    }
                )

            else: # Gestion message de groupe
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message", # Méthode qui reçoit les events diffusés par group_send et les envoie au client
                        "message": message,
                        "sender": self.user.username
                    }
                )
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e}")
            await self.send(text_data=json.dumps({
                "error": "Invalid JSON format"
            }))
        
    async def chat_message(self, event):
        message = event['message']
        sender = event.get('sender', 'Anonymous')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Envoyer le message diffusé au WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message,
            'sender': sender,
            'timestamp': timestamp
         }))


class PongConsumer(AsyncWebsocketConsumer):
    game_running = False

    async def connect(self):
        global players
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        human_group_name = f'game_{self.game_id}_humans'
        ai_group_name = f'game_{self.game_id}_ai'
        query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        self.player_id = query_params.get('player_id', ['unknown'])[0]

        mode = query_params.get('mode', ['multi'])[0]
        if self.player_id == "player2" and mode == 'solo':
            self.is_ai = True
            self.group_name = ai_group_name
        else:
            self.is_ai = False
            self.group_name = human_group_name

        # Initialiser l'état du joueur s'il n'existe pas
        if self.player_id not in players:
            if self.player_id == "player1":
                players[self.player_id] = DEFAULT_PLAYER_ONE_STATE.copy()
            elif self.player_id == "player2":
                players[self.player_id] = DEFAULT_PLAYER_TWO_STATE.copy()
            else:
                print(f"ID de joueur non valide : {self.player_id}")
                await self.close()
                return

        # Ajouter le client au groupe
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        print(f"Joueur {self.player_id} connecté au jeu {self.game_id}")


    async def disconnect(self, close_code):
        global players
        print(f"Déconnexion du joueur {self.player_id}", flush=True)

        # Supprimer l'état du joueur
        # if self.player_id in players:
        #     del players[self.player_id]

        # Arrêter la boucle si le joueur est celui qui l'a lancée
        if hasattr(self, 'game_task') and not self.game_task.done():
            self.game_task.cancel()
            print(f"Boucle de jeu arrêtée pour {self.player_id}")

        # Retirer le client du groupe WebSocket
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        # Optionnel : annuler la tâche si tu veux arrêter la partie
        # (mais souvent, on ne le fait qu’après un "quit_game" explicite)
        # if hasattr(self, 'game_task') and not self.game_task.done():
        #     self.game_task.cancel()
        #     print(f"Annulation de la tâche de jeu pour game_id={self.game_id}")

    async def receive(self, text_data):
        global paused, players
        data = json.loads(text_data)
        action = data.get('action')

        if self.player_id not in players:
            print(f"Joueur {self.player_id} inconnu")
            return
        print(f"Message reçu dans receive : {text_data}, by player : {self.player_id}", flush=True)

        player_state = players[self.player_id]

        if action == 'move_up':
            player_state['dy'] = -player_state['speed']
        elif action == 'move_down':
            player_state['dy'] = player_state['speed']
        elif action == 'stop_move_down' and player_state['dy'] == player_state['speed']:
            player_state['dy'] = 0
        elif action == 'stop_move_up' and player_state['dy'] == -player_state['speed']:
            player_state['dy'] = 0

        elif action == 'pause_game':
            paused = not paused

        elif action == 'start_game' and self.game_running == False:
            self.game_running = True
            mode = data.get('mode')
            print(f"Mode = {mode}", flush = True)
            if mode == 'solo':
                asyncio.create_task(launch_ai())
            player_state['lifepoints'] = 5
            players["player2"]['lifepoints'] = 5
            await self.channel_layer.group_send(
                f'game_{self.game_id}_ai',
                {
                    "type": "update_position"
                }
            )
            self.game_task = asyncio.create_task(self.ball_loop())

        elif action == 'reset_game':
            reset_game()
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "update_position"}
            )

        elif action == 'quit_game':
            # Nouveau bloc pour stopper la partie côté serveur
            print("Action quit_game reçue => arrêt de la partie côté serveur", flush=True)
            self.game_running = False
            # Annuler la boucle si elle tourne
            if hasattr(self, 'game_task') and not self.game_task.done():
                self.game_task.cancel()
                print("Tâche de jeu annulée (quit_game).", flush=True)

            # On peut éventuellement envoyer un message "game_over"
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "game_over",
                    "message": "Partie quittée."
                }
            )

    async def update_position(self, event):
        global ball_state, players
        player_state = players[self.player_id]
        opponent_state = None

        for player_id, state in players.items():
            if player_id != self.player_id:
                opponent_state = state
                break

        # print(f"Player {self.player_id}: x={player_state['x']}, y={player_state['y']}, lifepoints={player_state['lifepoints']}")
        # if opponent_state:
        #     print(f"Opponent: x={opponent_state['x']}, y={opponent_state['y']}, lifepoints={opponent_state['lifepoints']}")

        await self.send(text_data=json.dumps({
            'type': 'position_update',
            'ball_position': {
                'x': ball_state['x'],
                'y': ball_state['y'],
                'dy': ball_state['dy'],
                'dx': ball_state['dx'],
            },
            'player_state': {
                'x': player_state['x'],
                'y': player_state['y'],
                'lifepoints': player_state['lifepoints'],
            },
            'opponent_state': {
                'x': opponent_state['x'],
                'y': opponent_state['y'],
                'lifepoints': opponent_state['lifepoints'],
            }
        }))


    async def start_game(self, event):
        # Cette méthode est un exemple si tu utilises un "type": "start_game" dans un group_send
        self.game_task = asyncio.create_task(self.ball_loop())

    async def ball_loop(self):
        global paused, ball_state, players
        count = 0
        try:
            while self.game_running:
                if not paused:
                    count += 1
                    ball_updater()
                    if "human" in self.group_name or count == 60:
                        await self.channel_layer.group_send(
                            self.group_name,
                            {"type": "update_position"}
                        )
                        
                        if count == 60 :
                            await self.channel_layer.group_send(
                                f'game_{self.game_id}_ai',
                                {"type": "update_position"}
                            )
                            print("Message sent to group : ", self.group_name)
                            count = 0
                    if players['player1']['lifepoints'] < 1 or players['player2']['lifepoints'] < 1:
                        self.game_running = False
                        message = "Game Over! Vous avez perdu." if players['player1']['lifepoints'] < 1 else "Congrats! You win."
                        await self.channel_layer.group_send(
                            self.group_name,
                            {"type": "game_over", "message": message}
                        )
                        break
                await asyncio.sleep(1 / 60)
        except asyncio.CancelledError:
            print("Boucle de jeu annulée.")


    async def game_over(self, event):
        """
        Méthode appelée pour gérer la fin du jeu.
        """
        await self.send(text_data=json.dumps({
            "type": "game_over",
            "message": event["message"]
        }))

    async def game_state(self, event):
        # Si besoin, une méthode pour transmettre l'état complet
        await self.send(text_data=json.dumps(event['state']))


