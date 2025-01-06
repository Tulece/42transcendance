from django.http import HttpResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import threading
import time

# Constantes
PADDLE_SIZE = 100
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 400
UPDATE_INTERVAL = 1 / 60

# Variables globales pour stocker les positions
player_state = {
    'y': CANVAS_HEIGHT / 2,
    'x': CANVAS_WIDTH / 100,
    'dy': 0,
    'speed': 3,
}

ball_state = {
    'y': CANVAS_HEIGHT / 2,
    'x': CANVAS_WIDTH / 2,
    'dx': 2,
    'dy': 2,
    'radius': 10,
}

paused = False
channel_layer = get_channel_layer()

def ball_updater():
        # Mettre à jour la position de la balle
        ball_state['x'] += ball_state['dx']
        ball_state['y'] += ball_state['dy']

        player_state['y'] += player_state['dy']
        if player_state['y'] < 0:
            player_state['y'] = 0
        if player_state['y'] + PADDLE_SIZE > CANVAS_HEIGHT :
            player_state['y'] = CANVAS_HEIGHT - PADDLE_SIZE

        #Player Collider
        if ball_state['x'] - ball_state['radius'] < player_state['x'] and ball_state['y'] <= player_state['y'] + PADDLE_SIZE and ball_state['y'] >= player_state['y']:
            ball_state['dx'] *= -1
            ball_state['dx'] += 1
            ball_state['dy'] += 1

        # Gérer les collisions avec les murs
        if ball_state['x'] + ball_state['radius'] > CANVAS_WIDTH or \
            ball_state['x'] - ball_state['radius'] < 0:
            ball_state['dx'] *= -1

        if ball_state['y'] + ball_state['radius'] > CANVAS_HEIGHT or \
            ball_state['y'] - ball_state['radius'] < 0:
            ball_state['dy'] *= -1

def game_launcher(request):
    global CANVAS_WIDTH, CANVAS_HEIGHT, player_state, ball_state
    player_state['y'] = CANVAS_HEIGHT / 2
    player_state['x'] = CANVAS_WIDTH / 100,
    ball_state = {
        'y': CANVAS_HEIGHT / 2,
        'x': CANVAS_WIDTH / 2,
        'dx': 2,
        'dy': 2,
        'radius': 10,
    }
    return HttpResponse(status=204)

def pause_game():
    global paused
    paused = not paused

def reset_game():
    """
    Réinitialise les positions du paddle et de la balle.
    """
    global player_state, ball_state
    player_state = {'x': CANVAS_WIDTH / 100, 'y': CANVAS_HEIGHT / 2, 'dy': 0, 'speed': 3}
    ball_state['x'] = CANVAS_WIDTH / 2
    ball_state['y'] = CANVAS_HEIGHT / 2
    ball_state['dx'] = 2
    ball_state['dy'] = 2
