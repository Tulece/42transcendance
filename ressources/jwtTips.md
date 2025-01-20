# Commandes utiles pour tester l'authentification JWT dans le projet Django

# Obtenir un token JWT (access et refresh)
curl -X POST http://127.0.0.1:8000/api/token/ \
-H "Content-Type: application/json" \
-d '{"username": "admin", "password": "adminpassword"}'

# Utiliser le token d'access pour accéder à un endpoint protégé
curl -X GET http://127.0.0.1:8000/api/protected/ \
-H "Authorization: Bearer <ACCESS_TOKEN>"

# Renouveler le token d'access avec le token refresh
curl -X POST http://127.0.0.1:8000/api/token/refresh/ \
-H "Content-Type: application/json" \
-d '{"refresh": "<REFRESH_TOKEN>"}'

# Exemple d'utilisation des tokens dans une variable d'environnement
ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -X GET http://127.0.0.1:8000/api/protected/ \
-H "Authorization: Bearer $ACCESS_TOKEN"
