"""
Cree les tables de la base PostgreSQL et donne ses droits au role applicatif.

Prerequis : roles et base crees une fois avec sql/00_roles.sql.
Utilise DATABASE_ADMIN_URL (role proprietaire technova_admin).

Lancer depuis la racine du depot :
    python scripts/create_db.py              # cree les tables (sans toucher aux existantes)
    python scripts/create_db.py --reset      # supprime puis recree toutes les tables
    python scripts/create_db.py --dump-sql   # ecrit le DDL equivalent dans sql/01_schema.sql
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402

ROLE_APP = "technova_app"

# moindre privilege : l'API lit les employes, ajoute et lit les predictions,
# mais ne peut ni modifier ni supprimer l'historique
DROITS_APP = [
    f"GRANT USAGE ON SCHEMA public TO {ROLE_APP}",
    f"GRANT SELECT ON employees TO {ROLE_APP}",
    f"GRANT SELECT, INSERT ON prediction_inputs, predictions TO {ROLE_APP}",
    f"GRANT USAGE ON SEQUENCE prediction_inputs_id_seq, predictions_id_seq TO {ROLE_APP}",
]


def ddl_sql() -> str:
    """DDL PostgreSQL genere a partir des modeles SQLAlchemy (une seule source de verite)."""
    dialecte = postgresql.dialect()
    blocs = ["-- Genere par : python scripts/create_db.py --dump-sql (ne pas modifier a la main)\n"]
    for table in Base.metadata.sorted_tables:
        blocs.append(str(CreateTable(table).compile(dialect=dialecte)).strip() + ";\n")
        blocs += [str(CreateIndex(i).compile(dialect=dialecte)) + ";" for i in table.indexes]
        blocs.append("")
    blocs += [d + ";" for d in DROITS_APP]
    return "\n".join(blocs) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="supprime puis recree toutes les tables")
    parser.add_argument("--dump-sql", action="store_true", help="ecrit sql/01_schema.sql sans se connecter")
    args = parser.parse_args()

    if args.dump_sql:
        (RACINE / "sql" / "01_schema.sql").write_text(ddl_sql(), encoding="utf-8")
        print("DDL ecrit dans sql/01_schema.sql")
        return

    url = get_settings().database_admin_url
    if not url:
        sys.exit("DATABASE_ADMIN_URL n'est pas defini (voir .env.example)")
    engine = create_engine(url)

    if args.reset:
        Base.metadata.drop_all(engine)
        print("Tables supprimees")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        role_existe = conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": ROLE_APP}).first()
        if role_existe:
            for droit in DROITS_APP:
                conn.execute(text(droit))
        else:
            print(f"Role {ROLE_APP} absent : droits non accordes (voir sql/00_roles.sql)")
    print("Tables pretes :", ", ".join(t.name for t in Base.metadata.sorted_tables))


if __name__ == "__main__":
    main()
