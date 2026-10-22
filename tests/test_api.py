"""
Tests fonctionnels des endpoints FastAPI (statuts HTTP, format des reponses, securite, erreurs).
"""

import pytest

from app.ml.preprocessing import COLONNES_ENTREE

# ---------- Supervision et documentation ----------


def test_health(client):
    r = client.get("/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_loaded": True, "database": True, "environment": "test"}


def test_racine_redirige_vers_la_documentation(client):
    r = client.get("/", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "/docs"


def test_documentation_swagger(client):
    assert client.get("/docs").status_code == 200
    chemins = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/model/info", "/predict", "/predict/batch", "/predictions"} <= set(chemins)


def test_model_info(client, predictor):
    r = client.get("/model/info")

    assert r.status_code == 200
    corps = r.json()
    assert corps["algorithme"] == "RandomForestClassifier"
    assert corps["nb_features"] == 39
    assert corps["seuil"] == pytest.approx(predictor.threshold)
    assert corps["metriques_test"]["rappel"] >= 0.8


# ---------- Prediction ----------


def test_predict(client, headers, employe_valide):
    r = client.post("/predict", json=employe_valide, headers=headers)

    assert r.status_code == 200
    corps = r.json()
    assert set(corps) == {"prediction_id", "created_at", "probabilite_depart", "prediction", "label", "seuil",
                          "model_version"}
    assert 0 <= corps["probabilite_depart"] <= 1
    assert corps["prediction"] == 1
    assert corps["label"] == "depart_probable"


def test_predict_label_reste(client, headers, employe_valide):
    profil_stable = {**employe_valide, "heure_supplementaires": "Non", "age": 45, "revenu_mensuel": 15000,
                     "satisfaction_employee_equipe": 4, "satisfaction_employee_equilibre_pro_perso": 4,
                     "satisfaction_employee_environnement": 4, "frequence_deplacement": "Aucun"}

    corps = client.post("/predict", json=profil_stable, headers=headers).json()

    assert corps["prediction"] == 0
    assert corps["label"] == "reste"


def test_predict_meme_resultat_que_le_modele(client, headers, employe_valide, predictor):
    [attendu] = predictor.predict([employe_valide])

    corps = client.post("/predict", json=employe_valide, headers=headers).json()

    assert corps["probabilite_depart"] == pytest.approx(attendu.probabilite, abs=1e-4)


def test_predict_batch(client, headers, employe_valide):
    lot = [employe_valide, {**employe_valide, "heure_supplementaires": "Non"}, employe_valide]

    r = client.post("/predict/batch", json={"employes": lot}, headers=headers)

    assert r.status_code == 200
    resultats = r.json()["resultats"]
    assert len(resultats) == 3
    assert resultats[0]["probabilite_depart"] == resultats[2]["probabilite_depart"]
    assert len({res["prediction_id"] for res in resultats}) == 3


# ---------- Erreurs de validation (422) ----------


@pytest.mark.parametrize(
    ("modif", "champ"),
    [
        ({"age": 15}, "age"),
        ({"poste": "Astronaute"}, "poste"),
        ({"revenu_mensuel": "beaucoup"}, "revenu_mensuel"),
        ({"satisfaction_employee_equipe": 9}, "satisfaction_employee_equipe"),
        ({"champ_inconnu": 1}, "champ_inconnu"),
    ],
)
def test_predict_donnees_invalides(client, headers, employe_valide, modif, champ):
    r = client.post("/predict", json={**employe_valide, **modif}, headers=headers)

    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"][-1] == champ


@pytest.mark.parametrize("champ", ["age", "poste", "heure_supplementaires"])
def test_predict_champ_manquant(client, headers, employe_valide, champ):
    r = client.post("/predict", json={k: v for k, v in employe_valide.items() if k != champ}, headers=headers)

    assert r.status_code == 422
    assert r.json()["detail"][0]["type"] == "missing"


def test_predict_incoherence(client, headers, employe_valide):
    r = client.post("/predict", json={**employe_valide, "annees_dans_le_poste_actuel": 20}, headers=headers)

    assert r.status_code == 422
    assert "annees_dans_le_poste_actuel" in r.json()["detail"][0]["msg"]


@pytest.mark.parametrize("corps", [None, [], "texte", {}])
def test_predict_corps_invalide(client, headers, corps):
    assert client.post("/predict", json=corps, headers=headers).status_code == 422


def test_predict_json_malforme(client, headers):
    r = client.post("/predict", content="{pas du json", headers={**headers, "Content-Type": "application/json"})

    assert r.status_code == 422


@pytest.mark.parametrize("taille", [0, 101])
def test_batch_taille_invalide(client, headers, employe_valide, taille):
    r = client.post("/predict/batch", json={"employes": [employe_valide] * taille}, headers=headers)

    assert r.status_code == 422


def test_batch_un_employe_invalide_rejette_tout_le_lot(client, headers, employe_valide):
    r = client.post("/predict/batch", json={"employes": [employe_valide, {**employe_valide, "age": 5}]},
                    headers=headers)

    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "employes", 1, "age"]


def test_methode_non_autorisee(client):
    assert client.get("/predict").status_code == 405


# ---------- Authentification ----------

ENDPOINTS_PROTEGES = [
    ("post", "/predict"), ("post", "/predict/batch"), ("get", "/predictions"), ("get", "/predictions/1"),
    ("get", "/employees/1"), ("post", "/employees/1/predict"),
]


@pytest.mark.parametrize(("methode", "url"), ENDPOINTS_PROTEGES)
@pytest.mark.parametrize("cle", [None, "mauvaise-cle", ""])
def test_endpoint_protege_sans_cle_valide(client, methode, url, cle):
    headers = {} if cle is None else {"X-API-Key": cle}

    r = getattr(client, methode)(url, headers=headers)

    assert r.status_code == 401
    assert "X-API-Key" in r.json()["detail"]


@pytest.mark.parametrize("url", ["/health", "/model/info", "/docs"])
def test_endpoints_publics_sans_cle(client, url):
    assert client.get(url).status_code == 200


def test_acces_libre_sans_api_key_configuree(client, employe_valide, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "api_key", None)

    assert client.post("/predict", json=employe_valide).status_code == 200


# ---------- Modele absent ----------


def test_modele_introuvable(monkeypatch, tmp_path, headers, employe_valide):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app

    monkeypatch.setattr(get_settings(), "model_path", tmp_path / "absent.joblib")
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "degraded"
        assert client.get("/health").json()["model_loaded"] is False
        assert client.post("/predict", json=employe_valide, headers=headers).status_code == 503
        assert client.get("/model/info").status_code == 503


def test_schema_openapi_decrit_les_25_champs(client):
    schema = client.get("/openapi.json").json()["components"]["schemas"]["EmployeInput"]

    assert set(schema["properties"]) == set(COLONNES_ENTREE)
    assert set(schema["required"]) == set(COLONNES_ENTREE)
    assert schema["examples"]
