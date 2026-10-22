"""
Tests du modele : chargement, coherence des sorties, performances et comportement.
"""

import time

import pytest
from sklearn.metrics import precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.ml.preprocessing import COLONNES_QUALITATIVES, preparer_features


def test_artefact_complet(predictor):
    assert type(predictor.model).__name__ == "RandomForestClassifier"
    assert len(predictor.feature_columns) == 39
    assert 0 < predictor.threshold < 1
    assert predictor.model_version == "1.0.0"
    assert set(predictor.categories) == set(COLONNES_QUALITATIVES)
    assert predictor.model.n_features_in_ == 39


def test_prediction_bien_formee(predictor, employe_valide):
    [r] = predictor.predict([employe_valide])

    assert 0 <= r.probabilite <= 1
    assert r.prediction in (0, 1)
    assert r.prediction == int(r.probabilite >= predictor.threshold)


def test_predictions_reproductibles(predictor, employe_valide):
    assert predictor.predict([employe_valide]) == predictor.predict([employe_valide])


def test_lot_et_unitaire_identiques(predictor, dataset):
    employes = dataset.head(10).to_dict("records")

    en_lot = predictor.predict(employes)
    un_par_un = [predictor.predict([e])[0] for e in employes]

    assert en_lot == un_par_un


def test_employe_1_detecte_comme_depart(predictor, employe_valide):
    """L'employe n°1 du dataset est parti : le modele doit le signaler."""
    [r] = predictor.predict([employe_valide])

    assert r.prediction == 1


def test_heures_supplementaires_augmentent_le_risque(predictor, employe_valide):
    """Les heures sup sont le 1er facteur de depart identifie au projet 4 (SHAP)."""
    [avec] = predictor.predict([{**employe_valide, "heure_supplementaires": "Oui"}])
    [sans] = predictor.predict([{**employe_valide, "heure_supplementaires": "Non"}])

    assert avec.probabilite > sans.probabilite


def test_performances_sur_le_jeu_de_test(predictor, dataset):
    """Memes 294 employes de test qu'au projet 4 : on retrouve les performances annoncees."""
    X = preparer_features(dataset, predictor.feature_columns)
    y = (dataset["a_quitte_l_entreprise"] == "Oui").astype(int)
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    probas = predictor.model.predict_proba(X_test)[:, 1]
    preds = (probas >= predictor.threshold).astype(int)

    assert recall_score(y_test, preds) == pytest.approx(predictor.metrics["rappel"], abs=1e-4)
    assert precision_score(y_test, preds) == pytest.approx(predictor.metrics["precision"], abs=1e-4)
    assert recall_score(y_test, preds) >= 0.80  # exigence metier : detecter au moins 80 % des departs


def test_temps_de_reponse(predictor, dataset):
    employes = dataset.to_dict("records")

    debut = time.perf_counter()
    predictor.predict(employes[:1])
    unitaire = time.perf_counter() - debut
    debut = time.perf_counter()
    predictor.predict(employes)
    complet = time.perf_counter() - debut

    assert unitaire < 0.5  # une prediction API
    assert complet < 3  # les 1 470 employes d'un coup


@pytest.mark.slow
def test_export_reproduit_le_modele(tmp_path, monkeypatch, predictor):
    """Relancer l'export donne le meme seuil et les memes performances (resultats reproductibles)."""
    import joblib

    from scripts import export_model

    sortie = tmp_path / "model.joblib"
    monkeypatch.setattr(export_model, "SORTIE", sortie)
    monkeypatch.setattr(export_model, "RACINE", tmp_path)
    export_model.main()

    nouveau = joblib.load(sortie)
    assert nouveau["threshold"] == pytest.approx(predictor.threshold)
    assert nouveau["metrics_test"] == predictor.metrics
    assert nouveau["feature_columns"] == predictor.feature_columns
