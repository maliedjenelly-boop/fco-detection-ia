# -*- coding: utf-8 -*-
"""
SÉCURISATION DES DONNÉES & RGPD (§vii.2 du guide).

La table `veterinaire` contient des données personnelles (email, téléphone).
Ce script met en place des mesures concrètes et démontrables :
  1. une VUE `v_veterinaire_public` qui MASQUE les emails (minimisation),
  2. une démonstration d'accès en LECTURE SEULE (toute écriture est refusée),
  3. la génération d'un rapport des mesures (pour captures d'écran).

Usage :  python securite_rgpd.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BDD = Path(__file__).parent
DB = BDD / "fco.db"
RAPPORT = BDD / "securite_rgpd.md"

VUE = """
CREATE VIEW IF NOT EXISTS v_veterinaire_public AS
SELECT id_vet, nom, clinique, type, ville,
       '****' || substr(email, instr(email,'@')) AS email_masque
FROM veterinaire
WHERE email <> '';
"""


def main():
    if not DB.exists():
        sys.exit("Base absente : lancez build_database.py")

    # 1) Vue de minimisation des données
    con = sqlite3.connect(DB)
    con.executescript(VUE)
    con.commit()
    print("1) Vue 'v_veterinaire_public' (emails masqués) :")
    for r in con.execute("SELECT nom, ville, email_masque FROM v_veterinaire_public"):
        print(f"     {r[0]:<38} {r[1]:<16} {r[2]}")
    con.close()

    # 2) Démonstration d'accès LECTURE SEULE (refus d'écriture)
    print("\n2) Connexion en lecture seule (mode=ro) :")
    ro = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    print("     lecture OK :", ro.execute("SELECT COUNT(*) FROM veterinaire").fetchone()[0], "lignes")
    try:
        ro.execute("DELETE FROM veterinaire")
        print("     ÉCRITURE ACCEPTÉE — anormal !")
    except sqlite3.OperationalError as e:
        print(f"     écriture REFUSÉE (attendu) : {e}")
    ro.close()

    # 3) Rapport des mesures
    RAPPORT.write_text(
        "# Sécurisation des données & conformité RGPD\n\n"
        "## Données personnelles identifiées\n"
        "- Table `veterinaire` : `nom`, `telephone`, `email` (donnée à caractère personnel).\n\n"
        "## Mesures mises en place\n"
        "| Mesure | Principe RGPD | Mise en œuvre |\n| --- | --- | --- |\n"
        "| Minimisation | Art. 5.1.c | Vue `v_veterinaire_public` masquant l'email (`****@domaine`) |\n"
        "| Contrôle d'accès | Intégrité & confidentialité | Connexion **lecture seule** pour les usages non administratifs |\n"
        "| Données d'exemple | Pas de données réelles | Numéros de **fiction ARCEP**, domaine `exemple.fr` |\n"
        "| Limitation de conservation | Art. 5.1.e | Base reconstructible à la demande, pas d'historique conservé |\n"
        "| Traçabilité | Responsabilité | Scripts d'ETL versionnés et reproductibles |\n\n"
        "## Points de contrôle RGPD\n"
        "1. Aucune donnée personnelle réelle n'est stockée (jeu d'exemple).\n"
        "2. Les accès applicatifs utilisent la **vue masquée**, pas la table brute.\n"
        "3. L'accès en écriture est réservé à l'administrateur de la base.\n"
        "4. Finalité explicite : mise en relation éleveur ↔ vétérinaire en cas de suspicion.\n",
        encoding="utf-8")
    print(f"\n✅ Vue créée + rapport -> {RAPPORT.name}")


if __name__ == "__main__":
    main()
