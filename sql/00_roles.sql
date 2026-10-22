-- Roles et base de donnees (a lancer une seule fois avec un compte superutilisateur PostgreSQL) :
--   psql -d postgres -v admin_pwd="'...'" -v app_pwd="'...'" -f sql/00_roles.sql
--
-- Deux roles separes (principe du moindre privilege) :
--   technova_admin : proprietaire de la base, cree les tables et charge le dataset (scripts)
--   technova_app   : utilise par l'API, lecture des employes + ajout/lecture des predictions,
--                    sans droit de modifier ou supprimer l'historique

CREATE ROLE technova_admin LOGIN PASSWORD :admin_pwd;
CREATE ROLE technova_app LOGIN PASSWORD :app_pwd;
CREATE DATABASE technova OWNER technova_admin;
REVOKE ALL ON DATABASE technova FROM PUBLIC;
GRANT CONNECT ON DATABASE technova TO technova_app;
