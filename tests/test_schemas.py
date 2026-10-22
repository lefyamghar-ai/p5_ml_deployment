"""
Tests unitaires de la validation Pydantic des donnees entrantes.
"""

import pytest
from pydantic import ValidationError

from app.ml.preprocessing import COLONNES_ENTREE
from app.schemas import BatchInput, EmployeInput


def test_exemple_valide(employe_valide):
    assert EmployeInput(**employe_valide).age == 41


def test_tous_les_employes_du_dataset_sont_acceptes(dataset):
    """Aucun faux rejet : les 1 470 vrais employes passent la validation."""
    df = dataset[COLONNES_ENTREE].copy()
    df["augementation_salaire_precedente"] = df["augementation_salaire_precedente"].str.rstrip(" %").astype(float)

    for ligne in df.to_dict("records"):
        EmployeInput(**ligne)


def test_champs_du_schema_identiques_aux_colonnes_du_modele():
    assert set(EmployeInput.model_fields) == set(COLONNES_ENTREE)


def test_modalites_du_schema_identiques_a_celles_du_modele(predictor):
    """Le schema doit accepter exactement les modalites vues a l'entrainement."""
    for colonne, modalites in predictor.categories.items():
        annotation = EmployeInput.model_fields[colonne].annotation
        assert set(annotation.__args__) == set(modalites), colonne


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [
        ("age", 17), ("age", 71),
        ("revenu_mensuel", 0), ("revenu_mensuel", -100),
        ("satisfaction_employee_environnement", 0), ("satisfaction_employee_equipe", 5),
        ("note_evaluation_actuelle", 5),
        ("niveau_hierarchique_poste", 0), ("niveau_hierarchique_poste", 6),
        ("augementation_salaire_precedente", -1), ("augementation_salaire_precedente", 101),
        ("distance_domicile_travail", -1),
        ("nombre_experiences_precedentes", -1),
    ],
)
def test_valeur_hors_bornes_refusee(employe_valide, champ, valeur):
    with pytest.raises(ValidationError) as erreur:
        EmployeInput(**{**employe_valide, champ: valeur})

    assert erreur.value.errors()[0]["loc"] == (champ,)


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [("genre", "X"), ("poste", "Astronaute"), ("departement", "Finance"),
     ("heure_supplementaires", "Peut-être"), ("frequence_deplacement", "Toujours"), ("poste", "manager")],
)
def test_modalite_inconnue_refusee(employe_valide, champ, valeur):
    with pytest.raises(ValidationError):
        EmployeInput(**{**employe_valide, champ: valeur})


@pytest.mark.parametrize(("champ", "valeur"), [("age", "quarante"), ("revenu_mensuel", "beaucoup"), ("age", 41.5)])
def test_mauvais_type_refuse(employe_valide, champ, valeur):
    with pytest.raises(ValidationError):
        EmployeInput(**{**employe_valide, champ: valeur})


def test_nombre_en_texte_accepte(employe_valide):
    """Pydantic convertit "41" en 41 (mode souple par defaut pour les entiers ecrits en texte)."""
    assert EmployeInput(**{**employe_valide, "age": "41"}).age == 41


@pytest.mark.parametrize("champ", COLONNES_ENTREE)
def test_chaque_champ_est_obligatoire(employe_valide, champ):
    with pytest.raises(ValidationError) as erreur:
        EmployeInput(**{k: v for k, v in employe_valide.items() if k != champ})

    assert erreur.value.errors()[0]["type"] == "missing"


def test_champ_inconnu_refuse(employe_valide):
    with pytest.raises(ValidationError, match="extra"):
        EmployeInput(**employe_valide, salaire_souhaite=10_000)


@pytest.mark.parametrize(
    ("modifs", "message"),
    [
        ({"age": 20, "annee_experience_totale": 10}, "âge"),
        ({"annee_experience_totale": 3, "annees_dans_le_poste_actuel": 4}, "annees_dans_le_poste_actuel"),
        ({"annee_experience_totale": 8, "annees_depuis_la_derniere_promotion": 9}, "promotion"),
    ],
)
def test_incoherence_entre_champs_refusee(employe_valide, modifs, message):
    with pytest.raises(ValidationError, match=message):
        EmployeInput(**{**employe_valide, **modifs})


def test_cas_limites_acceptes(employe_valide):
    """Les bornes elles-memes sont valides."""
    EmployeInput(**{**employe_valide, "age": 18, "annee_experience_totale": 4, "annees_dans_le_poste_actuel": 0,
                    "annees_depuis_la_derniere_promotion": 0, "augementation_salaire_precedente": 0})
    EmployeInput(**{**employe_valide, "age": 70, "augementation_salaire_precedente": 100})


@pytest.mark.parametrize("taille", [0, 101])
def test_lot_taille_limitee(employe_valide, taille):
    with pytest.raises(ValidationError):
        BatchInput(employes=[employe_valide] * taille)


def test_lot_valide(employe_valide):
    assert len(BatchInput(employes=[employe_valide] * 100).employes) == 100
