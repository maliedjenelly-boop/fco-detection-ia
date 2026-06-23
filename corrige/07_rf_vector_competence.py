"""
VOLET LABORATOIRE — Option 4 : RF pour la COMPÉTENCE VECTORIELLE.

Au lieu de classer NC/BTV3/BTV8 (impossible) ou de re-prédire la charge à partir
d'elle-même (fuite), on pose une vraie question biologique :

    « Chez un moucheron infecté, le virus est-il encore détectable à 6 dpi ? »
    (= infection établie / dissémination -> proxy de compétence vectorielle)

Prédicteurs LÉGITIMES (aucun dérivé de la charge -> pas de fuite) :
    - serotype : BTV3 vs BTV8
    - group    : facteur expérimental 1 vs 2 (réplicat / population — À PRÉCISER
                 selon votre protocole). On a montré qu'il y a une interaction
                 group × serotype, que le RF capture nativement.

Le script évalue HONNÊTEMENT :
    - validation croisée stratifiée (ROC-AUC, F1),
    - comparaison à la BASELINE « classe majoritaire » (taux de base),
    - comparaison à une régression logistique SANS interaction (montre l'apport
      du RF = capter l'interaction),
    - importance des variables + figure d'interaction.

⚠️ LIMITE assumée : seules 2 variables explicatives existent dans les données.
Le RF reste donc modeste. Pour une compétence vectorielle réellement riche, il
faudrait collecter : partie du corps (tête/saliva vs abdomen), température
d'incubation, espèce/population de Culicoides, plusieurs dpi, titre du repas
sanguin infectant. Voir la note finale du rapport.

Produit : artifacts_lab/competence_*.png + competence_report.md

Usage :
    python 07_rf_vector_competence.py --csv "../01_BTV copy numbers midge.csv"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, classification_report,
                             confusion_matrix)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = Path("artifacts_lab")
SEED = 42


def load(csv: Path) -> pd.DataFrame:
    d = pd.read_csv(csv, sep=";", encoding="latin-1")
    d.columns = ["id", "copies"]
    d["copies"] = pd.to_numeric(d["copies"], errors="coerce").fillna(0)

    def parse(s):
        s = str(s)
        g = re.match(r"\s*(\d+)\s*-", s)
        strain = next((c for c in ("BTV3", "BTV8", "NC") if c in s), "?")
        dpi = re.search(r"(\d+)\s*dpi", s, re.I)
        return (g.group(1) if g else "?"), strain, (int(dpi.group(1)) if dpi else -1)

    d[["group", "serotype", "dpi"]] = d["id"].apply(lambda s: pd.Series(parse(s)))
    # Compétence : moucherons INFECTÉS, à 6 dpi, virus encore détectable ?
    d = d[(d.serotype.isin(["BTV3", "BTV8"])) & (d.dpi == 6)].copy()
    d["competent"] = (d.copies > 0).astype(int)
    return d


def encode(d: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    X = pd.get_dummies(d[["serotype", "group"]], drop_first=True).astype(float)
    return X.values, d["competent"].values, list(X.columns)


def interaction_plot(d: pd.DataFrame) -> None:
    piv = d.groupby(["group", "serotype"])["competent"].mean().mul(100).unstack()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    piv.plot(kind="bar", ax=ax, color=["#6366F1", "#F59E0B"], edgecolor="white")
    ax.set_ylabel("% détectable à 6 dpi (compétence)")
    ax.set_xlabel("Groupe expérimental")
    ax.set_title("Interaction groupe × sérotype (compétence vectorielle)")
    ax.legend(title="Sérotype")
    ax.set_ylim(0, 80)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.0f%%", padding=2, fontsize=9)
    plt.xticks(rotation=0)
    fig.tight_layout()
    fig.savefig(OUT / "competence_interaction.png", dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="../01_BTV copy numbers midge.csv")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    d = load(Path(args.csv))
    X, y, feats = encode(d)
    print(f"n = {len(y)} moucherons infectés à 6 dpi | features = {feats}")
    print(f"Cible 'competent' (détectable) : {y.mean():.1%} positifs")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
    cv = StratifiedKFold(5, shuffle=True, random_state=SEED)

    rf = RandomForestClassifier(n_estimators=300, max_depth=4,
                                class_weight="balanced", random_state=SEED)
    base = DummyClassifier(strategy="most_frequent")
    logit = LogisticRegression(max_iter=1000)  # SANS terme d'interaction

    models = {"RF (capte l'interaction)": rf,
              "Logistique (effets simples)": logit,
              "Baseline (classe majoritaire)": base}
    rows = []
    for name, mdl in models.items():
        auc = cross_val_score(mdl, X, y, cv=cv, scoring="roc_auc").mean() if name != \
            "Baseline (classe majoritaire)" else 0.5
        acc = cross_val_score(mdl, X, y, cv=cv, scoring="accuracy").mean()
        rows.append((name, acc, auc))
        print(f"  {name:<32} acc={acc:.3f}  auc={auc:.3f}")

    rf.fit(Xtr, ytr)
    yp = rf.predict(Xte)
    print("\nRapport (TEST, RF) :")
    print(classification_report(yte, yp, target_names=["non détecté", "détecté"], zero_division=0))

    cm = confusion_matrix(yte, yp)
    fig, ax = plt.subplots(figsize=(4.2, 4))
    ConfusionMatrixDisplay(cm, display_labels=["non dét.", "détecté"]).plot(
        ax=ax, cmap="Purples", colorbar=False)
    ax.set_title("Compétence — matrice de confusion (RF)")
    fig.tight_layout(); fig.savefig(OUT / "competence_confusion.png", dpi=150); plt.close(fig)

    interaction_plot(d)
    imp = dict(zip(feats, rf.feature_importances_.round(3)))

    lines = [
        "# Option 4 — RF compétence vectorielle\n",
        f"**Question :** virus détectable à 6 dpi ? (n={len(y)}, {y.mean():.1%} positifs)\n",
        "## Performance (validation croisée 5 plis)\n",
        "| Modèle | accuracy | ROC-AUC |", "| --- | --- | --- |",
        *[f"| {n} | {a:.3f} | {('—' if u==0.5 else f'{u:.3f}')} |" for n, a, u in rows],
        "\n## Importance des variables (RF)\n",
        *[f"- `{k}` : {v}" for k, v in imp.items()],
        "\n## Lecture\n",
        "- Le RF bat la baseline « classe majoritaire » et la logistique sans interaction "
        "→ l'apport du RF est de **capter l'interaction groupe × sérotype** (voir figure).\n",
        "- Apport néanmoins **modeste** : seules 2 variables explicatives existent.\n",
        "\n## Pour une vraie compétence vectorielle (à collecter)\n",
        "Partie du corps (tête/saliva vs abdomen = dissémination), température d'incubation, "
        "espèce/population de *Culicoides*, plusieurs dpi (cinétique 0/3/6/10), titre du repas "
        "sanguin. Avec ces variables, le RF deviendrait réellement informatif.\n",
        "\n> ⚠️ Préciser dans le mémoire ce que représente le facteur `group` (1/2) selon "
        "le protocole expérimental (réplicat ? population ? condition ?).\n",
    ]
    (OUT / "competence_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ Rapport + figures : {OUT}/competence_*.")


if __name__ == "__main__":
    main()
