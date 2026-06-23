"""
VOLET LABORATOIRE — Analyse de la cinétique de réplication virale (BTV).

Au lieu d'un classifieur faible (BTV3 vs BTV8 non séparables), on exploite ce
que la donnée contient VRAIMENT : la dynamique de la charge virale selon le
sérotype et le temps post-infection (DPI). C'est une analyse statistique
descriptive + inférentielle, bien plus solide scientifiquement.

Produit (dans artifacts_lab/) :
  - kinetics_boxplot.png        : distribution (log) des copies par sérotype × DPI
  - detection_rate.png          : % d'individus détectables (copies > 0) par groupe
  - kinetics_summary.md         : tableau descriptif + résultats des tests
  - kinetics_stats.json         : résultats bruts (pour le mémoire)

Tests utilisés (données très asymétriques, beaucoup de zéros -> non-paramétrique) :
  - Mann-Whitney U : BTV3 vs BTV8 (charge virale)
  - Kruskal-Wallis : effet global du sérotype
  - Fisher exact   : différence des taux de détection (proportion copies > 0)

Usage :
    python 04_lab_kinetics_analysis.py --csv "../01_BTV copy numbers midge.csv"
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
from scipy import stats

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = Path("artifacts_lab")
STRAIN_COLORS = {"NC": "#10B981", "BTV3": "#6366F1", "BTV8": "#F59E0B"}


# --------------------------------------------------------------------------- #
def load(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, sep=";", encoding="latin-1")
    df.columns = ["midge_id", "copies"]
    df["copies"] = pd.to_numeric(df["copies"], errors="coerce")
    df = df.dropna(subset=["copies"]).reset_index(drop=True)

    def parse(s):
        s = str(s)
        cls = next((c for c in ("BTV3", "BTV8", "NC") if c in s), "UNKNOWN")
        m = re.search(r"(\d+)\s*dpi", s, re.IGNORECASE)
        return cls, (int(m.group(1)) if m else -1)

    df[["strain", "dpi"]] = df["midge_id"].apply(lambda s: pd.Series(parse(s)))
    df = df[df["strain"] != "UNKNOWN"].reset_index(drop=True)
    df["log_copies"] = np.log10(df["copies"] + 1)
    df["detectable"] = df["copies"] > 0
    return df


# --------------------------------------------------------------------------- #
def descriptive(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["strain", "dpi"])
    tab = g["copies"].agg(
        n="count",
        pct_detectable=lambda x: 100 * (x > 0).mean(),
        median="median",
        mean="mean",
        max="max",
    ).round(1)
    return tab.reset_index()


def run_tests(df: pd.DataFrame) -> dict:
    res = {}

    # 1) Sérotype : BTV3 vs BTV8 sur la charge (log), au pic d'infection (6 dpi)
    sub = df[df.dpi == 6]
    b3 = sub[sub.strain == "BTV3"]["copies"]
    b8 = sub[sub.strain == "BTV8"]["copies"]
    if len(b3) and len(b8):
        u, p = stats.mannwhitneyu(b3, b8, alternative="two-sided")
        res["BTV3_vs_BTV8_6dpi"] = {
            "test": "Mann-Whitney U", "U": float(u), "p_value": float(p),
            "median_BTV3": float(b3.median()), "median_BTV8": float(b8.median()),
            "significatif_5pct": bool(p < 0.05),
        }

    # 2) Effet global du sérotype (infectés seulement)
    inf = df[(df.strain != "NC") & (df.dpi == 6)]
    groups = [g["copies"].values for _, g in inf.groupby("strain")]
    if len(groups) >= 2:
        h, p = stats.kruskal(*groups)
        res["kruskal_serotype_6dpi"] = {"test": "Kruskal-Wallis", "H": float(h),
                                        "p_value": float(p), "significatif_5pct": bool(p < 0.05)}

    # 3) Effet du DPI (0 vs 6) au sein de chaque sérotype infecté
    res["effet_dpi"] = {}
    for s in ("BTV3", "BTV8"):
        d0 = df[(df.strain == s) & (df.dpi == 0)]["copies"]
        d6 = df[(df.strain == s) & (df.dpi == 6)]["copies"]
        if len(d0) and len(d6):
            u, p = stats.mannwhitneyu(d6, d0, alternative="greater")
            res["effet_dpi"][s] = {"p_value": float(p),
                                   "median_0dpi": float(d0.median()),
                                   "median_6dpi": float(d6.median()),
                                   "augmente_avec_dpi": bool(p < 0.05)}

    # 4) Taux de détection BTV3 vs BTV8 (proportion copies > 0) à 6 dpi
    if len(b3) and len(b8):
        table = [[int((b3 > 0).sum()), int((b3 == 0).sum())],
                 [int((b8 > 0).sum()), int((b8 == 0).sum())]]
        odds, p = stats.fisher_exact(table)
        res["taux_detection_6dpi"] = {"test": "Fisher exact", "odds_ratio": float(odds),
                                      "p_value": float(p),
                                      "pct_detectable_BTV3": round(100 * (b3 > 0).mean(), 1),
                                      "pct_detectable_BTV8": round(100 * (b8 > 0).mean(), 1),
                                      "significatif_5pct": bool(p < 0.05)}
    return res


# --------------------------------------------------------------------------- #
def plot_boxplot(df: pd.DataFrame) -> None:
    order = [("NC", 0), ("NC", 6), ("BTV3", 0), ("BTV3", 6), ("BTV8", 0), ("BTV8", 6)]
    data, labels, colors = [], [], []
    for s, d in order:
        vals = df[(df.strain == s) & (df.dpi == d)]["log_copies"].values
        if len(vals):
            data.append(vals)
            labels.append(f"{s}\n{d} dpi")
            colors.append(STRAIN_COLORS[s])
    fig, ax = plt.subplots(figsize=(9, 5))
    bp = ax.boxplot(data, labels=labels, patch_artist=True, showmeans=True,
                    medianprops=dict(color="black"))
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.65)
    ax.set_ylabel("Charge virale  log10(copies + 1)")
    ax.set_title("Cinétique de la charge virale par sérotype et DPI")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "kinetics_boxplot.png", dpi=150)
    plt.close(fig)


def plot_detection(df: pd.DataFrame) -> None:
    piv = (df.groupby(["strain", "dpi"])["detectable"].mean() * 100).unstack()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    piv.plot(kind="bar", ax=ax, color=["#94A3B8", "#0D9488"], edgecolor="white")
    ax.set_ylabel("% d'individus détectables (copies > 0)")
    ax.set_xlabel("Sérotype")
    ax.set_title("Taux de détection du génome viral")
    ax.legend(title="DPI")
    ax.set_ylim(0, 100)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.0f%%", padding=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "detection_rate.png", dpi=150)
    plt.close(fig)


def df_to_markdown(df: pd.DataFrame) -> str:
    """Tableau Markdown sans dépendance externe (évite 'tabulate')."""
    cols = list(df.columns)
    head = "| " + " | ".join(map(str, cols)) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |"
            for row in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def write_report(tab: pd.DataFrame, tests: dict) -> None:
    lines = ["# Analyse de cinétique virale — FCO\n",
             "## Statistiques descriptives (par sérotype × DPI)\n",
             df_to_markdown(tab), "\n## Tests statistiques\n"]
    t = tests.get("BTV3_vs_BTV8_6dpi")
    if t:
        verdict = "différence SIGNIFICATIVE" if t["significatif_5pct"] else "PAS de différence significative"
        lines.append(f"- **BTV3 vs BTV8 (6 dpi)** — {t['test']} : p = {t['p_value']:.3g} → {verdict}. "
                     f"Médianes : BTV3 = {t['median_BTV3']:.0f}, BTV8 = {t['median_BTV8']:.0f} copies.\n")
    t = tests.get("taux_detection_6dpi")
    if t:
        lines.append(f"- **Taux de détection (6 dpi)** — {t['test']} : p = {t['p_value']:.3g}. "
                     f"Détectables : BTV3 = {t['pct_detectable_BTV3']}%, BTV8 = {t['pct_detectable_BTV8']}%.\n")
    for s, e in tests.get("effet_dpi", {}).items():
        v = "augmente significativement" if e["augmente_avec_dpi"] else "n'augmente pas significativement"
        lines.append(f"- **Effet du temps ({s})** — la charge {v} de 0 à 6 dpi "
                     f"(médiane {e['median_0dpi']:.0f} → {e['median_6dpi']:.0f}, p = {e['p_value']:.3g}).\n")
    lines.append("\n> Lecture : la charge virale renseigne sur la **réplication/le temps**, "
                 "pas sur l'identité du sérotype — ce qui justifie de ne PAS en faire un "
                 "classifieur BTV3/BTV8.\n")
    lines.append("\n> ⚠️ **CONFONDANT — à lire avant de conclure.** Les tests ci-dessus "
                 "**regroupent les deux essais expérimentaux**. Or l'effet du sérotype "
                 "**s'inverse entre les essais** (interaction essai × sérotype, cf. "
                 "`07_rf_analysis.py`). La comparaison BTV3 vs BTV8 sur données regroupées "
                 "est donc **confondue (paradoxe de Simpson)** : ces p-values ne doivent PAS "
                 "être interprétées telles quelles. Utiliser l'analyse **stratifiée par essai** "
                 "du script 07.\n")
    (OUT / "kinetics_summary.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="../01_BTV copy numbers midge.csv")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    df = load(Path(args.csv))
    print(f"{len(df)} individus | sérotypes : {df['strain'].value_counts().to_dict()}")

    tab = descriptive(df)
    print("\nStatistiques descriptives :")
    print(tab.to_string(index=False))

    tests = run_tests(df)
    plot_boxplot(df)
    plot_detection(df)
    write_report(tab, tests)
    (OUT / "kinetics_stats.json").write_text(json.dumps(tests, indent=2, ensure_ascii=False),
                                             encoding="utf-8")

    print("\nRésultats clés :")
    for k, v in tests.items():
        if isinstance(v, dict) and "p_value" in v:
            print(f"  {k}: p = {v['p_value']:.3g}")
    print(f"\n✅ Figures + rapport dans : {OUT}/")


if __name__ == "__main__":
    main()
