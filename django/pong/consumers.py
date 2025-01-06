from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken
from jwt import decode as jwt_decode
from urllib.parse import parse_qs
from django.conf import settings
import asyncio
import json
from .logic.game import *


class menuConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = None  # Initialisation
        # Décodage et extraction du token depuis le query string
        query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        token = query_params.get('token', [None])[0]
        if not token:
            print("Token manquant, fermeture de la connexion.")
            await self.close(code=4003)
            return

        try:
            # Décodage du token JWT
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


class PongConsumer(AsyncWebsocketConsumer):
    # async def connect(self):
    #     self.username = None  # Initialisation
    #     # Décodage et extraction du token depuis le query string
    #     query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
    #     token = query_params.get('token', [None])[0]
    #     if not token:
    #         print("Token manquant, fermeture de la connexion.")
    #         await self.close(code=4003)
    #         return

    #     try:
    #         # Décodage du token JWT
    #         payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    #         self.username = payload.get('username', 'Anonyme')
    #         print(f"Utilisateur authentifié : {self.username}")
    #         await self.accept()
    #     except InvalidToken as e:
    #         print(f"Token invalide : {e}")
    #         await self.close(code=4003)
    #     except Exception as e:
    #         print(f"Erreur inattendue lors de la validation du token : {e}")
    #         await self.close(code=4003)

    # async def disconnect(self, close_code):
    #     print(f"Déconnecté : {self.username} (code {close_code})")

    # async def receive(self, text_data):
    #     print(f"Message reçu de {self.username}: {text_data}")
    #     await self.send(text_data=f"Echo: {text_data}")

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.group_name = f'game_{self.game_id}'

        # Ajouter le client au groupe
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Retirer le client du groupe
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        print(f"Message reçu dans receive : {text_data}")
        data = json.loads(text_data)
        action = data.get('action')

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
        elif action == 'start_game':
            # On lance la boucle de mise à jour en tâche de fond
            CANVAS_HEIGHT = data.get('height')
            CANVAS_WIDTH = data.get('width')
            self.game_task = asyncio.create_task(self.ball_loop())
        elif action == 'reset_game':
            if self.game_task is not None:
                self.game_task.cancel()  # Annuler la tâche en cours
                try:
                    await self.game_task  # Attendre que la tâche se termine
                except asyncio.CancelledError:
                    pass
            reset_game()
            self.game_task = asyncio.create_task(self.ball_loop())



    async def update_position(self, event):
        """
        Méthode appelée quand le thread envoie {"type": "update_position"}.
        Ici on renvoie la position de la balle et du joueur à ce client.
        """
        # Si tu stockes la logique dans `logic.py` :
        from .logic.game import ball_state, player_state

        await self.send(text_data=json.dumps({
            'type': 'position_update',
            'ball_position': {
                'x': ball_state['x'],
                'y': ball_state['y']
            },
            'player_state': {
                'x': player_state['x'],
                'y': player_state['y']
            }
        }))

    async def start_game(self, event):
        # event = { 'type': 'start_game' } (par exemple)
        # On lance la boucle en tâche de fond (async)
        self.game_task = asyncio.create_task(self.ball_loop())

    async def ball_loop(self):
        global paused, ball_state
        while True:
            if not paused:
                # Mettre à jour la balle
                ball_updater()
                await self.channel_layer.group_send(
                    self.group_name,  # ex: "game_1"
                    {
                        "type": "update_position"
                    }
                )
            # On dort en asynchrone
            await asyncio.sleep(1/60)


    async def game_state(self, event):
        # Envoyer l'état du jeu
        await self.send(text_data=json.dumps(event['state']))
