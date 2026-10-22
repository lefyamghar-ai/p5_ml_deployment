"""
Charge le dataset RH du projet 4 (data/employes.csv) dans la table employees.

Relancable sans risque : les employes deja presents (meme id_employee) sont ignores.
Utilise DATABASE_ADMIN_URL (role proprietaire).

Lancer depuis la racine du depot : python scripts/load_dataset.py
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app.config import get_settings  # noqa: E402
from app.models import Employee  # noqa: E402

DONNEES = RACINE / "data" / "employes.csv"


def lire_dataset(chemin: Path = DONNEES) -> list[dict]:
    df = pd.read_csv(chemin)
    df["augementation_salaire_precedente"] = (  # "11 %" -> 11.0
        df["augementation_salaire_precedente"].str.replace("%", "", regex=False).str.strip().astype(float)
    )
    df["a_quitte_l_entreprise"] = df["a_quitte_l_entreprise"] == "Oui"
    return df.to_dict("records")


def main() -> None:
    url = get_settings().database_admin_url
    if not url:
        sys.exit("DATABASE_ADMIN_URL n'est pas defini (voir .env.example)")
    engine = create_engine(url)

    lignes = lire_dataset()
    compter = select(func.count()).select_from(Employee)
    with engine.begin() as conn:
        avant = conn.execute(compter).scalar_one()
        conn.execute(insert(Employee).values(lignes).on_conflict_do_nothing(index_elements=["id_employee"]))
        apres = conn.execute(compter).scalar_one()
    print(f"{apres - avant} employes ajoutes, {apres} dans la table employees")


if __name__ == "__main__":
    main()
