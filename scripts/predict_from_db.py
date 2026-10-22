"""
Fait predire le modele sur des employes stockes en base, en passant par la base
comme l'API : chaque entree et chaque sortie sont enregistrees (source = "script").

Utilise DATABASE_URL (role applicatif, memes droits que l'API).

Lancer depuis la racine du depot :
    python scripts/predict_from_db.py               # 20 employes au hasard
    python scripts/predict_from_db.py --limit 100
    python scripts/predict_from_db.py --ids 1 2 3
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import func, select

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app.config import get_settings  # noqa: E402
from app.database import get_sessionmaker  # noqa: E402
from app.ml.predictor import Predictor  # noqa: E402
from app.models import Employee  # noqa: E402
from app.schemas import EmployeInput  # noqa: E402
from app.services import predire_et_tracer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=20, help="nombre d'employes tires au hasard")
    parser.add_argument("--ids", type=int, nargs="+", help="id_employee precis")
    args = parser.parse_args()

    predictor = Predictor(get_settings().model_path)
    with get_sessionmaker()() as db:
        requete = select(Employee)
        requete = requete.where(Employee.id_employee.in_(args.ids)) if args.ids else \
            requete.order_by(func.random()).limit(args.limit)
        employes = db.scalars(requete).all()
        if not employes:
            sys.exit("Aucun employe trouve (la table employees est-elle chargee ?)")

        champs = set(EmployeInput.model_fields)
        donnees = [EmployeInput.model_validate({c: getattr(e, c) for c in champs}).model_dump() for e in employes]
        sorties = predire_et_tracer(db, predictor, donnees, source="script",
                                    employee_ids=[e.id_employee for e in employes])

        bons = 0
        print(f"{'employe':>8} {'proba':>6} {'prediction':>16} {'reel':>6}")
        for e, p in zip(employes, sorties, strict=True):
            bons += p.prediction == int(e.a_quitte_l_entreprise)
            predit = "depart_probable" if p.prediction else "reste"
            reel = "parti" if e.a_quitte_l_entreprise else "reste"
            print(f"{e.id_employee:>8} {p.probabilite_depart:>6.3f} {predit:>16} {reel:>6}")
        print(f"\n{len(sorties)} predictions enregistrees (ids {sorties[0].id} a {sorties[-1].id}), "
              f"{bons}/{len(sorties)} conformes a la realite")


if __name__ == "__main__":
    main()
