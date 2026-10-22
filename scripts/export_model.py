"""
Exporte le modele final du projet 4 (TechNova, prediction de demission) pour l'API.

Memes reglages que la presentation du projet 4 :
- RandomForest(n_estimators=200, max_depth=4, min_samples_leaf=5, class_weight="balanced")
- meme decoupage train/test (80/20, stratifie, random_state=42)
- seuil de decision choisi en validation croisee sur le train (max F2-score)

Entree : data/employes.csv (DataFrame fusionne du projet 4)
Sortie : app/ml/model.joblib (modele + colonnes + seuil + metriques)

Lancer depuis la racine du depot : python scripts/export_model.py
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))  # pour importer app.* quand on lance le script directement

from app.ml.preprocessing import COLONNES_QUALITATIVES, preparer_features  # noqa: E402

DONNEES = RACINE / "data" / "employes.csv"
SORTIE = RACINE / "app" / "ml" / "model.joblib"
MODEL_VERSION = "1.0.0"
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(DONNEES)
    X = preparer_features(df)  # 39 colonnes, identiques a data/etape_2_X.csv du projet 4
    y = (df["a_quitte_l_entreprise"] == "Oui").astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    model = RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=5,
                                   class_weight="balanced", random_state=RANDOM_STATE)

    # seuil choisi sur des probabilites "hors pli" du train, jamais sur le test
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    probas_cv = cross_val_predict(model, X_train, y_train, cv=cv, method="predict_proba")[:, 1]
    precisions, rappels, seuils = precision_recall_curve(y_train, probas_cv)
    f2 = 5 * precisions * rappels / (4 * precisions + rappels + 1e-9)
    seuil = float(seuils[int(np.argmax(f2[:-1]))])

    model.fit(X_train, y_train)
    probas_test = model.predict_proba(X_test)[:, 1]
    preds_test = (probas_test >= seuil).astype(int)
    vn, fp, fn, vp = confusion_matrix(y_test, preds_test).ravel()

    metriques = {
        "rappel": round(recall_score(y_test, preds_test), 4),
        "precision": round(precision_score(y_test, preds_test), 4),
        "f2": round(fbeta_score(y_test, preds_test, beta=2), 4),
        "roc_auc": round(roc_auc_score(y_test, probas_test), 4),
        "vrais_positifs": int(vp), "faux_positifs": int(fp),
        "faux_negatifs": int(fn), "vrais_negatifs": int(vn),
    }

    artefact = {
        "model": model,
        "feature_columns": list(X.columns),
        "threshold": seuil,
        "categories": {c: sorted(df[c].dropna().unique().tolist()) for c in COLONNES_QUALITATIVES},
        "model_version": MODEL_VERSION,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "metrics_test": metriques,
    }
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefact, SORTIE, compress=3)

    print(f"Modele sauvegarde : {SORTIE.relative_to(RACINE)}")
    print(f"Colonnes : {len(artefact['feature_columns'])} | seuil F2 : {seuil:.3f}")
    print(f"Test : {metriques}")


if __name__ == "__main__":
    main()
