1) Connexion SSH
----------------
- Adresse IP : DM insta
- Utilisateur : root
- Mot de passe : DM insta
- Port : 22

Depuis votre machine (Linux/macOS) :

    ssh root@Adresse IP

Saisir le mot de passe lorsqu’il est demandé.

2) Vérifier Docker & Docker Compose
-----------------------------------
Sur le serveur, en SSH :

4) Lancer le projet
-------------------
Se placer à la racine du projet :

    docker compose up -d --build

Cette commande va :
- Lancer le conteneur PostgreSQL (port 5432).
- Lancer le conteneur Django (port 8000, non exposé directement).
- Lancer le conteneur Nginx (ports 80 et 443).
- En mode détaché (`-d`), reconstruction forcée des images (`--build`).

5) Accéder au site
------------------
Une fois que tout est démarré, allez sur :

    http://Adresse IP/

ou :

    https://transcendence.dev/


7) Certificats SSL / Let’s Encrypt
----------------------------------
- Les fichiers `.pem` (par ex. `fullchain.pem`, `privkey.pem`) ne doivent pas être rendus publics.
- Il est conseillé d’utiliser Certbot pour générer/renouveler les certificats :

      apt-get install certbot python3-certbot-nginx
      certbot --nginx -d transcendence.dev

ce qui mettra automatiquement en place les certificats dans `/etc/letsencrypt/live/...`.

8) Ajustements Django
---------------------
- Dans le fichier `django/pong/settings.py`, assurez-vous que :

      ALLOWED_HOSTS = ["transcendence.dev"]

  et, pour le HTTPS :

      CSRF_COOKIE_SECURE = True
      SESSION_COOKIE_SECURE = True
      CSRF_TRUSTED_ORIGINS = ["https://transcendence.dev"]

afin d’éviter les erreurs `DisallowedHost` et les avertissements CSRF.

9) Tips
-------
- Pensez à recompiler (`docker compose up -d --build`) à chaque fois que vous mettez à jour le code.

- Pour l’authentification via 42, configurez `OAUTH42_CLIENT_ID`, `OAUTH42_CLIENT_SECRET`, `OAUTH42_REDIRECT_URI` dans le `.env`.
