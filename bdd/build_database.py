# -*- coding: utf-8 -*-
"""
CONSTRUCTION DE LA BASE DE DONNÉES FCO (SQLite).

Charge et UNIFIE trois sources de formats différents (exigence du guide) :
  1. CSV  — mesures de charge virale       -> tables essai / serotype / mesure_virale
  2. JSON — catalogue des images (généré)  -> table image
  3. XLSX — contacts vétérinaires (généré) -> table veterinaire  (données perso -> RGPD)

Réalise : création du schéma, gestion des valeurs manquantes / incohérences,
contrôle d'intégrité (clés étrangères), génération du dictionnaire de données
et export du dump SQL.

Usage :  python build_database.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BDD = Path(__file__).parent
ROOT = BDD.parent
DB = BDD / "fco.db"
CSV = ROOT / "01_BTV copy numbers midge.csv"
IMG_ROOT = ROOT / "fco_dataset_final"
JSON_IMG = BDD / "image_catalog.json"
XLSX_VET = BDD / "veterinaires.xlsx"
DUMP = BDD / "fco_dump.sql"
DICT = BDD / "dictionnaire_donnees.md"

SEROTYPES = [(1, "NC", "Contrôle négatif", 0),
             (2, "BTV3", "Bluetongue sérotype 3", 1),
             (3, "BTV8", "Bluetongue sérotype 8", 1)]
CODE2ID = {c: i for i, c, *_ in SEROTYPES}

VETS = [
    ("Clinique Vétérinaire des Trois Vallées", "Médecine des ruminants",
     "Vétérinaire sanitaire", "Clermont-Ferrand", "04 65 71 18 22", "troisvallees@exemple.fr"),
    ("Cabinet Vétérinaire du Bocage", "Vétérinaire rural",
     "Vétérinaire traitant", "Rennes", "02 61 91 34 56", "bocage@exemple.fr"),
    ("Clinique Vétérinaire Saint-Roch", "Élevage & filière ovine",
     "Vétérinaire sanitaire", "Toulouse", "05 36 49 27 81", "saintroch@exemple.fr"),
    ("Service de Garde Vétérinaire", "Urgences élevage 24/7",
     "Urgences", "Lyon", "04 65 71 00 15", ""),
]


def log(msg=""): print(msg)


# --------------------------------------------------------------------------- #
def parse_id(mid: str):
    s = str(mid)
    essai = re.match(r"\s*(\d+)\s*-", s)
    strain = next((c for c in ("BTV3", "BTV8", "NC") if c in s), None)
    dpi = re.search(r"(\d+)\s*dpi", s, re.IGNORECASE)
    indiv = re.search(r"(\d+)\s*$", s)
    return (int(essai.group(1)) if essai else None, strain,
            int(dpi.group(1)) if dpi else None,
            int(indiv.group(1)) if indiv else None)


def charger_csv(con):
    """Source 1 (CSV) -> mesure_virale, avec rapport valeurs manquantes."""
    df = pd.read_csv(CSV, sep=";", encoding="latin-1")
    df.columns = ["midge_id", "copies"]
    brut = len(df)

    # --- Contrôle qualité (exigence guide) ---
    df["copies_num"] = pd.to_numeric(df["copies"], errors="coerce")
    nb_copies_manquantes = int(df["copies_num"].isna().sum())
    parsed = df["midge_id"].map(parse_id)
    df["essai"] = [p[0] for p in parsed]
    df["strain"] = [p[1] for p in parsed]
    df["dpi"] = [p[2] for p in parsed]
    df["indiv"] = [p[3] for p in parsed]
    nb_strain_inconnu = int(df["strain"].isna().sum())
    nb_essai_inconnu = int(df["essai"].isna().sum())
    nb_dpi_inconnu = int(df["dpi"].isna().sum())

    # --- Nettoyage : valeurs manquantes de charge -> 0 ; lignes non parsables rejetées ---
    df["copies_num"] = df["copies_num"].fillna(0.0)
    rejets = df[df["strain"].isna() | df["essai"].isna() | df["dpi"].isna()]
    df = df.drop(rejets.index).reset_index(drop=True)

    rows = [(i + 1, int(r.indiv) if pd.notna(r.indiv) else 0, int(r.essai),
             CODE2ID[r.strain], int(r.dpi), float(r.copies_num),
             1 if r.copies_num > 0 else 0)
            for i, r in df.iterrows()]
    con.executemany(
        "INSERT INTO mesure_virale "
        "(id_mesure,id_individu,id_essai,id_serotype,dpi,genome_copies,detectable) "
        "VALUES (?,?,?,?,?,?,?)", rows)

    log("  [CSV] mesure_virale :")
    log(f"        lignes brutes               : {brut}")
    log(f"        charges non numériques (→0) : {nb_copies_manquantes}")
    log(f"        sérotype/essai/dpi illisible: {nb_strain_inconnu}/{nb_essai_inconnu}/{nb_dpi_inconnu}")
    log(f"        lignes rejetées (incohérence): {len(rejets)}")
    log(f"        lignes chargées             : {len(rows)}")


def catalogue_images(con):
    """Source 2 (JSON) -> image. Génère d'abord le JSON depuis le dataset."""
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    catalogue = []
    if IMG_ROOT.exists():
        for split in ("train", "val", "test"):
            for sev_dir in (IMG_ROOT / split).glob("*"):
                if not sev_dir.is_dir():
                    continue
                sev = sev_dir.name
                classe = "sain" if sev == "healthy" else "malade"
                source = "stock" if sev == "healthy" else "pdf_clinique"
                for f in sev_dir.iterdir():
                    if f.suffix.lower() in exts:
                        catalogue.append({"fichier": f.name, "classe": classe,
                                          "severite": sev, "source": source, "split": split})
    JSON_IMG.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = [(i + 1, c["fichier"], c["classe"], c["severite"], c["source"], c["split"])
            for i, c in enumerate(catalogue)]
    con.executemany(
        "INSERT INTO image (id_image,fichier,classe,severite,source,split) VALUES (?,?,?,?,?,?)",
        rows)
    log(f"  [JSON] image : {len(rows)} images cataloguées (-> {JSON_IMG.name})")


