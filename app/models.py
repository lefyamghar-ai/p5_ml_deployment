"""
Tables de la base PostgreSQL (ORM SQLAlchemy).

- employees          : le dataset RH du projet 4 (1 470 employes, avec la cible reelle)
- prediction_inputs  : chaque demande envoyee au modele (donnees de l'employe + origine)
- predictions        : chaque reponse du modele, liee a sa demande (1 pour 1)

Les caracteristiques de l'employe portent les memes noms partout (API, dataset, tables) :
une ligne de employees peut etre envoyee telle quelle au modele.
Types generiques SQLAlchemy : le meme schema fonctionne aussi en SQLite (tests).
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, SmallInteger, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship


class Base(DeclarativeBase):
    __mapper_args__ = {"eager_defaults": True}  # relit created_at (genere par la base) apres l'insertion


class CaracteristiquesEmploye:
    """Les 25 caracteristiques attendues par le modele (communes a employees et prediction_inputs)."""

    age: Mapped[int] = mapped_column(SmallInteger)
    genre: Mapped[str] = mapped_column(String(1))
    revenu_mensuel: Mapped[int] = mapped_column(Integer)
    statut_marital: Mapped[str] = mapped_column(String(20))
    departement: Mapped[str] = mapped_column(String(30))
    poste: Mapped[str] = mapped_column(String(40))
    nombre_experiences_precedentes: Mapped[int] = mapped_column(SmallInteger)
    annee_experience_totale: Mapped[int] = mapped_column(SmallInteger)
    annees_dans_le_poste_actuel: Mapped[int] = mapped_column(SmallInteger)
    satisfaction_employee_environnement: Mapped[int] = mapped_column(SmallInteger)
    note_evaluation_precedente: Mapped[int] = mapped_column(SmallInteger)
    niveau_hierarchique_poste: Mapped[int] = mapped_column(SmallInteger)
    satisfaction_employee_nature_travail: Mapped[int] = mapped_column(SmallInteger)
    satisfaction_employee_equipe: Mapped[int] = mapped_column(SmallInteger)
    satisfaction_employee_equilibre_pro_perso: Mapped[int] = mapped_column(SmallInteger)
    note_evaluation_actuelle: Mapped[int] = mapped_column(SmallInteger)
    heure_supplementaires: Mapped[str] = mapped_column(String(3))
    augementation_salaire_precedente: Mapped[float] = mapped_column(Float)
    nombre_participation_pee: Mapped[int] = mapped_column(SmallInteger)
    nb_formations_suivies: Mapped[int] = mapped_column(SmallInteger)
    distance_domicile_travail: Mapped[int] = mapped_column(SmallInteger)
    niveau_education: Mapped[int] = mapped_column(SmallInteger)
    domaine_etude: Mapped[str] = mapped_column(String(40))
    frequence_deplacement: Mapped[str] = mapped_column(String(20))
    annees_depuis_la_derniere_promotion: Mapped[int] = mapped_column(SmallInteger)

    @declared_attr.directive
    def __table_args__(cls):
        nom = cls.__tablename__
        return (
            CheckConstraint("age BETWEEN 18 AND 70", name=f"ck_{nom}_age"),
            CheckConstraint("revenu_mensuel > 0", name=f"ck_{nom}_revenu"),
            CheckConstraint("heure_supplementaires IN ('Oui', 'Non')", name=f"ck_{nom}_heures_sup"),
            CheckConstraint(
                "satisfaction_employee_environnement BETWEEN 1 AND 4 AND satisfaction_employee_nature_travail "
                "BETWEEN 1 AND 4 AND satisfaction_employee_equipe BETWEEN 1 AND 4 "
                "AND satisfaction_employee_equilibre_pro_perso BETWEEN 1 AND 4",
                name=f"ck_{nom}_satisfactions",
            ),
        )


class Employee(CaracteristiquesEmploye, Base):
    __tablename__ = "employees"

    id_employee: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    annees_dans_l_entreprise: Mapped[int] = mapped_column(SmallInteger)  # non utilisee par le modele
    annes_sous_responsable_actuel: Mapped[int] = mapped_column(SmallInteger)  # non utilisee par le modele
    a_quitte_l_entreprise: Mapped[bool]  # cible reelle, pour comparer aux predictions


class PredictionInput(CaracteristiquesEmploye, Base):
    __tablename__ = "prediction_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    source: Mapped[str] = mapped_column(String(20))  # api, api_batch, employee, script
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id_employee"), index=True)

    prediction: Mapped["Prediction | None"] = relationship(back_populates="input", uselist=False)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("probabilite_depart BETWEEN 0 AND 1", name="ck_predictions_probabilite"),
        CheckConstraint("prediction IN (0, 1)", name="ck_predictions_prediction"),
        Index("ix_predictions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    input_id: Mapped[int] = mapped_column(ForeignKey("prediction_inputs.id", ondelete="CASCADE"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    probabilite_depart: Mapped[float] = mapped_column(Float)
    prediction: Mapped[int] = mapped_column(SmallInteger)
    seuil: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(20))
    latency_ms: Mapped[float] = mapped_column(Float)  # temps de calcul du modele

    input: Mapped[PredictionInput] = relationship(back_populates="prediction")
