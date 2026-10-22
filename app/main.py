"""
API FastAPI exposant le modele de prediction d'attrition TechNova.

Documentation interactive : /docs (Swagger UI) et /redoc.
Lancer en local : uvicorn app.main:app --reload
"""

import secrets
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings
from app.ml.predictor import Predictor, Resultat
from app.schemas import (
    BatchInput,
    BatchOutput,
    EmployeInput,
    HealthOutput,
    ModelInfoOutput,
    PredictionOutput,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.predictor = Predictor(get_settings().model_path)  # charge une seule fois au demarrage
    except FileNotFoundError:
        app.state.predictor = None  # l'API demarre quand meme : /health le signale
    yield


app = FastAPI(
    title="TechNova — API de prédiction d'attrition",
    description="Expose le modèle RandomForest du projet 4 : probabilité de démission d'un employé.",
    version="0.2.0",
    lifespan=lifespan,
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verifier_api_key(
    cle: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if settings.api_key is None:  # pas de cle configuree (dev local) : acces libre
        return
    if cle is None or not secrets.compare_digest(cle, settings.api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clé API absente ou invalide (en-tête X-API-Key)")


def get_predictor(request: Request) -> Predictor:
    predictor = request.app.state.predictor
    if predictor is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Modèle non chargé")
    return predictor


def _en_sortie(r: Resultat, predictor: Predictor) -> PredictionOutput:
    return PredictionOutput(
        probabilite_depart=round(r.probabilite, 4),
        prediction=r.prediction,
        label="depart_probable" if r.prediction == 1 else "reste",
        seuil=round(predictor.threshold, 4),
        model_version=predictor.model_version,
    )


@app.get("/", include_in_schema=False)
def racine():
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthOutput, tags=["Supervision"])
def health(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    """État de l'API et du modèle."""
    charge = request.app.state.predictor is not None
    return HealthOutput(status="ok" if charge else "degraded", model_loaded=charge, environment=settings.app_env)


@app.get("/model/info", response_model=ModelInfoOutput, tags=["Modèle"])
def model_info(predictor: Annotated[Predictor, Depends(get_predictor)]):
    """Version, seuil, performances de test et modalités acceptées."""
    return ModelInfoOutput(
        model_version=predictor.model_version,
        algorithme=type(predictor.model).__name__,
        seuil=predictor.threshold,
        trained_at=predictor.trained_at,
        nb_features=len(predictor.feature_columns),
        metriques_test=predictor.metrics,
        categories=predictor.categories,
    )


@app.post("/predict", response_model=PredictionOutput, tags=["Prédiction"],
          dependencies=[Depends(verifier_api_key)])
def predict(employe: EmployeInput, predictor: Annotated[Predictor, Depends(get_predictor)]):
    """Prédit le risque de démission d'un employé."""
    resultat = predictor.predict([employe.model_dump()])[0]
    return _en_sortie(resultat, predictor)


@app.post("/predict/batch", response_model=BatchOutput, tags=["Prédiction"],
          dependencies=[Depends(verifier_api_key)])
def predict_batch(lot: BatchInput, predictor: Annotated[Predictor, Depends(get_predictor)]):
    """Prédit le risque de démission pour plusieurs employés (100 maximum)."""
    resultats = predictor.predict([e.model_dump() for e in lot.employes])
    return BatchOutput(resultats=[_en_sortie(r, predictor) for r in resultats])
