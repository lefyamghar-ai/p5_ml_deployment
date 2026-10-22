# Tests et couverture

## Lancer les tests

```bash
pytest                                   # 160 tests, environ 5 secondes
pytest --cov --cov-report=term-missing   # + couverture dans le terminal
pytest --cov --cov-report=html           # + rapport HTML dans htmlcov/index.html
pytest -m "not slow"                     # sans le test qui réentraîne le modèle
```

**Base de test** : par défaut, un fichier SQLite temporaire (rien à installer). Pour tester sur PostgreSQL,
comme en CI, on indique une base dédiée (jamais la base de travail : les tables y sont recréées) :

```bash
TEST_DATABASE_URL=postgresql+psycopg://technova_admin:MOT_DE_PASSE@localhost:5432/technova_test pytest
```

Les tables sont créées au début de la session et vidées après chaque test : les tests sont indépendants
et donnent toujours le même résultat (modèle et découpage train/test à `random_state` fixe).

## Ce qui est testé

| Fichier | Tests | Type | Contenu |
|---|---|---|---|
| `tests/test_preprocessing.py` | 17 | Unitaires | Encodage identique à l'entraînement (aussi pour un seul employé), `"11 %"` → 11.0, `Oui/Non` → 1/0, catégorie de référence, colonnes manquantes ou en trop |
| `tests/test_schemas.py` | 60 | Unitaires | Validation Pydantic : chaque champ obligatoire, bornes, modalités inconnues, mauvais types, champ en trop, incohérences entre champs, cas limites, taille des lots ; aucun des 1 470 vrais employés rejeté |
| `tests/test_model.py` | 9 | Fonctionnels (modèle) | Artefact complet, probabilités entre 0 et 1, seuil appliqué, reproductibilité, lot = unitaire, performances du projet 4 retrouvées sur le même jeu de test (rappel ≥ 0,80), temps de réponse, réexport identique |
| `tests/test_api.py` | 50 | Fonctionnels (API) | Statuts HTTP et format de chaque endpoint, erreurs 422 (données invalides, JSON malformé, lots), 401 sur les 6 endpoints protégés (sans clé, mauvaise clé, clé vide), 405, 503 si le modèle est absent, schéma OpenAPI |
| `tests/test_db.py` | 24 | Fonctionnels (base) | Chaque prédiction enregistre son entrée exacte et sa sortie, rien d'écrit pour une requête refusée, transaction annulée si le modèle échoue, historique (ordre, pagination, filtre), employés du dataset, contraintes `CHECK` et unicité, base indisponible (503, `/health` dégradé) |

## Couverture

Mesurée avec `pytest-cov` (lignes **et** branches), seuil minimal fixé à 90 % dans `pyproject.toml` :
la commande échoue en dessous.

| Fichier | Instructions | Branches | Couverture |
|---|---|---|---|
| `app/config.py` | 15 | 0 | 100 % |
| `app/database.py` | 17 | 2 | 100 % |
| `app/main.py` | 93 | 12 | 100 % |
| `app/ml/predictor.py` | 23 | 0 | 100 % |
| `app/ml/preprocessing.py` | 24 | 8 | 100 % |
| `app/models.py` | 60 | 0 | 100 % |
| `app/schemas.py` | 80 | 6 | 100 % |
| `app/services.py` | 16 | 0 | 100 % |
| **Total** | **328** | **28** | **100 %** |

Résultat identique sur SQLite et sur PostgreSQL 17.

## Points faibles identifiés et traités

| Risque | Traitement | Test qui le garde |
|---|---|---|
| Une modalité inconnue (ex. un nouveau poste) serait encodée sans erreur comme la catégorie de référence : prédiction fausse et silencieuse | Le schéma n'accepte que les modalités vues à l'entraînement | `test_modalites_du_schema_identiques_a_celles_du_modele`, `test_modalite_inconnue_refusee` |
| Un employé seul (cas de l'API) n'a pas toutes les colonnes one-hot : risque de décalage avec l'entraînement | Réalignement sur les 39 colonnes du modèle | `test_inference_identique_a_l_entrainement_ligne_par_ligne` |
| Le seuil par défaut (0,5) ferait rater des départs | Le seuil F2 (0,435) est stocké avec le modèle et appliqué | `test_prediction_bien_formee`, `test_performances_sur_le_jeu_de_test` |
| Une prédiction pourrait être renvoyée sans être tracée, ou tracée à moitié | Entrée et sortie écrites dans une seule transaction | `test_service_transaction_annulee_si_le_modele_echoue`, `test_une_sortie_par_entree` |
| Données incohérentes acceptées par la base hors API | Contraintes `CHECK` et unicité en base | `test_contrainte_*`, `test_une_seule_sortie_par_entree` |
| Le modèle dépend de la version de scikit-learn | Versions figées dans `requirements.txt` ; un réexport doit redonner le même modèle | `test_export_reproduit_le_modele` |

Limite connue : Pydantic convertit un nombre écrit en texte (`"41"`) en entier ; c'est accepté volontairement
(comportement standard, la valeur reste contrôlée par les bornes).
