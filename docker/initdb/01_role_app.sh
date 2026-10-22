#!/bin/sh
# Execute une seule fois par l'image postgres, a la creation du volume de donnees.
# Cree le role applicatif (moindre privilege) ; ses droits sur les tables sont donnes par create_db.py.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v app_pwd="$POSTGRES_APP_PASSWORD" <<'EOSQL'
CREATE ROLE technova_app LOGIN PASSWORD :'app_pwd';
REVOKE ALL ON DATABASE technova FROM PUBLIC;
GRANT CONNECT ON DATABASE technova TO technova_app;
EOSQL
