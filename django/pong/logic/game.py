from django.http import HttpResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import threading
import time

# Constantes
PADDLE_SIZE = 50

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 400

# Variables globales pour stocker les positions
player_position = {
    'y': CANVAS_HEIGHT / 2,
    'x': CANVAS_WIDTH / 12,
}

ball_state = {
    'y': CANVAS_HEIGHT / 2,
    'x': CANVAS_WIDTH / 2,
    'dx': 2,
    'dy': 2,
    'radius': 10,
}

paused = False

UPDATE_INTERVAL = 1 / 60

channel_layer = get_channel_layer()

def ball_updater():
        # Mettre à jour la position de la balle
        ball_state['x'] += ball_state['dx']
        ball_state['y'] += ball_state['dy']

        #Player Collider
        if ball_state['x'] - ball_state['radius'] < player_position['x'] and ball_state['y'] <= player_position['y'] + PADDLE_SIZE and ball_state['y'] >= player_position['y']:
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
    global CANVAS_WIDTH, CANVAS_HEIGHT, player_position, ball_state
    player_position = {
        'y': CANVAS_HEIGHT / 2,
        'x': CANVAS_WIDTH / 12,
    }
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

def move_player_up():
    """Déplace la barre vers le haut."""
    global player_position
    player_position['y'] -= 5  # Déplacer la barre de 10 pixels vers le haut
    if player_position['y'] < 0:
        player_position['y'] = 0  # Empêcher la barre de sortir du canvas

def move_player_down():
    """Déplace la barre vers le bas."""
    global player_position
    player_position['y'] += 5  # Déplacer la barre de 10 pixels vers le haut
    if player_position['y'] + PADDLE_SIZE > CANVAS_HEIGHT :
        player_position['y'] = CANVAS_HEIGHT - PADDLE_SIZE  # Empêcher la barre de sortir du canvas


def reset_game():
    """
    Réinitialise les positions du paddle et de la balle.
    """
    global player_position, ball_state
    player_position = {'x': CANVAS_WIDTH / 12, 'y': CANVAS_HEIGHT / 2}
    ball_state['x'] = CANVAS_WIDTH / 2
    ball_state['y'] = CANVAS_HEIGHT / 2
    ball_state['dx'] = 2
    ball_state['dy'] = 2
