# Utiliser une image Python légère
FROM python:3.10-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l’application
COPY . .

# Ajouter le script d'entrée
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Exposer le port pour Django
EXPOSE 8000

# Définir le script d'entrée
ENTRYPOINT ["/app/entrypoint.sh"]

# Commande par défaut pour démarrer le serveur
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
