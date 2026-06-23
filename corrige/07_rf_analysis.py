"""
VOLET LABORATOIRE — Exploitation du Random Forest avec la variable ESSAI.

L'identifiant des moucherons encode un numéro d'essai expérimental :
    "<essai>-<strain> <dpi>dpi <individu>"   ex. "2-BTV3 6dpi 100"
Le pipeline initial l'ignorait. Or cette variable révèle une INTERACTION forte
essai × sérotype : le sérotype qui réplique le plus s'INVERSE entre les deux
essais. Regrouper les essais (comme le faisait 04) produit donc une conclusion
confondue (paradoxe de Simpson).

Ce script exploite le RF pour ce qu'il fait de mieux — capter des interactions —
et tester la reproductibilité :

  A. RF EN RÉGRESSION  : log_copies ~ strain + dpi + essai
       -> R² + importance par PERMUTATION (essai pèse-t-il autant que strain ?)
  B. GRAPHE D'INTERACTION essai × sérotype (montre l'inversion)
  C. VALIDATION INTER-ESSAIS : entraîner sur un essai, tester sur l'autre
       -> si l'accuracy s'effondre, la relation charge↔sérotype n'est pas
          reproductible (résultat honnête et fort).

Produit (artifacts_lab/) :
  rf_kinetics_by_essai.png, rf_interaction_essai_strain.png,
  rf_analysis_report.md, rf_analysis_stats.json

Usage :
    python 07_rf_analysis.py --csv "../01_BTV copy numbers midge.csv"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, r2_score
from sklearn.model_selection import train_test_split

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = Path("artifacts_lab")
COLORS = {"BTV3": "#6366F1", "BTV8": "#F59E0B", "NC": "#10B981"}


# --------------------------------------------------------------------------- #
def load(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";", encoding="latin-1")
    df.columns = ["midge_id", "copies"]
    df["copies"] = pd.to_numeric(df["copies"], errors="coerce")
    df = df.dropna(subset=["copies"]).reset_index(drop=True)

    def parse(s):
        s = str(s)
        essai = re.match(r"\s*(\d+)\s*-", s)
        strain = next((c for c in ("BTV3", "BTV8", "NC") if c in s), "?")
        dpi = re.search(r"(\d+)\s*dpi", s, re.IGNORECASE)
        return (int(essai.group(1)) if essai else -1, strain,
                int(dpi.group(1)) if dpi else -1)

    df[["essai", "strain", "dpi"]] = df["midge_id"].apply(lambda s: pd.Series(parse(s)))
    df = df[(df.strain != "?") & (df.essai > 0)].reset_index(drop=True)
    df["log_copies"] = np.log10(df["copies"] + 1)
    return df


def df_to_md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    head = "| " + " | ".join(map(str, cols)) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


# --------------------------------------------------------------------------- #
#  A. RF en régression : qui explique la charge virale ?                      #
# --------------------------------------------------------------------------- #
def rf_regression(df: pd.DataFrame) -> dict:
    inf = df[df.strain != "NC"].copy()           # NC = 0 copie -> on étudie la réplication
    inf["is_btv8"] = (inf.strain == "BTV8").astype(int)
    X = inf[["is_btv8", "dpi", "essai"]].values
    y = inf["log_copies"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42)

    rf = RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=1)
    rf.fit(Xtr, ytr)
    r2 = r2_score(yte, rf.predict(Xte))

    perm = permutation_importance(rf, Xte, yte, n_repeats=30, random_state=42, n_jobs=1)
    names = ["sérotype (BTV8?)", "dpi", "essai"]
    imp = {n: round(float(m), 3) for n, m in zip(names, perm.importances_mean)}
    return {"r2_test": round(float(r2), 3), "permutation_importance": imp}


# --------------------------------------------------------------------------- #
#  C. Validation inter-essais (reproductibilité) : BTV3 vs BTV8 à 6 dpi       #
# --------------------------------------------------------------------------- #
def cross_trial(df: pd.DataFrame) -> dict:
    sub = df[(df.strain != "NC") & (df.dpi == 6)].copy()
    feat = ["log_copies"]

    def acc(train_essai, test_essai):
        tr = sub[sub.essai == train_essai]
        te = sub[sub.essai == test_essai]
        clf = RandomForestClassifier(n_estimators=300, random_state=42,
                                     class_weight="balanced", n_jobs=1)
        clf.fit(tr[feat].values, tr.strain.values)
        return round(accuracy_score(te.strain.values, clf.predict(te[feat].values)), 3)

    # baseline "majorité" sur l'ensemble
    chance = round(max((sub.strain == c).mean() for c in ("BTV3", "BTV8")), 3)
    # référence intra (split aléatoire, essais mélangés)
    Xtr, Xte, ytr, yte = train_test_split(sub[feat].values, sub.strain.values,
                                          test_size=0.25, random_state=42, stratify=sub.strain)
    clf = RandomForestClassifier(n_estimators=300, random_state=42,
                                 class_weight="balanced", n_jobs=1).fit(Xtr, ytr)
    intra = round(accuracy_score(yte, clf.predict(Xte)), 3)

    return {"chance_majorite": chance, "intra_essais_melanges": intra,
            "train_essai1_test_essai2": acc(1, 2),
            "train_essai2_test_essai1": acc(2, 1)}


# --------------------------------------------------------------------------- #
#  Figures                                                                    #
# --------------------------------------------------------------------------- #
def plot_kinetics_by_essai(df: pd.DataFrame) -> None:
    essais = sorted(df.essai.unique())
    fig, axes = plt.subplots(1, len(essais), figsize=(11, 4.5), sharey=True)
    for ax, e in zip(np.atleast_1d(axes), essais):
        order, data, labels, colors = [("BTV3", 6), ("BTV8", 6)], [], [], []
        for s, d in order:
            v = df[(df.essai == e) & (df.strain == s) & (df.dpi == d)]["log_copies"].values
            data.append(v); labels.append(f"{s}\n{d}dpi"); colors.append(COLORS[s])
        bp = ax.boxplot(data, labels=labels, patch_artist=True, showmeans=True,
                        medianprops=dict(color="black"))
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c); patch.set_alpha(0.65)
        ax.set_title(f"Essai {e}"); ax.grid(axis="y", alpha=0.3)
    np.atleast_1d(axes)[0].set_ylabel("log10(copies + 1)")
    fig.suptitle("Charge virale à 6 dpi — stratifiée par essai (l'effet sérotype s'inverse)")
    fig.tight_layout()
    fig.savefig(OUT / "rf_kinetics_by_essai.png", dpi=150)
    plt.close(fig)


def plot_interaction(df: pd.DataFrame) -> None:
    sub = df[(df.strain != "NC") & (df.dpi == 6)]
    piv = sub.groupby(["essai", "strain"])["log_copies"].mean().unstack()
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for s in ("BTV3", "BTV8"):
        ax.plot(piv.index, piv[s], marker="o", linewidth=2.5, label=s, color=COLORS[s])
    ax.set_xticks(piv.index); ax.set_xlabel("Essai")
    ax.set_ylabel("log10(copies + 1) moyen — 6 dpi")
    ax.set_title("Interaction essai × sérotype\n(les courbes se croisent → effet non reproductible)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "rf_interaction_essai_strain.png", dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- #
def write_report(df: pd.DataFrame, reg: dict, cross: dict) -> None:
    sub = df[(df.strain != "NC") & (df.dpi == 6)]
    desc = (sub.groupby(["essai", "strain"])["copies"]
            .agg(n="count", mediane="median",
                 pct_detectable=lambda x: round(100 * (x > 0).mean(), 1))
            .round(1).reset_index())

    L = ["# Exploitation du Random Forest avec la variable ESSAI\n",
         "## 1. Effectifs et charge virale par essai × sérotype (6 dpi)\n",
         df_to_md(desc),
         "\n> L'effet du sérotype **s'inverse** entre les essais : regrouper les "
         "essais (comme le faisait `04_lab_kinetics_analysis.py`) est donc confondu "
         "(paradoxe de Simpson). Il faut **stratifier par essai**.\n",
         "\n## 2. RF en régression — log_copies ~ sérotype + dpi + essai\n",
         f"- R² (test) = **{reg['r2_test']}**",
         "- Importance par permutation (plus c'est haut, plus la variable explique la charge) :"]
    for k, v in sorted(reg["permutation_importance"].items(), key=lambda kv: -kv[1]):
        L.append(f"  - **{k}** : {v}")
    L += ["\n> Le RF capte automatiquement l'interaction. Si `essai` pèse autant ou "
          "plus que le sérotype, la charge virale n'est pas un marqueur stable du sérotype.\n",
          "\n## 3. Validation inter-essais (reproductibilité) — BTV3 vs BTV8 à 6 dpi\n",
          f"- Niveau du hasard (classe majoritaire) : **{cross['chance_majorite']}**",
          f"- Intra (essais mélangés, split aléatoire) : **{cross['intra_essais_melanges']}**",
          f"- Train essai 1 → test essai 2 : **{cross['train_essai1_test_essai2']}**",
          f"- Train essai 2 → test essai 1 : **{cross['train_essai2_test_essai1']}**",
          "\n> Si l'accuracy inter-essais tombe au niveau (ou en dessous) du hasard, "
          "le modèle appris sur un essai ne se transfère pas à l'autre : la relation "
          "charge↔sérotype **n'est pas reproductible**. C'est LE résultat à retenir.\n"]
    (OUT / "rf_analysis_report.md").write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="../01_BTV copy numbers midge.csv")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    df = load(Path(args.csv))
    print(f"{len(df)} individus | essais : {sorted(df.essai.unique())}")

    reg = rf_regression(df)
    cross = cross_trial(df)
    plot_kinetics_by_essai(df)
    plot_interaction(df)
    write_report(df, reg, cross)
    (OUT / "rf_analysis_stats.json").write_text(
        json.dumps({"regression": reg, "cross_trial": cross}, indent=2, ensure_ascii=False),
        encoding="utf-8")

    print("\n--- RF régression (charge virale) ---")
    print("  R² test :", reg["r2_test"])
    print("  importance permutation :", reg["permutation_importance"])
    print("\n--- Validation inter-essais (BTV3 vs BTV8) ---")
    for k, v in cross.items():
        print(f"  {k} : {v}")
    print(f"\n✅ Figures + rapport dans : {OUT}/")


if __name__ == "__main__":
    main()
