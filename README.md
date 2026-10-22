# Futurisys — Déploiement du modèle de prédiction d'attrition (TechNova)

Projet 5 OpenClassrooms : mettre en production le modèle du projet 4 (TechNova Partners),
qui estime le risque de démission d'un employé à partir de ses données RH.

Objectifs :

- exposer le modèle via une API **FastAPI** documentée (Swagger) ;
- enregistrer chaque prédiction (entrée et sortie) dans **PostgreSQL** ;
- tester le code avec **Pytest** et mesurer la couverture ;
- automatiser les tests avec **GitHub Actions**.

## Le modèle

| Élément | Valeur |
|---|---|
| Algorithme | `RandomForestClassifier` (200 arbres, `max_depth=4`, `min_samples_leaf=5`, `class_weight="balanced"`) |
| Données | 1 470 employés, 16,12 % de départs (SIRH + évaluations + sondage) |
| Entrée | 25 caractéristiques brutes d'un employé → 39 variables après encodage one-hot |
| Seuil de décision | 0,435, choisi en validation croisée (max F2 : le rappel compte deux fois plus que la précision) |
| Performances (test, 294 employés) | rappel 0,83 · précision 0,36 · F2 0,66 · ROC AUC 0,79 (39 départs détectés sur 47) |

Le fichier `app/ml/model.joblib` contient le modèle, la liste des colonnes, le seuil, les modalités
attendues pour chaque variable qualitative, la version et les métriques de test.
Il se régénère à l'identique (mêmes réglages et même découpage train/test qu'au projet 4) avec :

```bash
python scripts/export_model.py
```

Le prétraitement (`app/ml/preprocessing.py`) reproduit exactement celui du projet 4 : il produit les mêmes
39 colonnes que `etape_2_X.csv`, aussi bien sur tout le dataset que pour un seul employé à la fois (cas de l'API).

## Structure du dépôt

```text
.
├── app/                  # Code de l'application (API, modèle, base de données)
│   ├── main.py           # API FastAPI (endpoints)
│   ├── schemas.py        # Schémas Pydantic (validation entrée / sortie)
│   ├── config.py         # Configuration lue dans l'environnement (.env)
│   └── ml/
│       ├── predictor.py      # Chargement du modèle et prédiction
│       ├── preprocessing.py  # Transformation données brutes -> variables du modèle
│       └── model.joblib      # Modèle exporté
├── data/
│   ├── raw/              # 3 fichiers sources du projet 4
│   └── employes.csv      # Données fusionnées (1 470 employés)
├── scripts/
│   └── export_model.py   # Entraîne et exporte le modèle
├── requirements.txt      # Dépendances d'exécution
├── requirements-dev.txt  # + tests, couverture, lint
├── ruff.toml             # Standards de code (vérifiés par ruff)
└── .env.example          # Variables d'environnement (modèle du .env)
```

## Installation

Prérequis : Python 3.13 et PostgreSQL 17.

```bash
git clone https://github.com/lefyamghar-ai/p5_ml_deployment.git
cd p5_ml_deployment
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # puis renseigner les vraies valeurs
```

## Lancer l'API

```bash
uvicorn app.main:app --reload
```

Documentation interactive (Swagger) : http://localhost:8000/docs, ou ReDoc sur `/redoc`.

| Méthode | Endpoint | Rôle | Clé API |
|---|---|---|---|
| GET | `/health` | État de l'API et du modèle | non |
| GET | `/model/info` | Version, seuil, métriques de test, modalités acceptées | non |
| POST | `/predict` | Prédiction pour un employé | oui |
| POST | `/predict/batch` | Prédiction pour 1 à 100 employés | oui |

Exemple :

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"age": 41, "genre": "F", "revenu_mensuel": 5993, "statut_marital": "Célibataire",
       "departement": "Commercial", "poste": "Cadre Commercial", "nombre_experiences_precedentes": 8,
       "annee_experience_totale": 8, "annees_dans_le_poste_actuel": 4,
       "satisfaction_employee_environnement": 2, "note_evaluation_precedente": 3,
       "niveau_hierarchique_poste": 2, "satisfaction_employee_nature_travail": 4,
       "satisfaction_employee_equipe": 1, "satisfaction_employee_equilibre_pro_perso": 1,
       "note_evaluation_actuelle": 3, "heure_supplementaires": "Oui",
       "augementation_salaire_precedente": 11, "nombre_participation_pee": 0, "nb_formations_suivies": 0,
       "distance_domicile_travail": 1, "niveau_education": 2, "domaine_etude": "Infra & Cloud",
       "frequence_deplacement": "Occasionnel", "annees_depuis_la_derniere_promotion": 0}'
