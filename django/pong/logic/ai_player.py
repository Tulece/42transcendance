import asyncio
import websockets
import json
from .game import CANVAS_HEIGHT, CANVAS_WIDTH, PADDLE_SIZE, PADDLE_WIDTH, DEFAULT_PLAYER_TWO_STATE, absadd

SERVER_URL = "ws://localhost:8000/ws/game/1/?player_id=player2&mode=solo"

class AIPlayer:
    instance_count = 0  # Compteur d'instances (Used to id each playing IA);

    def __init__(self):
        AIPlayer.instance_count += 1
        self.ball_position = {'x': 0, 'y': 0, 'dx': 0, 'dy': 0}
        self.paddle_position = {'x': 0, 'y': 0, 'speed': 5}
        self.opponent_position = {'x': 0, 'y': 0}
        self.paddle_size = 100
        self.running = True
        self.next_estimation = {'x': 0, 'y':0, 'fbi':0}
        print(f"Instance AIPlayer créée : ID={AIPlayer.instance_count}", flush=True)

    async def connect(self):
        try:
            async with websockets.connect(SERVER_URL) as websocket:
                print("IA connectée au serveur")
                listener_task = asyncio.create_task(self.listen(websocket))
                await listener_task
        except websockets.ConnectionClosed as e:
            print("Connexion fermée :", e)
        except Exception as e:
            print("Erreur dans la connexion :", e)
        finally:
            self.running = False

    async def listen(self, websocket):
        try:
            async for message in websocket:
                data = json.loads(message)
                print("IA received data:", data, flush=True)
                if data["type"] == "position_update":
                    self.update_positions(data)
                    try:
                        await self.define_and_send(websocket)
                    except Exception as e:
                        print(f"Erreur dans define_and_send : {e}", flush=True)
                elif data["type"] == "game_over":
                    print(data["message"])
                    break
        except websockets.ConnectionClosed as e:
            print("Connexion WebSocket fermée :", e)
        except Exception as e:
            print(f"Erreur dans listen : {e}", flush=True)


    def actualise_pos(self, pos, dx, dy):
        pos['x'] += dx
        if (pos['x'] > CANVAS_WIDTH):
            pos['x'] = CANVAS_WIDTH - (pos['x'] - CANVAS_WIDTH)
            dx *= -1
        elif (pos['x'] < PADDLE_WIDTH + (CANVAS_WIDTH // 100)):
            pos['x'] += (PADDLE_WIDTH + (CANVAS_WIDTH // 100)) - pos['x'] 
            dy = 0
            dx = absadd(dx, 1)
            dx *= -1
        pos['y'] += dy
        if (pos['y'] > CANVAS_HEIGHT):
            pos['y'] = CANVAS_HEIGHT - (pos['y'] - CANVAS_HEIGHT)
            dy *= -1
        elif (pos['y'] < 0):
            pos['y'] = -pos['y']
            dy *= -1
        return {'x': pos['x'], 'y': pos['y']}


    def update_positions(self, data):
        self.ball_position.update(data["ball_position"])
        self.paddle_position.update(data["player1_state"])
        self.opponent_position.update(data["player2_state"])

    def estimate_next_point(self):
        act_pos = {'x': self.ball_position['x'], 'y': self.ball_position['y']}
        for frames in range(60):
            act_pos = self.actualise_pos(act_pos, self.ball_position['dx'], self.ball_position['dy'])
            if act_pos['x'] >= DEFAULT_PLAYER_TWO_STATE['x']:
                self.next_estimation['fbi'] = frames
                self.next_estimation['x'] = act_pos['x']
                self.next_estimation['y'] = act_pos['y']
                return
            if frames == 59:
                self.next_estimation['fbi'] = frames
                self.next_estimation['x'] = act_pos['x']
                self.next_estimation['y'] = CANVAS_HEIGHT // 2

    async def compute_action(self, websocket):
        paddle_y = self.paddle_position["y"]
        action = []

        ball_y = self.next_estimation["y"]
        diff = abs(ball_y - (paddle_y + (PADDLE_SIZE // 2)))
        
        if ball_y < paddle_y + self.paddle_size // 2:
            action.append("move_up")
        elif ball_y > paddle_y + self.paddle_size // 2:
            action.append("move_down")
        else:
            action.append(None)
        if action[0] is not None:
            frames_to_reach = diff // self.paddle_position['speed']
            frames_to_reach += 2 
            action.append(min(frames_to_reach, 59))
            action.append(f"stop_{action[0]}")
        return action

    async def define_and_send(self, websocket):
        self.estimate_next_point()
        actions = await self.compute_action(websocket)
        if actions:
            i = 0
            total_wait = 0
            while i < len(actions):
                if isinstance(actions[i], int) or isinstance(actions[i], float):
                    await asyncio.sleep(actions[i] / 60)
                    total_wait += actions[i]
                    i += 1
                elif actions is None:
                    continue
                else:
                    await websocket.send(json.dumps({"action": actions[i]}))
                    print(f"Action envoyée : {actions[i]}")
                    i += 1
            if total_wait < 60:
                await asyncio.sleep((60 - total_wait) / 60)

if __name__ == "__main__":
    ai = AIPlayer()
    asyncio.run(ai.connect())
    
async def launch_ai():
    ai = AIPlayer()
    await ai.connect()
