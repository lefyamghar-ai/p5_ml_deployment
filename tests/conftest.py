"""
Fixtures partagees par tous les tests.

Base de donnees de test :
- par defaut, un fichier SQLite temporaire (aucune installation necessaire) ;
- si TEST_DATABASE_URL est defini (ex. en CI), une vraie base PostgreSQL.
Les tables sont creees au debut de la session et videes apres chaque test :
les tests sont independants et reproductibles.

Les variables d'environnement sont fixees AVANT l'import de l'application,
pour que la configuration de test remplace celle du .env local.
"""

import os
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

API_KEY_TEST = "cle-de-test"


@pytest.fixture(scope="session", autouse=True)
def environnement_de_test(tmp_path_factory):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path_factory.mktemp('db') / 'test.db'}"
    os.environ.update({"APP_ENV": "test", "DATABASE_URL": url, "API_KEY": API_KEY_TEST})
    os.environ.pop("MODEL_PATH", None)

    from app.config import get_settings
    from app.database import get_engine, get_sessionmaker

    for cache in (get_settings, get_engine, get_sessionmaker):
        cache.cache_clear()

    from app.models import Base

    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    yield
    Base.metadata.drop_all(get_engine())
    get_engine().dispose()


@pytest.fixture(autouse=True)
def base_vide():
    """Vide les tables apres chaque test (ordre inverse des cles etrangeres)."""
    yield
    from app.database import get_engine
    from app.models import Base

    with get_engine().begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(scope="session")
def predictor():
    from app.config import get_settings
    from app.ml.predictor import Predictor

    return Predictor(get_settings().model_path)


@pytest.fixture(scope="session")
def dataset():
    import pandas as pd

    return pd.read_csv(RACINE / "data" / "employes.csv")


@pytest.fixture
def employe_valide() -> dict:
    """Employe n°1 du dataset (parti en realite), au format attendu par l'API."""
    from app.schemas import EXEMPLE_EMPLOYE

    return dict(EXEMPLE_EMPLOYE)


@pytest.fixture
def db():
    from app.database import get_sessionmaker

    with get_sessionmaker()() as session:
        yield session


@pytest.fixture
def employes_en_base(db) -> list[int]:
    """Charge les 20 premiers employes du dataset dans la table employees."""
    from app.models import Employee
    from scripts.load_dataset import lire_dataset

    lignes = lire_dataset()[:20]
    db.add_all(Employee(**ligne) for ligne in lignes)
    db.commit()
    return [ligne["id_employee"] for ligne in lignes]


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:  # le "with" declenche le chargement du modele (lifespan)
        yield c


@pytest.fixture
def headers() -> dict:
    return {"X-API-Key": API_KEY_TEST}
