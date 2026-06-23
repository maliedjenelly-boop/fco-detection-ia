# -*- coding: utf-8 -*-
"""
OPTIMISATION DE LA BASE — comparaison du temps d'exécution AVANT / APRÈS index.

Exigence du guide (Bloc 1 / §vii.2) : « comparaison du temps d'exécution des
requêtes entre les tables optimisées et non-optimisées ».

Démarche :
  1. on retire tout index, on chronomètre une requête répétée -> table NON optimisée ;
  2. on affiche le plan d'exécution (SCAN = parcours complet) ;
  3. on crée les index, on rechronométre -> table OPTIMISÉE ;
  4. on affiche le plan (SEARCH USING INDEX) et le facteur d'accélération.

Usage :  python optimisation_requetes.py
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BDD = Path(__file__).parent
DB = BDD / "fco.db"
DUMP = BDD / "fco_dump.sql"
RAPPORT = BDD / "optimisation_rapport.md"

REPET = 4000  # nb de répétitions pour rendre la mesure significative (table petite)
# Requête réaliste : recherche ciblée d'un individu dans un essai (colonnes NON-PK)
REQUETE = "SELECT id_mesure, genome_copies FROM mesure_virale WHERE id_individu=? AND id_essai=?"

INDEX = [
    "CREATE INDEX idx_mesure_indiv ON mesure_virale(id_individu, id_essai)",
    "CREATE INDEX idx_mesure_sero_dpi ON mesure_virale(id_serotype, dpi)",
]


def chrono(con, paires):
    cur = con.cursor()
    t0 = time.perf_counter()
    for _ in range(REPET):
        for indiv, essai in paires:
            cur.execute(REQUETE, (indiv, essai)).fetchall()
    return time.perf_counter() - t0


def plan(con):
    rows = con.execute("EXPLAIN QUERY PLAN " + REQUETE, (1, 1)).fetchall()
    return " | ".join(r[-1] for r in rows)


def main():
    if not DB.exists():
        sys.exit("Base absente : lancez d'abord build_database.py")
    con = sqlite3.connect(DB)

    # jeu de clés à rechercher (échantillon réel)
    paires = con.execute(
        "SELECT DISTINCT id_individu, id_essai FROM mesure_virale LIMIT 30").fetchall()

    # 1) état NON optimisé
    for idx in ("idx_mesure_indiv", "idx_mesure_sero_dpi"):
        con.execute(f"DROP INDEX IF EXISTS {idx}")
    con.commit()
    plan_avant = plan(con)
    t_avant = chrono(con, paires)

    # 2) état OPTIMISÉ
    for ddl in INDEX:
        con.execute(ddl)
    con.execute("ANALYZE")
    con.commit()
    plan_apres = plan(con)
    t_apres = chrono(con, paires)

    facteur = t_avant / t_apres if t_apres else float("inf")
    nb_req = REPET * len(paires)

    print(f"Requêtes exécutées : {nb_req:,}".replace(",", " "))
    print(f"\n{'':16}{'temps total':>14}{'plan':>10}")
    print(f"{'NON optimisée':16}{t_avant*1000:>11.0f} ms   SCAN (parcours complet)")
    print(f"{'OPTIMISÉE':16}{t_apres*1000:>11.0f} ms   SEARCH USING INDEX")
    print(f"\n→ Accélération : x{facteur:.1f}")
    print(f"\nPlan AVANT : {plan_avant}")
    print(f"Plan APRÈS : {plan_apres}")

    RAPPORT.write_text(
        "# Optimisation des requêtes — comparaison avant/après index\n\n"
        f"Requête testée :\n\n```sql\n{REQUETE}\n```\n\n"
        f"Exécutée **{nb_req} fois** (table = {con.execute('SELECT COUNT(*) FROM mesure_virale').fetchone()[0]} lignes).\n\n"
        "| Version | Index | Temps total | Plan d'exécution |\n| --- | --- | --- | --- |\n"
        f"| Non optimisée | aucun | {t_avant*1000:.0f} ms | {plan_avant} |\n"
        f"| Optimisée | idx_mesure_indiv, idx_mesure_sero_dpi | {t_apres*1000:.0f} ms | {plan_apres} |\n\n"
        f"**Accélération : ×{facteur:.1f}.** L'index transforme le parcours complet "
        "(SCAN) en recherche indexée (SEARCH USING INDEX).\n", encoding="utf-8")

    # 3) le dump final reflète la version OPTIMISÉE (index inclus)
    with open(DUMP, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(line + "\n")
    con.close()
    print(f"\n✅ Rapport -> {RAPPORT.name} | dump optimisé -> {DUMP.name}")


if __name__ == "__main__":
    main()
