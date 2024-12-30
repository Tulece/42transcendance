import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("WebSocket connected")
        await self.accept()

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected: {close_code}")

    async def receive(self, text_data):
        print(f"Message received: {text_data}")
        try:
            # Vérifier si le message est vide ou non JSON
            if not text_data.strip():
                await self.send(text_data="Erreur : message vide")
                return
            data = json.loads(text_data)
            await self.send(text_data=json.dumps({
                'message': f"Echo: {data.get('message', 'Aucun message')}"
            }))
        except json.JSONDecodeError as e:
            print(f"Erreur JSON: {e}")
            await self.send(text_data="Erreur : message non valide")

