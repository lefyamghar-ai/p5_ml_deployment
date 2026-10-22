"""
Tests de la base de donnees : enregistrement systematique des entrees et sorties du modele,
historique, employes du dataset, contraintes et indisponibilite de la base.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import Employee, Prediction, PredictionInput
from app.services import predire_et_tracer


def compter(db, modele) -> int:
    return db.scalar(select(func.count()).select_from(modele))


# ---------- Tracabilite ----------


def test_predict_enregistre_entree_et_sortie(client, headers, employe_valide, db):
    corps = client.post("/predict", json=employe_valide, headers=headers).json()

    prediction = db.get(Prediction, corps["prediction_id"])
    assert prediction is not None
    assert prediction.probabilite_depart == corps["probabilite_depart"]
    assert prediction.prediction == corps["prediction"]
    assert prediction.model_version == "1.0.0"
    assert prediction.latency_ms >= 0

    entree = prediction.input
    assert entree.source == "api"
    assert entree.employee_id is None
    assert {c: getattr(entree, c) for c in employe_valide} == employe_valide  # donnees exactes conservees


def test_requete_invalide_n_ecrit_rien(client, headers, employe_valide, db):
    client.post("/predict", json={**employe_valide, "age": 15}, headers=headers)
    client.post("/predict", json=employe_valide)  # sans cle API

    assert compter(db, PredictionInput) == 0
    assert compter(db, Prediction) == 0


def test_batch_enregistre_chaque_employe(client, headers, employe_valide, db):
    client.post("/predict/batch", json={"employes": [employe_valide] * 5}, headers=headers)

    assert compter(db, PredictionInput) == 5
    assert compter(db, Prediction) == 5
    assert set(db.scalars(select(PredictionInput.source))) == {"api_batch"}


def test_une_sortie_par_entree(client, headers, employe_valide, db):
    for _ in range(3):
        client.post("/predict", json=employe_valide, headers=headers)

    entrees = db.scalars(select(PredictionInput)).all()
    assert len(entrees) == 3
    assert all(e.prediction is not None for e in entrees)


def test_service_transaction_annulee_si_le_modele_echoue(db, predictor, employe_valide, monkeypatch):
    """Pas de trace a moitie ecrite : si le modele plante, l'entree n'est pas conservee."""

    def panne(_):
        raise RuntimeError("panne du modele")

    monkeypatch.setattr(predictor, "predict", panne)
    with pytest.raises(RuntimeError):
        predire_et_tracer(db, predictor, [employe_valide], source="script")
    db.rollback()

    assert compter(db, PredictionInput) == 0


# ---------- Employes du dataset ----------


def test_lire_employe(client, headers, employes_en_base):
    r = client.get(f"/employees/{employes_en_base[0]}", headers=headers)

    assert r.status_code == 200
    assert r.json()["id_employee"] == 1
    assert r.json()["a_quitte_l_entreprise"] is True


def test_employe_introuvable(client, headers, employes_en_base):
    assert client.get("/employees/999999", headers=headers).status_code == 404
    assert client.post("/employees/999999/predict", headers=headers).status_code == 404


def test_predict_employe_lie_la_prediction_a_l_employe(client, headers, employes_en_base, db, employe_valide):
    r = client.post("/employees/1/predict", headers=headers)

    assert r.status_code == 200
    entree = db.get(Prediction, r.json()["prediction_id"]).input
    assert entree.source == "employee"
    assert entree.employee_id == 1
    # l'employe 1 en base et l'exemple de l'API sont la meme personne : meme prediction
    direct = client.post("/predict", json=employe_valide, headers=headers).json()
    assert r.json()["probabilite_depart"] == direct["probabilite_depart"]


def test_chargement_du_dataset(employes_en_base, db):
    assert compter(db, Employee) == 20
    assert db.get(Employee, 1).augementation_salaire_precedente == 11.0


# ---------- Historique ----------


def test_historique_du_plus_recent_au_plus_ancien(client, headers, employe_valide):
    ids = [client.post("/predict", json=employe_valide, headers=headers).json()["prediction_id"] for _ in range(3)]

    r = client.get("/predictions", headers=headers)

    assert r.status_code == 200
    assert r.json()["total"] == 3
    assert [p["prediction_id"] for p in r.json()["items"]] == ids[::-1]
    assert r.json()["items"][0]["entree"] == employe_valide


def test_historique_pagination(client, headers, employe_valide):
    client.post("/predict/batch", json={"employes": [employe_valide] * 5}, headers=headers)

    page = client.get("/predictions?limit=2&offset=2", headers=headers).json()

    assert page["total"] == 5
    assert len(page["items"]) == 2
    assert (page["limit"], page["offset"]) == (2, 2)


def test_historique_filtre_par_prediction(client, headers, employe_valide):
    stable = {**employe_valide, "heure_supplementaires": "Non", "age": 45, "revenu_mensuel": 15000,
              "satisfaction_employee_equipe": 4, "satisfaction_employee_equilibre_pro_perso": 4,
              "satisfaction_employee_environnement": 4, "frequence_deplacement": "Aucun"}
    client.post("/predict/batch", json={"employes": [employe_valide, employe_valide, stable]}, headers=headers)

    departs = client.get("/predictions?prediction=1", headers=headers).json()
    restes = client.get("/predictions?prediction=0", headers=headers).json()

    assert departs["total"] == 2
    assert restes["total"] == 1
    assert {p["prediction"] for p in departs["items"]} == {1}


@pytest.mark.parametrize("parametres", ["limit=0", "limit=101", "offset=-1", "prediction=2"])
def test_historique_parametres_invalides(client, headers, parametres):
    assert client.get(f"/predictions?{parametres}", headers=headers).status_code == 422


def test_lire_une_prediction(client, headers, employe_valide):
    pid = client.post("/predict", json=employe_valide, headers=headers).json()["prediction_id"]

    r = client.get(f"/predictions/{pid}", headers=headers)

    assert r.status_code == 200
    assert r.json()["prediction_id"] == pid
    assert r.json()["source"] == "api"
    assert r.json()["entree"] == employe_valide


def test_prediction_introuvable(client, headers):
    assert client.get("/predictions/999999", headers=headers).status_code == 404


# ---------- Contraintes de la base ----------


def test_contrainte_probabilite(db, employe_valide):
    entree = PredictionInput(**employe_valide, source="test")
    db.add(Prediction(input=entree, probabilite_depart=1.5, prediction=1, seuil=0.4, model_version="x",
                      latency_ms=1))

    with pytest.raises(IntegrityError):
        db.commit()


def test_contrainte_age(db, employe_valide):
    db.add(PredictionInput(**{**employe_valide, "age": 12}, source="test"))

    with pytest.raises(IntegrityError):
        db.commit()


def test_une_seule_sortie_par_entree(db, employe_valide):
    entree = PredictionInput(**employe_valide, source="test")
    db.add(entree)
    db.flush()
    for _ in range(2):
        db.add(Prediction(input_id=entree.id, probabilite_depart=0.5, prediction=1, seuil=0.4, model_version="x",
                          latency_ms=1))

    with pytest.raises(IntegrityError):
        db.commit()


# ---------- Base indisponible ----------


def _base_en_panne():
    raise OperationalError("SELECT 1", {}, Exception("connexion refusee"))
    yield  # pragma: no cover


def test_base_indisponible_renvoie_503(client, headers, employe_valide):
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = _base_en_panne
    try:
        r = client.post("/predict", json=employe_valide, headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 503
    assert r.json()["detail"] == "Base de données indisponible"


def test_health_signale_la_base_indisponible(client, monkeypatch):
    import app.main

    def pas_de_base():
        raise RuntimeError("DATABASE_URL n'est pas defini")

    monkeypatch.setattr(app.main, "get_sessionmaker", pas_de_base)

    assert client.get("/health").json() == {"status": "degraded", "model_loaded": True, "database": False,
                                            "environment": "test"}


def test_database_url_obligatoire(monkeypatch):
    from app.config import get_settings
    from app.database import get_engine

    monkeypatch.setattr(get_settings(), "database_url", None)
    get_engine().dispose()
    get_engine.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            get_engine()
    finally:
        monkeypatch.undo()
        get_engine.cache_clear()
