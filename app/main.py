"""
API FastAPI exposant le modele de prediction d'attrition TechNova.

Chaque prediction passe par la base PostgreSQL : l'entree est enregistree dans
prediction_inputs, la sortie dans predictions (voir app/services.py).

Documentation interactive : /docs (Swagger UI) et /redoc.
Lancer en local : uvicorn app.main:app --reload
"""

import secrets
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db, get_sessionmaker
from app.ml.predictor import Predictor
from app.models import Employee, Prediction
from app.schemas import (
    BatchInput,
    BatchOutput,
    EmployeeOutput,
    EmployeInput,
    HealthOutput,
    ModelInfoOutput,
    PredictionList,
    PredictionOutput,
    PredictionRecord,
)
from app.services import predire_et_tracer


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.predictor = Predictor(get_settings().model_path)  # charge une seule fois au demarrage
    except FileNotFoundError:
        app.state.predictor = None  # l'API demarre quand meme : /health le signale
    yield


app = FastAPI(
    title="TechNova — API de prédiction d'attrition",
    description="Expose le modèle RandomForest du projet 4 : probabilité de démission d'un employé. "
                "Chaque prédiction (entrée et sortie) est enregistrée dans PostgreSQL.",
    version="0.3.0",
    lifespan=lifespan,
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


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


PredictorDep = Annotated[Predictor, Depends(get_predictor)]
Protege = [Depends(verifier_api_key)]


@app.exception_handler(SQLAlchemyError)
async def base_indisponible(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={"detail": "Base de données indisponible"})


def _en_sortie(p: Prediction) -> PredictionOutput:
    return PredictionOutput(
        prediction_id=p.id,
        created_at=p.created_at,
        probabilite_depart=p.probabilite_depart,
        prediction=p.prediction,
        label="depart_probable" if p.prediction == 1 else "reste",
        seuil=p.seuil,
        model_version=p.model_version,
    )


def _en_historique(p: Prediction) -> PredictionRecord:
    entree = p.input
    return PredictionRecord(
        **_en_sortie(p).model_dump(),
        source=entree.source,
        employee_id=entree.employee_id,
        latency_ms=p.latency_ms,
        entree=EmployeInput.model_validate({c: getattr(entree, c) for c in EmployeInput.model_fields}),
    )


@app.get("/", include_in_schema=False)
def racine():
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthOutput, tags=["Supervision"])
def health(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    """État de l'API, du modèle et de la connexion à la base."""
    modele = request.app.state.predictor is not None
    try:
        with get_sessionmaker()() as db:
            db.execute(text("SELECT 1"))
        base = True
    except (SQLAlchemyError, RuntimeError):
        base = False
    return HealthOutput(status="ok" if modele and base else "degraded", model_loaded=modele, database=base,
                        environment=settings.app_env)


@app.get("/model/info", response_model=ModelInfoOutput, tags=["Modèle"])
def model_info(predictor: PredictorDep):
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


@app.post("/predict", response_model=PredictionOutput, tags=["Prédiction"], dependencies=Protege)
def predict(employe: EmployeInput, predictor: PredictorDep, db: DbSession):
    """Prédit le risque de démission d'un employé (entrée et sortie enregistrées en base)."""
    return _en_sortie(predire_et_tracer(db, predictor, [employe.model_dump()], source="api")[0])


@app.post("/predict/batch", response_model=BatchOutput, tags=["Prédiction"], dependencies=Protege)
def predict_batch(lot: BatchInput, predictor: PredictorDep, db: DbSession):
    """Prédit le risque de démission pour plusieurs employés (100 maximum)."""
    sorties = predire_et_tracer(db, predictor, [e.model_dump() for e in lot.employes], source="api_batch")
    return BatchOutput(resultats=[_en_sortie(p) for p in sorties])


@app.get("/employees/{id_employee}", response_model=EmployeeOutput, tags=["Employés"], dependencies=Protege)
def lire_employe(id_employee: int, db: DbSession):
    """Données d'un employé du dataset."""
    employe = db.get(Employee, id_employee)
    if employe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Employé {id_employee} introuvable")
    return EmployeeOutput.model_validate(employe, from_attributes=True)


@app.post("/employees/{id_employee}/predict", response_model=PredictionOutput, tags=["Prédiction"],
          dependencies=Protege)
def predict_employe(id_employee: int, predictor: PredictorDep, db: DbSession):
    """Prédit le risque de démission d'un employé déjà présent en base."""
    employe = lire_employe(id_employee, db)
    donnees = EmployeInput.model_validate(employe.model_dump(include=set(EmployeInput.model_fields))).model_dump()
    return _en_sortie(predire_et_tracer(db, predictor, [donnees], source="employee", employee_ids=[id_employee])[0])


@app.get("/predictions", response_model=PredictionList, tags=["Historique"], dependencies=Protege)
def lister_predictions(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    prediction: Annotated[int | None, Query(ge=0, le=1, description="Filtrer : 1 = départs probables")] = None,
):
    """Historique des prédictions, de la plus récente à la plus ancienne."""
    requete = select(Prediction)
    if prediction is not None:
        requete = requete.where(Prediction.prediction == prediction)
    total = db.scalar(select(func.count()).select_from(requete.subquery()))
    lignes = db.scalars(
        requete.options(selectinload(Prediction.input)).order_by(Prediction.id.desc()).limit(limit).offset(offset)
    ).all()
    return PredictionList(total=total, limit=limit, offset=offset, items=[_en_historique(p) for p in lignes])


@app.get("/predictions/{prediction_id}", response_model=PredictionRecord, tags=["Historique"], dependencies=Protege)
def lire_prediction(prediction_id: int, db: DbSession):
    """Une prédiction et les données d'entrée qui l'ont produite."""
    p = db.scalar(select(Prediction).options(selectinload(Prediction.input)).where(Prediction.id == prediction_id))
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Prédiction {prediction_id} introuvable")
    return _en_historique(p)

