# Basé sur l'image officielle de PostgreSQL
FROM postgres:15

# Copier les scripts d'initialisation
COPY ./init.sql /docker-entrypoint-initdb.d/
