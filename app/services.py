"""
Passage obligatoire par la base : toute prediction suit le meme chemin.

1. les donnees d'entree sont enregistrees dans prediction_inputs ;
2. le modele calcule la prediction ;
3. le resultat est enregistre dans predictions, lie a son entree ;
4. les deux sont valides ensemble (une seule transaction).
"""

import time

from sqlalchemy.orm import Session

from app.ml.predictor import Predictor
from app.models import Prediction, PredictionInput


def predire_et_tracer(
    db: Session,
    predictor: Predictor,
    employes: list[dict],
    source: str,
    employee_ids: list[int | None] | None = None,
) -> list[Prediction]:
    employee_ids = employee_ids or [None] * len(employes)
    entrees = [PredictionInput(**e, source=source, employee_id=i) for e, i in zip(employes, employee_ids, strict=True)]
    db.add_all(entrees)
    db.flush()  # attribue les id des entrees avant le calcul

    debut = time.perf_counter()
    resultats = predictor.predict(employes)
    latence_ms = (time.perf_counter() - debut) * 1000 / len(employes)

    sorties = [
        Prediction(
            input=entree,
            probabilite_depart=round(r.probabilite, 4),
            prediction=r.prediction,
            seuil=round(predictor.threshold, 4),
            model_version=predictor.model_version,
            latency_ms=round(latence_ms, 3),
        )
        for entree, r in zip(entrees, resultats, strict=True)
    ]
    db.add_all(sorties)
    db.commit()
    return sorties
