"""
Requetes d'exemple sur la base : volumes, dernieres predictions, suivi du modele.
Peut aussi exporter l'historique (entrees + sorties) en CSV.

Utilise DATABASE_URL (role applicatif, lecture seule ici).

Lancer depuis la racine du depot :
    python scripts/query_db.py
    python scripts/query_db.py --export data/examples/predictions_exemples.csv
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app.database import get_engine  # noqa: E402

REQUETES = {
    "Volumes par table": """
        SELECT 'employees' AS table_name, count(*) AS lignes FROM employees
        UNION ALL SELECT 'prediction_inputs', count(*) FROM prediction_inputs
        UNION ALL SELECT 'predictions', count(*) FROM predictions
    """,
    "Predictions par origine": """
        SELECT i.source, count(*) AS nb, round(avg(p.prediction)::numeric, 3) AS taux_depart_predit,
               round(avg(p.latency_ms)::numeric, 2) AS latence_ms_moy
        FROM predictions p JOIN prediction_inputs i ON i.id = p.input_id
        GROUP BY i.source ORDER BY nb DESC
    """,
    "10 dernieres predictions": """
        SELECT p.id, p.created_at::timestamp(0) AS date, i.source, i.employee_id, i.age, i.poste,
               i.heure_supplementaires AS heures_sup, p.probabilite_depart, p.prediction, p.model_version
        FROM predictions p JOIN prediction_inputs i ON i.id = p.input_id
        ORDER BY p.id DESC LIMIT 10
    """,
    "Predictions sur employes connus : prediction vs realite": """
        SELECT CASE WHEN e.a_quitte_l_entreprise THEN 'parti' ELSE 'reste' END AS reel,
               sum(CASE WHEN p.prediction = 1 THEN 1 ELSE 0 END) AS predit_depart,
               sum(CASE WHEN p.prediction = 0 THEN 1 ELSE 0 END) AS predit_reste
        FROM predictions p
        JOIN prediction_inputs i ON i.id = p.input_id
        JOIN employees e ON e.id_employee = i.employee_id
        GROUP BY reel ORDER BY reel
    """,
    "Taux de depart predit par departement": """
        SELECT i.departement, count(*) AS nb, round(avg(p.prediction)::numeric, 3) AS taux_depart_predit
        FROM predictions p JOIN prediction_inputs i ON i.id = p.input_id
        GROUP BY i.departement ORDER BY taux_depart_predit DESC
    """,
}

EXPORT = """
    SELECT p.id AS prediction_id, p.created_at, i.source, i.employee_id,
           i.age, i.genre, i.revenu_mensuel, i.statut_marital, i.departement, i.poste,
           i.nombre_experiences_precedentes, i.annee_experience_totale, i.annees_dans_le_poste_actuel,
           i.satisfaction_employee_environnement, i.note_evaluation_precedente, i.niveau_hierarchique_poste,
           i.satisfaction_employee_nature_travail, i.satisfaction_employee_equipe,
           i.satisfaction_employee_equilibre_pro_perso, i.note_evaluation_actuelle, i.heure_supplementaires,
           i.augementation_salaire_precedente, i.nombre_participation_pee, i.nb_formations_suivies,
           i.distance_domicile_travail, i.niveau_education, i.domaine_etude, i.frequence_deplacement,
           i.annees_depuis_la_derniere_promotion,
           p.probabilite_depart, p.prediction, p.seuil, p.model_version, p.latency_ms
    FROM predictions p JOIN prediction_inputs i ON i.id = p.input_id
    ORDER BY p.id
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=Path, help="exporte l'historique des predictions en CSV")
    args = parser.parse_args()

    with get_engine().connect() as conn:
        if args.export:
            df = pd.read_sql(text(EXPORT), conn)
            df["employee_id"] = df["employee_id"].astype("Int64")  # vide si la demande ne vient pas du dataset
            args.export.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(args.export, index=False)
            print(f"{len(df)} predictions exportees dans {args.export}")
            return
        for titre, sql in REQUETES.items():
            print(f"\n=== {titre}")
            print(pd.read_sql(text(sql), conn).to_string(index=False))


if __name__ == "__main__":
    main()
