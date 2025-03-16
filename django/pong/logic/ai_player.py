import asyncio
import websockets
import json
from .game import CANVAS_HEIGHT, CANVAS_WIDTH, PADDLE_SIZE, PADDLE_WIDTH, DEFAULT_PLAYER_TWO_STATE, BALL_RADIUS, PLAYER_SPEED, absadd


class AIPlayer:
    instance_count = 0  # Compteur d'instances (Used to id each playing IA);

    def __init__(self, host, game_id):
        self.ws = f"wss://{host}:8000/ws/game/{game_id}/?player_id=player2&mode=solo"
        AIPlayer.instance_count += 1
        self.ball_position = {'x': 0, 'y': 0, 'dx': 0, 'dy': 0}
        self.paddle_position = {'x': 0, 'y': 0, 'speed': PLAYER_SPEED}
        self.opponent_position = {'x': 0, 'y': 0}
        self.paddle_size = PADDLE_SIZE
        self.running = True
        self.latest_message = None
        self.next_estimation = {'x': 0, 'y':0, 'fbi':0}
        self.lock = asyncio.Lock()
        print(f"Instance AIPlayer créée : ID={AIPlayer.instance_count}", flush=True)

    async def connect(self):
        try:
            async with websockets.connect(self.ws) as websocket:
                print("IA connectée au serveur", flush=True)
                self.websocket = websocket
                listener_task = asyncio.create_task(self.listen(websocket))
                processer_task = asyncio.create_task(self.process())
                done, pending = await asyncio.wait(
                    [listener_task, processer_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                if listener_task in done:
                    print("Arrêt du traitement car WebSocket fermé.", flush=True)
                    self.running = False
                elif processer_task in done:
                    print("Le traitement a terminé en premier, arrêt de l'IA.", flush=True)

                for task in pending:
                    task.cancel()
        except websockets.ConnectionClosed as e:
            print(f"Connexion fermée : {e}", flush=True)
        except Exception as e:
            print(f"Erreur dans la connexion : {e}", flush=True)
        finally:
            self.running = False
            print("Déconnexion propre de l'IA.", flush=True)

    async def listen(self, websocket):
        try:
            async for message in websocket:
                data = json.loads(message)

                if data.get("type") == "game_over":
                    print("Fin de la partie détectée, arrêt de l'IA.", flush=True)
                    self.running = False
                    break
                elif data.get("type") == "position_update":
                    # async with self.lock:
                    self.latest_message = data

        except asyncio.CancelledError:
            print("Réception annulée.", flush=True)
        except Exception as e:
            print(f"Erreur dans receive_data : {e}", flush=True)


    async def process(self):
        while self.running:
            message = None
            time_to_sleep = 0
            # async with self.lock:
            if self.latest_message is not None:
                message = self.latest_message.copy()
                self.latest_message = None
            if message is not None:
                print(f"Traitement des données : {message}", flush=True)
                self.update_positions(message)

                time_to_sleep = await self.define_and_send(self.websocket)
            await asyncio.sleep((time_to_sleep + 1)/ 60)


    def actualise_pos(self, pos):
        pos['x'] += pos['dx']
        if (pos['x'] - BALL_RADIUS <= PADDLE_WIDTH + (CANVAS_WIDTH // 100)):
            pos['x'] += (PADDLE_WIDTH + (CANVAS_WIDTH // 100)) - (pos['x'] - BALL_RADIUS)
            pos['dy'] = 0
            pos['dx'] = absadd(pos['dx'], 1)
            pos['dx'] *= -1
        pos['y'] += pos['dy']
        if (pos['y'] + BALL_RADIUS > CANVAS_HEIGHT):
            pos['y'] -= (pos['y'] + BALL_RADIUS) - CANVAS_HEIGHT
            pos['dy'] *= -1
        elif (pos['y'] - BALL_RADIUS < 0):
            pos['y'] += 0 - (pos['y'] - BALL_RADIUS)
            pos['dy'] *= -1
        return {'x': pos['x'], 'y': pos['y'], 'dx': pos['dx'], 'dy': pos['dy']}


    def update_positions(self, data):
        self.ball_position.update(data["ball_position"])
        self.paddle_position.update(data["player2_state"])
        self.opponent_position.update(data["player1_state"])


    def estimate_next_point(self):
        act_pos = {'x': self.ball_position['x'], 'y': self.ball_position['y'], 'dx': self.ball_position['dx'], 'dy': self.ball_position['dy']}
        for frames in range(60):
            act_pos = self.actualise_pos(act_pos)
            if act_pos['x'] + BALL_RADIUS >= DEFAULT_PLAYER_TWO_STATE['x']:
                self.next_estimation['fbi'] = frames
                self.next_estimation['x'] = act_pos['x']
                self.next_estimation['y'] = act_pos['y']
                return
            if frames >= 59 or act_pos['x'] - BALL_RADIUS <= (CANVAS_WIDTH // 100 ) + PADDLE_WIDTH:
                # return to the center either if opponent has to hit the ball (and i can't predict the trajectory) or if impact will be in more than sixty frames (ans i'll i new information)
                self.next_estimation['fbi'] = frames
                self.next_estimation['x'] = act_pos['x']
                self.next_estimation['y'] = CANVAS_HEIGHT // 2
                return


    async def compute_action(self, websocket):
        paddle_y = self.paddle_position["y"]
        action = []

        ball_y = self.next_estimation["y"]

        if ball_y < paddle_y:
            action.append("move_up")
            diff = (paddle_y + (PADDLE_SIZE // 2)) - ball_y
        elif ball_y > paddle_y + self.paddle_size:
            action.append("move_down")
            diff = ball_y - (paddle_y + (PADDLE_SIZE // 2))
        else:
            action.append(None)
        if action[0] is not None:
            frames_to_reach = int(diff // PLAYER_SPEED) + 1
            action.append(min(frames_to_reach, 59))
            action.append(f"stop_{action[0]}")
        return action


    async def define_and_send(self, websocket):
        self.estimate_next_point()
        actions = await self.compute_action(websocket)
        if actions:
            i = 0
            total_wait = 0
            print(f"Actions envoyées : {actions} \n\n Ball position : {self.ball_position} \n\n Next_estimation : {self.next_estimation}", flush=True)
            while i < len(actions):
                if isinstance(actions[i], int):
                    await asyncio.sleep((actions[i])/ 60)
                    total_wait += actions[i]
                    i += 1
                elif actions is None:
                    continue
                else:
                    await websocket.send(json.dumps({"action": actions[i]}))
                    i += 1
            if total_wait < 60:
                return 60 - total_wait
            else:
                return 0


if __name__ == "__main__":
    ai = AIPlayer()
    asyncio.run(ai.connect())


async def launch_ai(host, game_id):
    ai = AIPlayer(host, game_id)
    await ai.connect()
