# Futurisys — Déploiement du modèle de prédiction d'attrition (TechNova)

Projet 5 OpenClassrooms : mettre en production le modèle du projet 4 (TechNova Partners),
qui estime le risque de démission d'un employé à partir de ses données RH.

Objectifs :

- exposer le modèle via une API **FastAPI** documentée (Swagger) ;
- enregistrer chaque prédiction (entrée et sortie) dans **PostgreSQL** ;
- tester le code avec **Pytest** et mesurer la couverture ;
- automatiser les tests avec **GitHub Actions**.

## Structure du dépôt

```text
.
├── app/                  # Code de l'application (API, modèle, base de données)
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
- [ ] Export du modèle du projet 4
- [ ] API FastAPI avec validation Pydantic
- [ ] Base PostgreSQL : création des tables, chargement du dataset, traçabilité des prédictions
- [ ] Tests Pytest et rapport de couverture
- [ ] Pipeline CI/CD GitHub Actions (environnements dev/test/prod, secrets)
- [ ] Documentation complète et soutenance
