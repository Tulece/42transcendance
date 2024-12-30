from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken
from jwt import decode as jwt_decode
from urllib.parse import parse_qs
from django.conf import settings

class PongConsumer(AsyncWebsocketConsumer):
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
