"""
Schemas Pydantic : validation des donnees entrantes et format des reponses.

Les bornes sont des bornes metier (un peu plus larges que les valeurs vues dans le dataset),
les variables qualitatives n'acceptent que les modalites connues du modele : une modalite
inconnue serait silencieusement encodee en "categorie de reference", donc on la refuse.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Note = Annotated[int, Field(ge=1, le=4)]  # echelle des satisfactions et evaluations : 1 a 4

EXEMPLE_EMPLOYE = {
    "age": 41, "genre": "F", "revenu_mensuel": 5993, "statut_marital": "Célibataire",
    "departement": "Commercial", "poste": "Cadre Commercial", "nombre_experiences_precedentes": 8,
    "annee_experience_totale": 8, "annees_dans_le_poste_actuel": 4,
    "satisfaction_employee_environnement": 2, "note_evaluation_precedente": 3,
    "niveau_hierarchique_poste": 2, "satisfaction_employee_nature_travail": 4,
    "satisfaction_employee_equipe": 1, "satisfaction_employee_equilibre_pro_perso": 1,
    "note_evaluation_actuelle": 3, "heure_supplementaires": "Oui",
    "augementation_salaire_precedente": 11, "nombre_participation_pee": 0, "nb_formations_suivies": 0,
    "distance_domicile_travail": 1, "niveau_education": 2, "domaine_etude": "Infra & Cloud",
    "frequence_deplacement": "Occasionnel", "annees_depuis_la_derniere_promotion": 0,
}


class EmployeInput(BaseModel):
    """Caracteristiques brutes d'un employe (memes noms de colonnes que le SIRH du projet 4)."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [EXEMPLE_EMPLOYE]})

    age: int = Field(ge=18, le=70, description="Âge en années")
    genre: Literal["F", "M"]
    revenu_mensuel: int = Field(gt=0, le=100_000, description="Salaire mensuel brut")
    statut_marital: Literal["Célibataire", "Divorcé(e)", "Marié(e)"]
    departement: Literal["Commercial", "Consulting", "Ressources Humaines"]
    poste: Literal[
        "Assistant de Direction", "Cadre Commercial", "Consultant", "Directeur Technique", "Manager",
        "Représentant Commercial", "Ressources Humaines", "Senior Manager", "Tech Lead",
    ]
    nombre_experiences_precedentes: int = Field(ge=0, le=20)
    annee_experience_totale: int = Field(ge=0, le=50)
    annees_dans_le_poste_actuel: int = Field(ge=0, le=50)
    satisfaction_employee_environnement: Note
    note_evaluation_precedente: Note
    niveau_hierarchique_poste: int = Field(ge=1, le=5)
    satisfaction_employee_nature_travail: Note
    satisfaction_employee_equipe: Note
    satisfaction_employee_equilibre_pro_perso: Note
    note_evaluation_actuelle: Note
    heure_supplementaires: Literal["Oui", "Non"]
    augementation_salaire_precedente: float = Field(ge=0, le=100, description="Dernière augmentation, en %")
    nombre_participation_pee: int = Field(ge=0, le=10)
    nb_formations_suivies: int = Field(ge=0, le=20)
    distance_domicile_travail: int = Field(ge=0, le=200, description="En km")
    niveau_education: int = Field(ge=1, le=5)
    domaine_etude: Literal[
        "Autre", "Entrepreunariat", "Infra & Cloud", "Marketing", "Ressources Humaines", "Transformation Digitale",
    ]
    frequence_deplacement: Literal["Aucun", "Frequent", "Occasionnel"]
    annees_depuis_la_derniere_promotion: int = Field(ge=0, le=50)

    @model_validator(mode="after")
    def verifier_coherence(self):
        if self.annee_experience_totale > self.age - 14:
            raise ValueError("annee_experience_totale incohérente avec l'âge")
        if self.annees_dans_le_poste_actuel > self.annee_experience_totale:
            raise ValueError("annees_dans_le_poste_actuel ne peut pas dépasser annee_experience_totale")
        if self.annees_depuis_la_derniere_promotion > self.annee_experience_totale:
            raise ValueError("annees_depuis_la_derniere_promotion ne peut pas dépasser annee_experience_totale")
        return self


class PredictionOutput(BaseModel):
    prediction_id: int = Field(description="Identifiant de la prédiction en base (table predictions)")
    created_at: datetime
    probabilite_depart: float = Field(ge=0, le=1, description="Probabilité de démission estimée")
    prediction: Literal[0, 1] = Field(description="1 = départ probable (probabilité >= seuil)")
    label: Literal["depart_probable", "reste"]
    seuil: float
    model_version: str


class BatchInput(BaseModel):
    employes: list[EmployeInput] = Field(min_length=1, max_length=100)


class BatchOutput(BaseModel):
    resultats: list[PredictionOutput]


class PredictionRecord(PredictionOutput):
    """Une prediction de l'historique, avec les donnees d'entree qui l'ont produite."""

    source: str
    employee_id: int | None
    latency_ms: float
    entree: EmployeInput


class PredictionList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PredictionRecord]


class EmployeeOutput(EmployeInput):
    model_config = ConfigDict(extra="ignore")

    id_employee: int
    a_quitte_l_entreprise: bool


class HealthOutput(BaseModel):
    status: Literal["ok", "degraded"]
    model_loaded: bool
    database: bool
    environment: str


class ModelInfoOutput(BaseModel):
    model_version: str
    algorithme: str
    seuil: float
    trained_at: str
    nb_features: int
    metriques_test: dict
    categories: dict[str, list[str]]
