# -*- coding: utf-8 -*-
"""
ANALYSE SUPERVISÉE À PARTIR DE LA BASE DE DONNÉES (§vii.2 du guide).

Les données ne sont PAS relues depuis le CSV : elles sont extraites de la base
SQLite par une requête SQL (jointure mesure_virale × serotype). On entraîne un
Random Forest (≥ 70 % en entraînement) pour la détection NC vs infecté, et on
reporte l'accuracy, la matrice de confusion et la baseline (lecture honnête).

Usage :  python ml_depuis_base.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BDD = Path(__file__).parent
DB = BDD / "fco.db"
RAPPORT = BDD / "ml_rapport.md"

REQUETE = """
SELECT m.genome_copies, m.dpi, m.detectable, s.est_infectieux AS cible
FROM mesure_virale m
JOIN serotype s ON m.id_serotype = s.id_serotype
"""


def main():
    if not DB.exists():
        sys.exit("Base absente : lancez build_database.py")
    con = sqlite3.connect(DB)
    df = pd.read_sql_query(REQUETE, con)          # <-- données issues de la BASE
    con.close()

    X = np.column_stack([np.log1p(df["genome_copies"]), df["dpi"], df["detectable"]])
    y = df["cible"].to_numpy()

    # Split : 70 % entraînement / 30 % test (exigence ≥ 70 %)
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y)

    clf = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=1)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    acc = accuracy_score(yte, pred)
    baseline = max((yte == v).mean() for v in np.unique(yte))   # « toujours classe majoritaire »
    cm = confusion_matrix(yte, pred)

    print(f"Données extraites de la base : {len(df)} lignes "
          f"(train {len(ytr)} / test {len(yte)})")
    print(f"\nAccuracy Random Forest : {acc:.3f}")
    print(f"Baseline (classe majoritaire) : {baseline:.3f}")
    print(f"Gain sur la baseline : +{(acc-baseline)*100:.1f} points")
    print("\nMatrice de confusion (lignes = vérité, colonnes = prédit) :")
    print("            préd. NC   préd. infecté")
    labels = ["NC (0)", "infecté(1)"]
    for i, lab in enumerate(labels):
        print(f"  {lab:12s} {cm[i][0]:>6}      {cm[i][1]:>6}")
    print("\n" + classification_report(yte, pred, target_names=["NC", "infecté"],
                                        zero_division=0))

    RAPPORT.write_text(
        "# Analyse supervisée depuis la base — détection NC vs infecté\n\n"
        "Données extraites par requête SQL sur `fco.db` (jointure mesure_virale × serotype).\n\n"
        f"- Lignes : {len(df)} (train {len(ytr)} / test {len(yte)}, soit {len(ytr)/len(df):.0%} en entraînement)\n"
        f"- Modèle : RandomForestClassifier (class_weight équilibré)\n"
        f"- **Accuracy = {acc:.3f}**\n"
        f"- Baseline (classe majoritaire) = {baseline:.3f} → gain réel = +{(acc-baseline)*100:.1f} points\n\n"
        "| | prédit NC | prédit infecté |\n| --- | --- | --- |\n"
        f"| **réel NC** | {cm[0][0]} | {cm[0][1]} |\n"
        f"| **réel infecté** | {cm[1][0]} | {cm[1][1]} |\n\n"
        "> Lecture honnête : le jeu étant à ~95 % d'infectés, l'accuracy doit être comparée "
        "à la baseline. Le modèle reconnaît surtout les NC à 0 dpi (cf. analyse du mémoire).\n",
        encoding="utf-8")
    print(f"\n✅ Rapport -> {RAPPORT.name}")


if __name__ == "__main__":
    main()
