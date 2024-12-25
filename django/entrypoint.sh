#!/bin/sh

# Attendre que la base de données soit prête
until nc -z "$POSTGRES_HOST" 5432; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 1
done

# Appliquer les migrations
echo "Applying database migrations..."
python manage.py migrate

# Créer le superutilisateur
echo "Creating superuser if not exists..."
python manage.py shell <<EOF
from django.contrib.auth.models import User
import os

username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'adminpassword')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser {username} created successfully.")
else:
    print(f"Superuser {username} already exists.")
EOF

# Lancer le serveur
exec "$@"
