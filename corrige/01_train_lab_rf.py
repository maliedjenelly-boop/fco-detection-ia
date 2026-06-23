"""
VOLET LABORATOIRE — Random Forest propre pour les données de charge virale BTV.

Ce script remplace la logique défectueuse de l'ancien projet :
  - PLUS de "labels dérivés des features" (fuite de données / data leakage).
  - Les vraies étiquettes (NC / BTV3 / BTV8) et le DPI sont extraits de la
    colonne midge-ID, qui les contient réellement (ex : "1-BTV3 6dpi 12").
  - Transformation log des copies génomiques (dynamique 0 -> 4.3e8).
  - Split stratifié + validation croisée + class_weight pour le déséquilibre.
  - Évaluation honnête : accuracy, rapport de classification, matrice de
    confusion, importance des variables.

IMPORTANT (constat scientifique, voir le rapport) :
  La charge virale ne permet PAS de distinguer BTV3 de BTV8 (sérotypes non
  identifiables par le nombre de copies). Ce script démontre cette limite et
  propose, en plus, la tâche réellement réalisable : "détection d'infection"
  (NC vs infecté). On entraîne donc DEUX modèles et on compare.

Usage :
    python 01_train_lab_rf.py --csv "../01_BTV copy numbers midge.csv"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Console Windows : forcer l'UTF-8 pour éviter les UnicodeEncodeError (emojis).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

RANDOM_STATE = 42
OUT_DIR = Path("artifacts_lab")


# --------------------------------------------------------------------------- #
# 1. Chargement et parsing des VRAIES étiquettes                              #
# --------------------------------------------------------------------------- #
def load_raw(csv_path: Path) -> pd.DataFrame:
    """Charge le CSV brut (séparateur ';', en-têtes avec espaces parasites)."""
    df = pd.read_csv(csv_path, sep=";", encoding="latin-1")
    df.columns = ["midge_id", "genome_copies"]
    df["genome_copies"] = pd.to_numeric(df["genome_copies"], errors="coerce")
    df = df.dropna(subset=["genome_copies"]).reset_index(drop=True)
    return df


def parse_label_and_dpi(midge_id: str) -> tuple[str, int]:
    """Extrait la classe (NC/BTV3/BTV8) et le DPI depuis l'identifiant."""
    s = str(midge_id)
    if "BTV3" in s:
        cls = "BTV3"
    elif "BTV8" in s:
        cls = "BTV8"
    elif "NC" in s:
        cls = "NC"
    else:
        cls = "UNKNOWN"
    m = re.search(r"(\d+)\s*dpi", s, flags=re.IGNORECASE)
    dpi = int(m.group(1)) if m else -1
    return cls, dpi


def build_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Construit les features SANS jamais dériver le label d'une feature."""
    df = df.copy()
    df[["strain", "dpi"]] = df["midge_id"].apply(
        lambda s: pd.Series(parse_label_and_dpi(s))
    )
    df = df[df["strain"] != "UNKNOWN"].reset_index(drop=True)

    # Feature engineering honnête : la charge virale s'étend sur ~8 ordres de
    # grandeur -> log1p. On ajoute un indicateur "détectable" (copies > 0).
    df["log_copies"] = np.log1p(df["genome_copies"])
    df["is_detectable"] = (df["genome_copies"] > 0).astype(int)
    return df


