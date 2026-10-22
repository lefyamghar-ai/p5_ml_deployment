"""
Chargement du modele exporte et calcul des predictions.

Le modele renvoie une probabilite de depart ; la decision (0 = reste, 1 = depart probable)
applique le seuil choisi au projet 4 (max F2), pas le seuil 0,5 par defaut.
"""

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from app.ml.preprocessing import preparer_features


@dataclass
class Resultat:
    probabilite: float
    prediction: int


class Predictor:
    def __init__(self, chemin: Path):
        artefact = joblib.load(chemin)
        self.model = artefact["model"]
        self.feature_columns: list[str] = artefact["feature_columns"]
        self.threshold: float = artefact["threshold"]
        self.categories: dict[str, list[str]] = artefact["categories"]
        self.model_version: str = artefact["model_version"]
        self.metrics: dict = artefact["metrics_test"]
        self.trained_at: str = artefact["trained_at"]

    def predict(self, employes: list[dict]) -> list[Resultat]:
        X = preparer_features(pd.DataFrame(employes), self.feature_columns)
        probas = self.model.predict_proba(X)[:, 1]
        return [Resultat(probabilite=float(p), prediction=int(p >= self.threshold)) for p in probas]
