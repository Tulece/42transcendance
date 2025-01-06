from django.http import HttpResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import threading
import time

# Constantes
PADDLE_SIZE = 100
PADDLE_WIDTH = 10
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 400
UPDATE_INTERVAL = 1 / 60

DEFAULT_PLAYER_ONE_STATE = {
    'x': CANVAS_WIDTH / 100,
    'y': (CANVAS_HEIGHT / 2) - (PADDLE_SIZE / 2),
    'dy': 0,
    'speed': 3,
}

DEFAULT_PLAYER_TWO_STATE = {
    'x': CANVAS_WIDTH - (CANVAS_WIDTH / 100) - PADDLE_WIDTH,
    'y': (CANVAS_HEIGHT / 2) - (PADDLE_SIZE / 2),
    'dy': 0,
    'speed': 3,
}

DEFAULT_BALL_STATE = {
    'y': CANVAS_HEIGHT / 2,
    'x': CANVAS_WIDTH / 2,
    'dx': -5,
    'dy': 5,
    'radius': 10,
}

# Variables globales pour stocker les positions
players = {
    "player1": DEFAULT_PLAYER_ONE_STATE.copy(),
    "player2": DEFAULT_PLAYER_TWO_STATE.copy(),
}
# player_state = DEFAULT_PLAYER_ONE_STATE.copy()
ball_state = DEFAULT_BALL_STATE.copy()

paused = False
channel_layer = get_channel_layer()

def ball_updater():
        global ball_state, players
        ball_state['x'] += ball_state['dx']
        ball_state['y'] += ball_state['dy']

        players['player1']['y'] += players['player1']['dy']
        if players['player1']['y'] < 0:
            players['player1']['y'] = 0
        if players['player1']['y'] + PADDLE_SIZE > CANVAS_HEIGHT :
            players['player1']['y'] = CANVAS_HEIGHT - PADDLE_SIZE

        if ball_state['x'] - ball_state['radius'] < players['player1']['x'] + PADDLE_WIDTH and ball_state['y'] - ball_state['radius'] <= players['player1']['y'] + PADDLE_SIZE and ball_state['y'] + ball_state['radius'] >= players['player1']['y']:
            ball_state['dx'] *= -1
            ball_state['dx'] += 1
            ball_state['dy'] += 1

        if ball_state['x'] + ball_state['radius'] > players['player2']['x'] and ball_state['y'] - ball_state['radius'] <= players['player2']['y'] + PADDLE_SIZE and ball_state['y'] + ball_state['radius'] >= players['player2']['y']:
            ball_state['dx'] *= -1
            ball_state['dx'] += 1
            ball_state['dy'] += 1

        if ball_state['x'] < ball_state['radius']:
            players['player1']['lifepoints'] -= 1
            reset_game()
        if ball_state['x'] + ball_state['radius'] >= CANVAS_WIDTH:
            players['player2']['lifepoints'] -= 1
            reset_game()

        if ball_state['x'] + ball_state['radius'] > CANVAS_WIDTH or \
            ball_state['x'] - ball_state['radius'] < 0:
            ball_state['dx'] *= -1

        if ball_state['y'] + ball_state['radius'] > CANVAS_HEIGHT or \
            ball_state['y'] - ball_state['radius'] < 0:
            ball_state['dy'] *= -1

def game_launcher(request):
    global CANVAS_WIDTH, CANVAS_HEIGHT, players, ball_state
    players['player1']['lifepoints'] = 5
    players['player1']['y'] = CANVAS_HEIGHT / 2
    players['player1']['x'] = CANVAS_WIDTH / 100
    players['player2']['lifepoint'] = 5
    players['player2']['y'] = CANVAS_HEIGHT / 2
    players['player2']['x'] = CANVAS_WIDTH - (CANVAS_WIDTH / 100)
    ball_state.update(DEFAULT_BALL_STATE)
    return HttpResponse(status=204)

def pause_game():
    global paused
    paused = not paused

def reset_game():
    """
    Réinitialise les positions du paddle et de la balle.
    """
    global players, ball_state
    players['player1'].update(DEFAULT_PLAYER_ONE_STATE)
    players['player2'].update(DEFAULT_PLAYER_TWO_STATE)
    ball_state.update(DEFAULT_BALL_STATE)