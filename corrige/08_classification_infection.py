# -*- coding: utf-8 -*-
"""
CLASSIFICATION BINAIRE — culicoïde infecté (détectable) vs non détecté.

Label biologique : genome_copies > 0  ->  1 (infecté/détecté), sinon 0.

⚠️ ANTI-FUITE DE DONNÉES : le label étant DÉFINI par la charge virale, utiliser
`genome_copies` (ou log/seuil) comme variable serait circulaire (AUC = 1 triviale,
inexploitable). On prédit donc la détectabilité à partir des CONDITIONS
EXPÉRIMENTALES lues dans l'identifiant : sérotype, DPI, essai. C'est un vrai
problème (modéliser la probabilité de détection / compétence vectorielle).

Modèles comparés : Logistic Regression, Random Forest, XGBoost.
Métriques : accuracy, F1, ROC-AUC. + gestion du déséquilibre, importance des
variables, validation croisée, et distribution des charges virales.

Usage :  python 08_classification_infection.py --csv "../01_BTV copy numbers midge.csv"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = Path("artifacts_lab")
FEATURES = ["dpi", "essai", "is_BTV3", "is_BTV8"]   # NC = référence (les deux à 0)


def load(csv: Path) -> pd.DataFrame:
    df = pd.read_csv(csv, sep=";", encoding="latin-1")
    df.columns = ["midge_id", "copies"]
    df["copies"] = pd.to_numeric(df["copies"], errors="coerce").fillna(0.0)

    def parse(s):
        s = str(s)
        e = re.match(r"\s*(\d+)\s*-", s)
        strain = next((c for c in ("BTV3", "BTV8", "NC") if c in s), None)
        d = re.search(r"(\d+)\s*dpi", s, re.IGNORECASE)
        return (int(e.group(1)) if e else None, strain, int(d.group(1)) if d else None)

    df[["essai", "serotype", "dpi"]] = df["midge_id"].apply(lambda s: pd.Series(parse(s)))
    df = df.dropna(subset=["essai", "serotype", "dpi"]).reset_index(drop=True)
    df["label"] = (df["copies"] > 0).astype(int)
    df["is_BTV3"] = (df["serotype"] == "BTV3").astype(int)
    df["is_BTV8"] = (df["serotype"] == "BTV8").astype(int)
    return df


def build_models(y_train):
    neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    spw = neg / pos if pos else 1.0
    return {
        "Logistic Regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(class_weight="balanced", max_iter=1000)),
        "Random Forest": RandomForestClassifier(
            n_estimators=400, class_weight="balanced", random_state=42, n_jobs=1),
        "XGBoost": XGBClassifier(
            n_estimators=400, max_depth=4, learning_rate=0.1,
            scale_pos_weight=spw, eval_metric="logloss", random_state=42,
            n_jobs=1, verbosity=0),
    }


def plot_distribution(df):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for strain, color in [("NC", "#10B981"), ("BTV3", "#6366F1"), ("BTV8", "#F59E0B")]:
        vals = np.log10(df[df.serotype == strain]["copies"] + 1)
        ax.hist(vals, bins=30, alpha=0.6, label=strain, color=color)
    ax.set_xlabel("Charge virale  log10(copies + 1)")
    ax.set_ylabel("Nombre d'individus")
    ax.set_title("Distribution des charges virales par sérotype\n(le pic à 0 = individus non détectés)")
    ax.legend()
    fig.tight_layout(); fig.savefig(OUT / "charge_distribution.png", dpi=150); plt.close(fig)


def plot_roc(models, X_test, y_test):
    fig, ax = plt.subplots(figsize=(6, 5.5))
    for name, m in models.items():
        proba = m.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, proba)
        ax.plot(fpr, tpr, lw=2, label=f"{name} (AUC={roc_auc_score(y_test, proba):.3f})")
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=1)
    ax.set_xlabel("Taux de faux positifs"); ax.set_ylabel("Taux de vrais positifs")
    ax.set_title("Courbes ROC"); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(OUT / "roc_curves.png", dpi=150); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="../01_BTV copy numbers midge.csv")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    df = load(Path(args.csv))
    X, y = df[FEATURES], df["label"].to_numpy()
    n0, n1 = int((y == 0).sum()), int((y == 1).sum())
    print(f"{len(df)} individus | label 0 (non détecté) = {n0} | label 1 (détecté) = {n1} "
          f"({n1/len(df):.0%}) → jeu quasi équilibré")
    print(f"Variables (sans fuite) : {FEATURES}\n")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
    models = build_models(ytr)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    rows = []
    for name, m in models.items():
        m.fit(Xtr, ytr)
        proba = m.predict_proba(Xte)[:, 1]
        pred = (proba >= 0.5).astype(int)
        cvres = cross_validate(m, X, y, cv=cv, scoring=["roc_auc", "f1", "accuracy"])
        rows.append({
            "Modèle": name,
            "Accuracy": accuracy_score(yte, pred),
            "F1": f1_score(yte, pred),
            "ROC-AUC": roc_auc_score(yte, proba),
            "AUC (CV 5-fold)": f"{cvres['test_roc_auc'].mean():.3f} ± {cvres['test_roc_auc'].std():.3f}",
        })
    res = pd.DataFrame(rows)
    print("=== Comparaison des modèles (jeu de test) ===")
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    # Importance des variables
    print("\n=== Importance des variables ===")
    rf = models["Random Forest"]; xgb = models["XGBoost"]
    lr = models["Logistic Regression"].named_steps["logisticregression"]
    imp = pd.DataFrame({
        "Variable": FEATURES,
        "RF": rf.feature_importances_,
        "XGBoost": xgb.feature_importances_,
        "LR (coef)": lr.coef_[0],
    })
    print(imp.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    plot_distribution(df)
    plot_roc(models, Xte, yte)

    # Démonstration de la FUITE (pour le mémoire) : si on inclut la charge -> AUC triviale
    from sklearn.linear_model import LogisticRegression as LR2
    leak = LR2(max_iter=1000).fit(Xtr.assign(detectable=(df.loc[Xtr.index, "copies"] > 0)),
                                  ytr)
    leak_auc = roc_auc_score(yte, leak.predict_proba(
        Xte.assign(detectable=(df.loc[Xte.index, "copies"] > 0)))[:, 1])
    print(f"\n[Démo fuite] En ajoutant la charge comme variable : AUC = {leak_auc:.3f} "
          "(triviale et inexploitable — à NE PAS faire).")

    # Rapport
    md = ["# Classification binaire — infecté (détecté) vs non détecté\n",
          f"- Individus : {len(df)} | label 0 = {n0}, label 1 = {n1} (jeu quasi équilibré)\n",
          f"- Variables (anti-fuite) : {', '.join(FEATURES)} ; la charge virale est EXCLUE (elle définit le label)\n",
          "\n## Comparaison des modèles\n", "```\n" + res.to_string(index=False) + "\n```",
          "\n## Importance des variables\n", "```\n" + imp.to_string(index=False) + "\n```",
          f"\n\n> Démonstration de fuite : inclure la charge donne AUC = {leak_auc:.2f} (trivial). "
          "On l'évite volontairement.\n",
          "\nFigures : charge_distribution.png, roc_curves.png\n"]
    try:
        (OUT / "classification_rapport.md").write_text("\n".join(md), encoding="utf-8")
    except Exception:
        pass
    print(f"\n✅ Figures + rapport dans : {OUT}/")


if __name__ == "__main__":
    main()
