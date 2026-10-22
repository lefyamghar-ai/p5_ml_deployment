"""
Preparation des donnees brutes d'un employe pour le modele.

Reproduit exactement les transformations du projet 4 (construire_x_y) :
- heure_supplementaires : "Oui"/"Non" -> 1/0
- augementation_salaire_precedente : "11 %" -> 11.0 (accepte aussi un nombre)
- encodage one-hot des variables qualitatives (categorie de reference supprimee)

A l'inference, on n'a souvent qu'un seul employe : get_dummies ne peut donc pas
deviner toutes les colonnes. On realigne sur la liste des colonnes vues a
l'entrainement (feature_columns), les colonnes absentes valent 0.
"""

import pandas as pd

COLONNES_REDONDANTES = [  # supprimees au projet 4 (trop correlees avec d'autres)
    "annees_dans_l_entreprise",
    "annes_sous_responsable_actuel",
]

COLONNES_QUALITATIVES = [
    "genre", "statut_marital", "departement", "poste",
    "domaine_etude", "frequence_deplacement",
]

COLONNES_NUMERIQUES = [
    "age", "revenu_mensuel", "nombre_experiences_precedentes", "annee_experience_totale",
    "annees_dans_le_poste_actuel", "satisfaction_employee_environnement",
    "note_evaluation_precedente", "niveau_hierarchique_poste",
    "satisfaction_employee_nature_travail", "satisfaction_employee_equipe",
    "satisfaction_employee_equilibre_pro_perso", "note_evaluation_actuelle",
    "heure_supplementaires", "augementation_salaire_precedente", "nombre_participation_pee",
    "nb_formations_suivies", "distance_domicile_travail", "niveau_education",
    "annees_depuis_la_derniere_promotion",
]

COLONNES_ENTREE = COLONNES_NUMERIQUES + COLONNES_QUALITATIVES  # ce que l'API doit recevoir


def _en_pourcentage(valeur) -> float:
    if isinstance(valeur, str):
        return float(valeur.replace("%", "").strip())  # "11 %" -> 11.0
    return float(valeur)


def _en_binaire(valeur) -> int:
    if isinstance(valeur, str):
        return int(valeur.strip().lower() == "oui")  # "Oui" -> 1
    return int(bool(valeur))


def preparer_features(df: pd.DataFrame, feature_columns: list[str] | None = None) -> pd.DataFrame:
    """Transforme des donnees brutes (1 ou plusieurs employes) en matrice X pour le modele.

    Sans feature_columns (entrainement) : get_dummies avec drop_first, comme au projet 4.
    Avec feature_columns (inference) : colonnes realignees sur celles de l'entrainement.
    """
    manquantes = [c for c in COLONNES_ENTREE if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes : {manquantes}")

    X = df[COLONNES_ENTREE].copy()
    X["heure_supplementaires"] = X["heure_supplementaires"].map(_en_binaire)
    X["augementation_salaire_precedente"] = X["augementation_salaire_precedente"].map(_en_pourcentage)

    if feature_columns is None:
        return pd.get_dummies(X, columns=COLONNES_QUALITATIVES, drop_first=True)

    X = pd.get_dummies(X, columns=COLONNES_QUALITATIVES)  # toutes les modalites presentes
    return X.reindex(columns=feature_columns, fill_value=0)  # meme ordre, categorie de reference ignoree
