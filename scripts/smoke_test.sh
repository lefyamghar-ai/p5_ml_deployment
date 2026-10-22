#!/usr/bin/env bash
# Test de fumee d'une API deployee : sante, prediction, securite, tracabilite en base.
# Usage : API_KEY=... BASE_URL=http://localhost:8000 scripts/smoke_test.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
: "${API_KEY:?API_KEY doit etre defini}"
EMPLOYE='{"age": 41, "genre": "F", "revenu_mensuel": 5993, "statut_marital": "Célibataire",
  "departement": "Commercial", "poste": "Cadre Commercial", "nombre_experiences_precedentes": 8,
  "annee_experience_totale": 8, "annees_dans_le_poste_actuel": 4, "satisfaction_employee_environnement": 2,
  "note_evaluation_precedente": 3, "niveau_hierarchique_poste": 2, "satisfaction_employee_nature_travail": 4,
  "satisfaction_employee_equipe": 1, "satisfaction_employee_equilibre_pro_perso": 1, "note_evaluation_actuelle": 3,
  "heure_supplementaires": "Oui", "augementation_salaire_precedente": 11, "nombre_participation_pee": 0,
  "nb_formations_suivies": 0, "distance_domicile_travail": 1, "niveau_education": 2,
  "domaine_etude": "Infra & Cloud", "frequence_deplacement": "Occasionnel", "annees_depuis_la_derniere_promotion": 0}'

echo "Attente de l'API sur $BASE_URL ..."
for _ in $(seq 1 60); do
  if [ "$(curl -fs "$BASE_URL/health" | jq -r .status 2>/dev/null)" = "ok" ]; then break; fi
  sleep 2
done
curl -fs "$BASE_URL/health" | jq -e '.status == "ok" and .model_loaded and .database' > /dev/null \
  || { echo "ECHEC : /health n'est pas ok"; curl -s "$BASE_URL/health"; exit 1; }
echo "OK  /health"

code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

[ "$(code -X POST "$BASE_URL/predict" -H 'Content-Type: application/json' -d "$EMPLOYE")" = 401 ] \
  || { echo "ECHEC : /predict sans cle devrait renvoyer 401"; exit 1; }
echo "OK  /predict sans cle -> 401"

[ "$(code -X POST "$BASE_URL/predict" -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' \
  -d '{"age": 15}')" = 422 ] || { echo "ECHEC : donnees invalides devraient renvoyer 422"; exit 1; }
echo "OK  /predict invalide -> 422"

REPONSE=$(curl -fs -X POST "$BASE_URL/predict" -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' \
  -d "$EMPLOYE")
ID=$(echo "$REPONSE" | jq -e .prediction_id)
echo "OK  /predict -> $(echo "$REPONSE" | jq -c '{probabilite_depart, label}')"

curl -fs "$BASE_URL/predictions/$ID" -H "X-API-Key: $API_KEY" | jq -e ".prediction_id == $ID" > /dev/null \
  || { echo "ECHEC : la prediction $ID n'est pas retrouvee en base"; exit 1; }
echo "OK  prediction $ID enregistree en base"

curl -fs "$BASE_URL/employees/1" -H "X-API-Key: $API_KEY" | jq -e '.id_employee == 1' > /dev/null \
  || { echo "ECHEC : dataset absent de la base"; exit 1; }
echo "OK  dataset charge en base"

echo "Test de fumee reussi"