```

Réponse :

```json
{"probabilite_depart": 0.5445, "prediction": 1, "label": "depart_probable", "seuil": 0.4349, "model_version": "1.0.0"}
```

### Validation des données (Pydantic)

Toute donnée non conforme est refusée avec un code **422** qui indique le champ en cause :

- champ manquant, champ inconnu ou mauvais type ;
- valeur hors bornes (âge 18–70, notes de satisfaction et d'évaluation 1–4, niveau 1–5, augmentation 0–100 %…) ;
- modalité inconnue pour une variable qualitative (ex. un `poste` absent des données d'entraînement) :
  le modèle l'encoderait sans prévenir comme la catégorie de référence, elle est donc refusée ;
- incohérence entre champs (ex. plus d'années dans le poste que d'années d'expérience).

### Authentification et sécurité

- Les endpoints de prédiction exigent l'en-tête `X-API-Key` dès que la variable `API_KEY` est définie
  (réponse **401** sinon). Sans `API_KEY` (développement local), l'accès est libre.
- La clé est comparée en temps constant (`secrets.compare_digest`).
- Aucun secret dans le code : `API_KEY` vient du `.env` (ignoré par Git) ou des secrets GitHub.

## Standards de code

- Style et imports vérifiés par [ruff](https://docs.astral.sh/ruff/) (`ruff check .`), règles dans `ruff.toml`.
- Versions des dépendances figées dans `requirements.txt` ; `scikit-learn`, `numpy` et `pandas` aux versions
  du projet 4, car le modèle exporté en dépend.
- Aucun secret dans le code : tout passe par des variables d'environnement (`.env`, jamais commité).

## Conventions Git

**Branches**

| Branche | Rôle |
|---|---|
| `main` | Code stable, livré. Chaque version est taguée. |
| `develop` | Intégration des fonctionnalités terminées. |
| `feature/<sujet>` | Une fonctionnalité (ex. `feature/api`, `feature/database`), créée depuis `develop`. |
| `fix/<sujet>` | Correction de bug. |

Chaque branche `feature/*` est relue et fusionnée dans `develop` par une **Pull Request** ;
`develop` est fusionnée dans `main` pour une livraison.

**Commits** : format [Conventional Commits](https://www.conventionalcommits.org/fr/),
par exemple `feat: ajoute l'endpoint /predict`, `fix: ...`, `test: ...`, `docs: ...`, `chore: ...`, `ci: ...`.

**Versions** : tags [SemVer](https://semver.org/lang/fr/) sur `main` (`v0.1.0`, `v0.2.0`, … `v1.0.0`).

## Avancement

- [x] Structure du dépôt, dépendances, conventions
- [x] Export du modèle du projet 4
- [x] API FastAPI (`/health`, `/model/info`, `/predict`, `/predict/batch`), validation Pydantic, clé API
- [ ] Base PostgreSQL : création des tables, chargement du dataset, traçabilité des prédictions
- [ ] Tests Pytest et rapport de couverture
- [ ] Pipeline CI/CD GitHub Actions (environnements dev/test/prod, secrets)
- [ ] Documentation complète et soutenance
