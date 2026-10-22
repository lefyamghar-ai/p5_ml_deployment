"""
Tests unitaires du pretraitement : donnees brutes -> 39 variables du modele.
"""

import pandas as pd
import pytest

from app.ml.preprocessing import COLONNES_ENTREE, COLONNES_QUALITATIVES, preparer_features


def test_entrainement_produit_39_colonnes_sans_categorie_de_reference(dataset):
    X = preparer_features(dataset)

    assert X.shape == (1470, 39)
    assert "genre_F" not in X.columns  # drop_first : la premiere modalite sert de reference
    assert "genre_M" in X.columns


def test_inference_identique_a_l_entrainement_ligne_par_ligne(dataset, predictor):
    """Un employe seul (cas de l'API) doit etre encode exactement comme dans le dataset complet."""
    X_complet = preparer_features(dataset).astype(float)

    for i in range(0, len(dataset), 37):
        X_seul = preparer_features(dataset.iloc[[i]], predictor.feature_columns).astype(float)
        assert list(X_seul.columns) == predictor.feature_columns
        assert (X_seul.values == X_complet.iloc[[i]].values).all(), f"ligne {i} encodee differemment"


def test_colonnes_dans_l_ordre_du_modele(employe_valide, predictor):
    X = preparer_features(pd.DataFrame([employe_valide]), predictor.feature_columns)

    assert list(X.columns) == predictor.feature_columns


@pytest.mark.parametrize("valeur", ["11 %", "11%", 11, 11.0])
def test_augmentation_texte_ou_nombre(employe_valide, predictor, valeur):
    X = preparer_features(pd.DataFrame([{**employe_valide, "augementation_salaire_precedente": valeur}]),
                          predictor.feature_columns)

    assert X["augementation_salaire_precedente"].iloc[0] == 11.0


@pytest.mark.parametrize(("valeur", "attendu"), [("Oui", 1), ("Non", 0), ("oui", 1), (True, 1), (False, 0)])
def test_heures_supplementaires_en_binaire(employe_valide, predictor, valeur, attendu):
    X = preparer_features(pd.DataFrame([{**employe_valide, "heure_supplementaires": valeur}]),
                          predictor.feature_columns)

    assert X["heure_supplementaires"].iloc[0] == attendu


def test_categorie_de_reference_encodee_en_zeros(employe_valide, predictor):
    """genre = F est la reference : toutes les colonnes genre_* valent 0."""
    X = preparer_features(pd.DataFrame([{**employe_valide, "genre": "F"}]), predictor.feature_columns)

    assert X.filter(regex="^genre_").sum(axis=1).iloc[0] == 0


def test_une_seule_modalite_active_par_variable(employe_valide, predictor):
    X = preparer_features(pd.DataFrame([{**employe_valide, "poste": "Manager"}]), predictor.feature_columns)

    assert X["poste_Manager"].iloc[0] == 1
    assert X.filter(regex="^poste_").sum(axis=1).iloc[0] == 1


def test_colonne_manquante_refusee(employe_valide):
    incomplet = {k: v for k, v in employe_valide.items() if k != "age"}

    with pytest.raises(ValueError, match="age"):
        preparer_features(pd.DataFrame([incomplet]))


def test_colonnes_en_trop_ignorees(employe_valide, predictor):
    X = preparer_features(pd.DataFrame([{**employe_valide, "id_employee": 1, "a_quitte_l_entreprise": "Oui"}]),
                          predictor.feature_columns)

    assert X.shape == (1, 39)


def test_listes_de_colonnes_coherentes():
    assert len(COLONNES_ENTREE) == 25
    assert set(COLONNES_QUALITATIVES) <= set(COLONNES_ENTREE)
