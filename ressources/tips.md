# Démarrer le projet
docker-compose up --build

# Arrêter et nettoyer tout
docker ps -q | xargs -r docker stop && docker system prune -a --volumes -f

# Entrer dans un conteneur
docker exec -it <container_name> sh
# Exemple :
docker exec -it django sh

# Afficher les logs d’un conteneur
docker logs -f <container_name>
# Exemple :
docker logs -f django

# Lister tous les conteneurs
docker ps -a

# Redémarrer un conteneur
docker restart <container_name>
# Exemple :
docker restart django

# Supprimer un conteneur
docker rm <container_name>
# Exemple :
docker rm django

# Supprimer une image
docker rmi <image_id>
# Exemple :
docker rmi abc123

# Accéder à PostgreSQL dans Docker
docker exec -it postgres psql -U <username> -d <database>
# Exemple :
docker exec -it postgres psql -U pong_user -d pong_db

# Nettoyer uniquement les volumes
docker volume prune -f