# --------------------------------------------------------------------------- #
# 2. Entraînement générique d'un Random Forest propre                         #
# --------------------------------------------------------------------------- #
def train_rf(
    df: pd.DataFrame,
    target: str,
    feature_cols: list[str],
    title: str,
) -> dict:
    """Entraîne, valide et évalue un RandomForest. Retourne un dict d'artefacts."""
    print("\n" + "=" * 70)
    print(f"  MODÈLE : {title}")
    print("=" * 70)

    X = df[feature_cols].values
    y = df[target].values

    print("Distribution des classes :")
    print(pd.Series(y).value_counts(), "\n")

    # Split stratifié (préserve les proportions dans train ET test).
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",  # gère le déséquilibre (NC minoritaire)
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    # Validation croisée stratifiée -> estimation honnête, robuste au hasard du split.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_f1 = cross_val_score(model, X, y, cv=cv, scoring="f1_macro")
    print(f"F1-macro (CV 5 folds) : {cv_f1.mean():.3f} ± {cv_f1.std():.3f}")

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Accuracy train : {train_acc:.3f}")
    print(f"Accuracy test  : {test_acc:.3f}")
    if train_acc - test_acc > 0.15:
        print("⚠️  Écart train/test important -> surapprentissage probable.")

    print("\nRapport de classification (test) :")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Matrice de confusion
    labels = sorted(np.unique(y))
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    OUT_DIR.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 4))
    ConfusionMatrixDisplay(cm, display_labels=labels).plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"Matrice de confusion — {title}")
    fig.tight_layout()
    cm_path = OUT_DIR / f"confusion_{target}.png"
    fig.savefig(cm_path, dpi=150)
    plt.close(fig)
    print(f"Matrice de confusion sauvée : {cm_path}")

    # Importance des variables
    importances = dict(zip(feature_cols, model.feature_importances_))
    print("\nImportance des variables :")
    for f, imp in sorted(importances.items(), key=lambda kv: -kv[1]):
        print(f"   {f:<15} {imp:.3f}")

    return {
        "model": model,
        "features": feature_cols,
        "classes": labels,
        "cv_f1_mean": float(cv_f1.mean()),
        "test_acc": float(test_acc),
        "importances": importances,
    }


# --------------------------------------------------------------------------- #
# 3. Main                                                                     #
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="../01_BTV copy numbers midge.csv")
    args = parser.parse_args()

    df = build_dataset(load_raw(Path(args.csv)))
    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_DIR / "dataset_clean.csv", index=False)

    features = ["log_copies", "dpi", "is_detectable"]

    # --- Tâche A : la tâche demandée à l'origine (NC / BTV3 / BTV8) -------- #
    # On la fait PROPREMENT pour MONTRER objectivement qu'elle est mal posée :
    # BTV3 et BTV8 seront massivement confondus dans la matrice de confusion.
    art_3cls = train_rf(
        df, target="strain", feature_cols=features,
        title="3 classes NC/BTV3/BTV8 (tâche d'origine — voir limites)",
    )

    # --- Tâche B : la tâche réellement réalisable -> détection d'infection - #
    df["infected"] = np.where(df["strain"] == "NC", "NC", "INFECTE")
    art_detect = train_rf(
        df, target="infected", feature_cols=features,
        title="Détection : NC vs INFECTÉ (tâche scientifiquement valide)",
    )

    # On sauvegarde le modèle de DÉTECTION (le seul réellement exploitable).
    bundle = {
        "model": art_detect["model"],
        "features": art_detect["features"],
        "classes": art_detect["classes"],
        "task": "infection_detection",
        "metrics": {k: art_detect[k] for k in ("cv_f1_mean", "test_acc")},
        "note": (
            "Modèle de DETECTION (NC vs infecté). Le classifieur 3 classes "
            "NC/BTV3/BTV8 n'est PAS exploitable : la charge virale ne distingue "
            "pas les sérotypes (cf. matrice de confusion)."
        ),
    }
    joblib.dump(bundle, OUT_DIR / "fco_lab_model.joblib")
    print(f"\n✅ Modèle sauvegardé : {OUT_DIR / 'fco_lab_model.joblib'}")
    print("\nRÉSUMÉ :")
    print(f"  3 classes  -> F1-macro CV = {art_3cls['cv_f1_mean']:.3f} (faible : BTV3/BTV8 confondus)")
    print(f"  Détection  -> F1-macro CV = {art_detect['cv_f1_mean']:.3f}")


if __name__ == "__main__":
    main()
