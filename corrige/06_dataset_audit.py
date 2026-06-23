"""
VOLET ÉLEVEUR — Audit anti-biais du jeu d'images.

Le Grad-CAM a montré que le modèle exploite la SOURCE (photo stock extérieure
= sain ; diapo/figure de PDF = malade) au lieu des lésions. Pire : le jeu
« malade » contient des images qui ne sont PAS des animaux (diapos-titre,
logos, pages de texte du PDF), étiquetées comme une sévérité de maladie.

Ce script :
  1. mesure, par classe, des indicateurs de SOURCE (format d'image, taille,
     uniformité du fond) -> prouve l'écart de distribution ;
  2. repère automatiquement les images « déchet » (fond quasi uniforme =
     diapo/logo/carte de texte) et les liste pour retrait ;
  3. (option --apply) déplace ces images en quarantaine, sans rien supprimer.

Heuristique « déchet » : sur une vignette quantifiée, si une seule couleur
domine > SEUIL de l'image, c'est presque sûrement une diapo/un fond uni et non
une photo d'animal (qui est toujours visuellement variée).

Produit : artifacts_image/audit_report.md + audit_flagged.csv

Usage :
    python 06_dataset_audit.py --data ../fco_dataset_final            # dry-run
    python 06_dataset_audit.py --data ../fco_dataset_final --apply    # quarantaine
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = Path("artifacts_image")
EXTS = (".jpg", ".jpeg", ".png", ".bmp")
DOMINANT_THRESHOLD = 0.50   # > 50 % de pixels d'une même couleur quantifiée -> "déchet"
HEALTHY = "healthy"


def image_stats(path: Path) -> dict | None:
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    w, h = im.size
    small = np.asarray(im.resize((96, 96)))
    q = (small // 32).reshape(-1, 3)               # quantification grossière (8 niveaux/canal)
    codes = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
    counts = np.bincount(codes, minlength=512)
    dom_frac = counts.max() / codes.size            # part de la couleur dominante
    gray_std = float(np.asarray(im.convert("L").resize((96, 96))).std())
    return {"w": w, "h": h, "aspect": round(w / h, 3),
            "dom_frac": round(float(dom_frac), 3), "gray_std": round(gray_std, 1)}


def collect(data: Path) -> list[dict]:
    rows = []
    for split in ("train", "val", "test"):
        sdir = data / split
        if not sdir.exists():
            continue
        for cls_dir in sorted(p for p in sdir.iterdir() if p.is_dir()):
            for f in cls_dir.iterdir():
                if f.suffix.lower() in EXTS:
                    s = image_stats(f)
                    if s is None:
                        continue
                    is_sick = cls_dir.name != HEALTHY
                    s.update(path=str(f), split=split, cls=cls_dir.name,
                             group="malade" if is_sick else "sain",
                             flag_junk=bool(is_sick and s["dom_frac"] > DOMINANT_THRESHOLD))
                    rows.append(s)
    return rows


def summarize(rows: list[dict]) -> str:
    by_group = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)

    lines = ["# Audit anti-biais du jeu d'images\n",
             f"Total : {len(rows)} images.\n",
             "## Écart de SOURCE entre groupes (moyennes)\n",
             "| Groupe | n | format (w/h) moyen | taille médiane | uniformité fond (dom_frac) |",
             "| --- | --- | --- | --- | --- |"]
    for g, rs in by_group.items():
        asp = np.mean([r["aspect"] for r in rs])
        px = int(np.median([r["w"] * r["h"] for r in rs]))
        dom = np.mean([r["dom_frac"] for r in rs])
        lines.append(f"| {g} | {len(rs)} | {asp:.2f} | {px:,} px | {dom:.2f} |")

    flagged = [r for r in rows if r["flag_junk"]]
    lines += ["\n## Images « déchet » détectées dans le groupe malade",
              f"\n**{len(flagged)} image(s)** au fond quasi uniforme (dom_frac > "
              f"{DOMINANT_THRESHOLD}) — très probablement des diapos/logos/pages de texte, "
              "pas des animaux :\n"]
    for r in sorted(flagged, key=lambda r: -r["dom_frac"]):
        lines.append(f"- `{Path(r['path']).name}` ({r['split']}/{r['cls']}) — "
                     f"dom_frac={r['dom_frac']}, gray_std={r['gray_std']}")
    lines += ["\n> Interprétation : plus `dom_frac` est élevé, plus l'image est un aplat "
              "uniforme (diapo). Une vraie photo d'animal dépasse rarement 0,40.\n",
              "\n## Recommandations\n",
              "1. **Retirer** ces images du jeu (option `--apply` -> quarantaine).\n",
              "2. Le biais de fond subsistera : photos saines (extérieur) vs malades "
              "(intérieur clinique). Pour le casser durablement : **recadrer les DEUX "
              "groupes sur la zone d'intérêt** (museau/bouche/yeux) ou collecter des images "
              "saines de même nature (gros plans, même contexte).\n",
              "3. Re-vérifier avec le Grad-CAM après nettoyage.\n"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../fco_dataset_final")
    ap.add_argument("--apply", action="store_true",
                    help="déplace les images déchet en quarantaine (sinon dry-run)")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    rows = collect(Path(args.data))
    if not rows:
        sys.exit(f"Aucune image trouvée sous {args.data}")

    report = summarize(rows)
    (OUT / "audit_report.md").write_text(report, encoding="utf-8")
    with open(OUT / "audit_flagged.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["path", "split", "cls", "group", "w", "h",
                                            "aspect", "dom_frac", "gray_std", "flag_junk"])
        wr.writeheader()
        wr.writerows(rows)

    flagged = [r for r in rows if r["flag_junk"]]
    print(f"{len(rows)} images analysées | {len(flagged)} déchet(s) détecté(s) "
          f"dans le groupe malade.")
    for r in sorted(flagged, key=lambda r: -r["dom_frac"])[:15]:
        print(f"  [{r['dom_frac']:.2f}] {r['split']}/{r['cls']}/{Path(r['path']).name}")

    if args.apply and flagged:
        qroot = Path(args.data) / "_quarantine"
        for r in flagged:
            src = Path(r["path"])
            dst = qroot / r["split"] / r["cls"] / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        print(f"\n→ {len(flagged)} image(s) déplacée(s) en quarantaine : {qroot}")
    elif flagged:
        print("\n(dry-run) Relancez avec --apply pour les mettre en quarantaine.")
    print(f"\n✅ Rapport : {OUT}/audit_report.md  |  détail : {OUT}/audit_flagged.csv")


if __name__ == "__main__":
    main()
