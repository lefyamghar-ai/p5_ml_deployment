"""
Configuration de l'application, lue dans les variables d'environnement (ou le fichier .env).

Aucun secret n'est ecrit dans le code : API_KEY et DATABASE_URL viennent de l'environnement
(.env en local, GitHub Secrets en CI/CD).
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

RACINE = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=RACINE / ".env", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    model_path: Path = RACINE / "app" / "ml" / "model.joblib"
    api_key: str | None = None  # si defini, les endpoints de prediction exigent l'en-tete X-API-Key
    database_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
