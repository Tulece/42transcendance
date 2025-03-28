import asyncio
import time
import math
import random
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from ..models import SimpleMatch, CustomUser
import json

# Constantes
PADDLE_SIZE = 70
PADDLE_WIDTH = 10
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 400
BALL_RADIUS = 5
UPDATE_INTERVAL = 1 / 60
PLAYER_SPEED = 8

DEFAULT_PLAYER_ONE_STATE = {
    'x': CANVAS_WIDTH / 100,
    'y': (CANVAS_HEIGHT / 2) - (PADDLE_SIZE / 2),
    'dy': 0,
    'speed': PLAYER_SPEED,
}

DEFAULT_PLAYER_TWO_STATE = {
    'x': CANVAS_WIDTH - (CANVAS_WIDTH / 100) - PADDLE_WIDTH,
    'y': (CANVAS_HEIGHT / 2) - (PADDLE_SIZE / 2),
    'dy': 0,
    'speed': PLAYER_SPEED,
}

DEFAULT_BALL_STATE = {
    'x': CANVAS_WIDTH / 2,
    'y': CANVAS_HEIGHT / 2,
    'dx': 5,
    'dy': 5,
    'radius': BALL_RADIUS,
}

def absadd(number, n):
    return number - n if number < 0 else number + n

class Game:
    def __init__(self, game_id, player1, player2 = None):
        self.game_id = game_id
        self.game_over = False
        self.players = {
            "player1": {
                **DEFAULT_PLAYER_ONE_STATE,
                'lifepoints': 5,
                'disconnected': False,
                'connected': False,
            },
            "player2": {
                **DEFAULT_PLAYER_TWO_STATE,
                'lifepoints': 5,
                'disconnected': False,
                'connected': False,
            },
        }
        self.ball_state = DEFAULT_BALL_STATE.copy()
        self.paused = False
        self.running = False
        self.resetting = False
        self.waiting_countdown = 0
        self.channel_layer = get_channel_layer()
        self.ignore_match_act = False


    @classmethod
    async def create(cls, game_id, player1, player2=None):
        game = cls(game_id, player1, player2)
        await game.create_match_entry(player1, player2, game_id)
        return game


    @database_sync_to_async
    def create_match_entry(self, player1, player2, game_id):

        try:
            user1 = CustomUser.objects.get(username=player1)
        except CustomUser.DoesNotExist:
            raise ValueError(f"User {player1} does not exist")

        user2 = None
        if player2:
            try:
                user2 = CustomUser.objects.get(username=player2)
            except CustomUser.DoesNotExist:
                raise ValueError(f"User {player2} does not exist")

        SimpleMatch.objects.create(
            player1=user1,
            player2=user2,
            game_id=game_id
        )



    async def start(self):
        self.running = True
        self.reset_pos()
        try:
            while self.running:
                start_time = time.perf_counter()
                if not self.paused:
                    self.update_game_state()
                await self.send_game_state()
                elapsed = time.perf_counter() - start_time
                sleep_time = UPDATE_INTERVAL - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            print(f"Game {self.game_id} annulée.", flush=True)

    def stop(self):
        self.running = False

    def update_game_state(self):
        if (not self.players["player1"]["connected"] or (not self.players["player2"]["connected"] and not self.game_id.startswith("aaaa"))):
            return

        if (self.players['player1']['lifepoints'] <= 0 or
            self.players['player2']['lifepoints'] <= 0 or
            self.players['player1']['disconnected'] or
            self.players['player2']['disconnected']):
            self.game_over = True
        elif self.resetting:
            self.send_game_state()
            self.resetting = False
            self.paused = False
        else:
            self.ball_updater()


    async def send_game_state(self):
        if (not self.players["player1"]["connected"] or (not self.players["player2"]["connected"] and not self.game_id.startswith("aaaa"))):
             await self.channel_layer.group_send(
                 self.game_id,
                 {
                     "type": "game_update",
                     "message": {
                         "type": "waiting",
                         "message": "En attente de l'adversaire"
                     }
                 }
             )
             await asyncio.sleep(UPDATE_INTERVAL)
             return

        if self.game_over:
             if self.players['player1']['lifepoints'] <= 0:
                 reason, player = "lifepoints", "player1"
             elif self.players['player2']['lifepoints'] <= 0:
                 reason, player = "lifepoints", "player2"
             elif self.players['player1']['disconnected']:
                 reason, player = "disconnected", "player1"
             elif self.players['player2']['disconnected']:
                 reason, player = "disconnected", "player2"
             else:
                 reason, player = "Unknown", "Unknown"
             if not self.ignore_match_act:
                await self.register_match_winner(player, self.game_id)
                self.ignore_match_act = True
             await self.channel_layer.group_send(
                 self.game_id,
                 {
                     "type": "game_update",
                     "message": {
                         "type": "game_over",
                         "message": f"{player} {reason}"
                     }
                 }
             )
             if not self.ignore_match_act:
                await self.register_match_winner(player, self.game_id)
             self.stop()
             return
        elif self.resetting:
             for i in range(3, 0, -1):
                 await self.channel_layer.group_send(
                     self.game_id,
                     {
                         "type": "game_update",
                         "message": {
                             "type": "waiting",
                             "message": f"{i}"
                         }
                     }
                 )
                 await asyncio.sleep(1)
             self.resetting = False
             self.paused = False
        elif not self.paused:
             await self.channel_layer.group_send(
                 self.game_id,
                 {
                     "type": "game_update",
                     "message": {
                         "type": "position_update",
                         "ball_position": {
                             "x": self.ball_state["x"],
                             "y": self.ball_state["y"],
                             "dx": self.ball_state["dx"],
                             "dy": self.ball_state["dy"],
                         },
                         "player1_state": {
                             "x": self.players["player1"]["x"],
                             "y": self.players["player1"]["y"],
                             "lifepoints": self.players["player1"]["lifepoints"],
                         },
                         "player2_state": {
                             "x": self.players["player2"]["x"],
                             "y": self.players["player2"]["y"],
                             "lifepoints": self.players["player2"]["lifepoints"],
                         },
                     },
                 }
             )

    @database_sync_to_async
    def set_match_winner(self, game_id, loser):
        try:
            match = SimpleMatch.objects.get(game_id=game_id)
            if match.winner is None:
                match.winner = "Player 1" if loser == "player2" else "Player 2"
                match.save()
            else:
                print("Le match a déjà un vainqueur.")
        except SimpleMatch.DoesNotExist:
            print("Match introuvable dans la DB.")


    async def register_match_winner(self, loser, game_id):
        await self.set_match_winner(game_id, loser)


    async def send_game_over(self, reason, player):
        await self.channel_layer.group_send(
            self.game_id,
            {
                "type": "game_update",
                "message": {
                    "type": "game_over",
                    "message": f"{player} {reason}"
                }
            }
        )

    def handle_player_action(self, player_id, action):
        if player_id not in self.players:
            return
        player_state = self.players[player_id]
        if action == "move_up":
            player_state["dy"] = -player_state["speed"]
        elif action == "move_down":
            player_state["dy"] = player_state["speed"]
        elif (action == "stop_move_down" and player_state["dy"] > 0) or (action == "stop_move_up" and player_state["dy"] < 0):
            player_state["dy"] = 0
        elif action == "pause_game":
            self.paused = not self.paused

    def handle_player_disconnect(self, player_id):
        if player_id not in self.players:
            print("handle_player_disconnect : mauvais player_id", flush=True)
            return
        self.players[player_id]['disconnected'] = True

    def set_player_connected(self, player_id):
        if player_id in self.players:
            self.players[player_id]['connected'] = True
            print(f"[Game {self.game_id}] {player_id} CONNECTÉ !", flush=True)
        else:
            print(f"[Game {self.game_id}] Erreur : {player_id} non trouvé", flush=True)

    def reset_pos(self):
        pos1 = DEFAULT_PLAYER_ONE_STATE.copy()
        pos2 = DEFAULT_PLAYER_TWO_STATE.copy()
        self.players['player1']['x'] = pos1['x']
        self.players['player1']['y'] = pos1['y']
        self.players['player1']['dy'] = pos1['dy']
        self.players['player2']['x'] = pos2['x']
        self.players['player2']['y'] = pos2['y']
        self.players['player2']['dy'] = pos2['dy']
        self.ball_state.update(DEFAULT_BALL_STATE)
        self.randomize_ball_direction()
        asyncio.create_task(self.countdown_task(3))

    async def countdown_task(self, countdown_seconds=3):
        self.waiting_countdown = countdown_seconds
        self.paused = True
        self.resetting = True
        while self.waiting_countdown > 0:
            await asyncio.sleep(1)
            self.waiting_countdown -= 1
        self.resetting = False
        self.paused = False

    def randomize_ball_direction(self):
        if math.floor(random.random() * 2):
            self.ball_state['dx'] *= -1
        if math.floor(random.random() * 2):
            self.ball_state['dy'] *= -1

    def ball_updater(self):
        ball_state = self.ball_state
        players = self.players

        ball_state['x'] += ball_state['dx']
        ball_state['y'] += ball_state['dy']

        players['player1']['y'] += players['player1']['dy']
        if players['player1']['y'] < 0:
            players['player1']['y'] = 0
        if players['player1']['y'] + PADDLE_SIZE > CANVAS_HEIGHT:
            players['player1']['y'] = CANVAS_HEIGHT - PADDLE_SIZE

        players['player2']['y'] += players['player2']['dy']
        if players['player2']['y'] < 0:
            players['player2']['y'] = 0
        if players['player2']['y'] + PADDLE_SIZE > CANVAS_HEIGHT:
            players['player2']['y'] = CANVAS_HEIGHT - PADDLE_SIZE

        # Collision avec la raquette du joueur 1
        if (ball_state['x'] - ball_state['radius'] < players['player1']['x'] + PADDLE_WIDTH and
            ball_state['y'] - ball_state['radius'] <= players['player1']['y'] + PADDLE_SIZE and
            ball_state['y'] + ball_state['radius'] >= players['player1']['y']):
            ball_state['x'] += (players['player1']['x'] + PADDLE_WIDTH) - ((ball_state['x'] - ball_state['radius']) - (players['player1']['x'] + PADDLE_WIDTH))
            ball_state['dx'] = absadd(ball_state['dx'], 1)
            if ball_state['y'] < players['player1']['y'] + PADDLE_SIZE / 8:
                ball_state['dy'] = abs(ball_state['dx']) * -1
            elif ball_state['y'] < players['player1']['y'] + (2 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = (abs(ball_state['dx']) // 2) * -1
            elif ball_state['y'] < players['player1']['y'] + (3 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = (abs(ball_state['dx']) // 4) * -1
            elif ball_state['y'] < players['player1']['y'] + (5 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = 0
            elif ball_state['y'] < players['player1']['y'] + (6 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = abs(ball_state['dx']) // 4
            elif ball_state['y'] < players['player1']['y'] + (7 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = abs(ball_state['dx']) // 2
            else:
                ball_state['dy'] = abs(ball_state['dx'])
            ball_state['dx'] *= -1

        # Collision avec la raquette du joueur 2
        if (ball_state['x'] + ball_state['radius'] > players['player2']['x'] and
            ball_state['y'] - ball_state['radius'] <= players['player2']['y'] + PADDLE_SIZE and
            ball_state['y'] + ball_state['radius'] >= players['player2']['y']):
            ball_state['x'] -= (ball_state['x'] + ball_state['radius']) - players['player2']['x']
            ball_state['dx'] = absadd(ball_state['dx'], 1)
            if ball_state['y'] < players['player2']['y'] + PADDLE_SIZE / 8:
                ball_state['dy'] = abs(ball_state['dx']) * -1
            elif ball_state['y'] < players['player2']['y'] + (2 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = (abs(ball_state['dx']) // 2) * -1
            elif ball_state['y'] < players['player2']['y'] + (3 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = (abs(ball_state['dx']) // 4) * -1
            elif ball_state['y'] < players['player2']['y'] + (5 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = 0
            elif ball_state['y'] < players['player2']['y'] + (6 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = abs(ball_state['dx']) // 4
            elif ball_state['y'] < players['player2']['y'] + (7 * (PADDLE_SIZE / 8)):
                ball_state['dy'] = abs(ball_state['dx']) // 2
            else:
                ball_state['dy'] = abs(ball_state['dx'])
            ball_state['dx'] *= -1

        if ball_state['x'] < ball_state['radius']:
            players['player1']['lifepoints'] -= 1
            if players['player1']['lifepoints'] > 0:
                self.reset_pos()
        if ball_state['x'] + ball_state['radius'] >= CANVAS_WIDTH:
            players['player2']['lifepoints'] -= 1
            if players['player2']['lifepoints'] > 0:
                self.reset_pos()

        if ball_state['y'] + ball_state['radius'] > CANVAS_HEIGHT:
            ball_state['y'] -= (ball_state['y'] + ball_state['radius']) - CANVAS_HEIGHT
            ball_state['dy'] *= -1
        if ball_state['y'] - ball_state['radius'] < 0:
            ball_state['y'] = abs(ball_state['y'] - ball_state['radius'])
            ball_state['dy'] *= -1

def absadd(number, n):
    return number - n if number < 0 else number + n