def charger_vets(con):
    """Source 3 (XLSX) -> veterinaire. Génère d'abord le XLSX."""
    wb = Workbook(); ws = wb.active; ws.title = "veterinaires"
    ws.append(["nom", "clinique", "type", "ville", "telephone", "email"])
    for v in VETS:
        ws.append(list(v))
    wb.save(XLSX_VET)

    df = pd.read_excel(XLSX_VET)
    rows = [(i + 1, *r) for i, r in enumerate(df.itertuples(index=False, name=None))]
    con.executemany(
        "INSERT INTO veterinaire (id_vet,nom,clinique,type,ville,telephone,email) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    log(f"  [XLSX] veterinaire : {len(rows)} contacts (-> {XLSX_VET.name})")


def controle_integrite(con):
    log("\n  Contrôle d'intégrité :")
    viol = con.execute("PRAGMA foreign_key_check").fetchall()
    log(f"        violations de clés étrangères : {len(viol)}")
    for t in ("essai", "serotype", "mesure_virale", "image", "veterinaire"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        log(f"        {t:<14}: {n} lignes")
    # cohérence : aucune mesure orpheline
    orph = con.execute(
        "SELECT COUNT(*) FROM mesure_virale m "
        "LEFT JOIN serotype s ON m.id_serotype=s.id_serotype WHERE s.id_serotype IS NULL"
    ).fetchone()[0]
    log(f"        mesures orphelines (sérotype) : {orph}")


def dictionnaire():
    d = [
        "# Dictionnaire de données — Base FCO\n",
        "Base SQLite `fco.db`. Trois sources unifiées : CSV (labo), JSON (images), XLSX (vétérinaires).\n",
        "## Table `essai`",
        "| Colonne | Type | Description |", "| --- | --- | --- |",
        "| id_essai | INTEGER (PK) | Identifiant de l'essai expérimental |",
        "| libelle | TEXT | Libellé de l'essai |\n",
        "## Table `serotype`",
        "| Colonne | Type | Description |", "| --- | --- | --- |",
        "| id_serotype | INTEGER (PK) | Identifiant du sérotype |",
        "| code | TEXT | NC / BTV3 / BTV8 |",
        "| libelle | TEXT | Libellé complet |",
        "| est_infectieux | INTEGER | 0 = contrôle négatif, 1 = infectieux |\n",
        "## Table `mesure_virale` (source CSV)",
        "| Colonne | Type | Description |", "| --- | --- | --- |",
        "| id_mesure | INTEGER (PK) | Identifiant de la mesure |",
        "| id_individu | INTEGER | N° de l'individu (moucheron) |",
        "| id_essai | INTEGER (FK→essai) | Essai expérimental |",
        "| id_serotype | INTEGER (FK→serotype) | Sérotype inoculé |",
        "| dpi | INTEGER | Jour post-infection (0 ou 6) |",
        "| genome_copies | REAL | Charge virale (copies du génome) |",
        "| detectable | INTEGER | 1 si genome_copies > 0 |\n",
        "## Table `image` (source JSON)",
        "| Colonne | Type | Description |", "| --- | --- | --- |",
        "| id_image | INTEGER (PK) | Identifiant de l'image |",
        "| fichier | TEXT | Nom du fichier image |",
        "| classe | TEXT | sain / malade |",
        "| severite | TEXT | healthy / mild / moderate / severe |",
        "| source | TEXT | stock / pdf_clinique (trace le biais de source) |",
        "| split | TEXT | train / val / test |\n",
        "## Table `veterinaire` (source XLSX — données personnelles, RGPD)",
        "| Colonne | Type | Description |", "| --- | --- | --- |",
        "| id_vet | INTEGER (PK) | Identifiant du vétérinaire |",
        "| nom | TEXT | Nom de la clinique/du praticien |",
        "| clinique | TEXT | Spécialité / structure |",
        "| type | TEXT | Vétérinaire sanitaire / traitant / urgences |",
        "| ville | TEXT | Ville |",
        "| telephone | TEXT | Téléphone (numéros fictifs ARCEP en exemple) |",
        "| email | TEXT | Email (donnée personnelle) |",
    ]
    DICT.write_text("\n".join(d), encoding="utf-8")
    log(f"\n  Dictionnaire de données -> {DICT.name}")


def export_dump(con):
    with open(DUMP, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(line + "\n")
    log(f"  Dump SQL -> {DUMP.name}")


def main():
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((BDD / "schema.sql").read_text(encoding="utf-8"))
    con.executemany("INSERT INTO essai (id_essai,libelle) VALUES (?,?)",
                    [(1, "Essai 1"), (2, "Essai 2")])
    con.executemany("INSERT INTO serotype (id_serotype,code,libelle,est_infectieux) VALUES (?,?,?,?)",
                    SEROTYPES)

    log(f"Base : {DB.name}")
    log("Chargement des sources :")
    charger_csv(con)
    catalogue_images(con)
    charger_vets(con)
    con.commit()
    controle_integrite(con)
    dictionnaire()
    export_dump(con)
    con.close()
    log("\n✅ Base construite avec succès.")


if __name__ == "__main__":
    main()
