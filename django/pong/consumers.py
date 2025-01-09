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



class PongConsumer(AsyncWebsocketConsumer):
    game_running = False

    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.group_name = f'game_{self.game_id}'
        query_params = parse_qs(self.scope['query_string'].decode('utf-8'))
        self.player_id = query_params.get('player_id', ['unknown'])[0]

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
        # Retirer le channel du groupe
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        # Optionnel : annuler la tâche si tu veux arrêter la partie
        # (mais souvent, on ne le fait qu’après un "quit_game" explicite)
        if hasattr(self, 'game_task') and not self.game_task.done():
            self.game_task.cancel()
            print(f"Annulation de la tâche de jeu pour game_id={self.game_id}")

    async def receive(self, text_data):
        global paused, players
        print(f"Message reçu dans receive : {text_data}", flush=True)
        data = json.loads(text_data)
        action = data.get('action')

        if self.player_id not in players:
            print(f"Joueur {self.player_id} inconnu")
            return

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
            player_state['lifepoints'] = 5
            players["player2"]['lifepoints'] = 5
            # on lance la boucle asynchrone
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

        await self.send(text_data=json.dumps({
            'type': 'position_update',
            'ball_position': {
                'x': ball_state['x'],
                'y': ball_state['y']
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
        while True:
            if not paused:
                ball_updater()
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "update_position"}
                )
                # Vérification des lifepoints
                if players['player1']['lifepoints'] < 1:
                    self.game_running = False
                    await self.channel_layer.group_send(
                        self.group_name,
                        {"type": "game_over", "message": "Game Over! Player1 a perdu."}
                    )
                    break

                elif players['player2']['lifepoints'] < 1:
                    self.game_running = False
                    await self.channel_layer.group_send(
                        self.group_name,
                        {"type": "game_over", "message": "Game Over! Player2 a perdu."}
                    )
                    break
            await asyncio.sleep(1/60)

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
