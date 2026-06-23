# Projet FCO — détection de la Fièvre Catarrhale Ovine

Pipeline propre, **honnête et reproductible** pour l'aide à la détection de la FCO,
combinant un volet **laboratoire** (charge virale), un volet **éleveur** (image),
une **base de données** relationnelle et une **application** Streamlit.

## Structure du projet

```
fco_hybride_project/
├── 01_BTV copy numbers midge.csv        # données labo brutes (source)
├── fco_dataset_final/                   # images 4 classes (healthy/mild/moderate/severe)
├── fco_dataset_binaire/                 # images 2 classes (sain / malade)
├── corrige/                             # CODE (voir ci-dessous)
├── bdd/                                 # BASE DE DONNÉES (voir section dédiée)
└── memoire/                             # mémoire Word + PDF + ZIP technique
```

```
corrige/
├── 01_train_lab_rf.py             # Volet labo : Random Forest (charge virale)
├── 02_train_image_efficientnet.py # Volet image : EfficientNet-B0 (sain/malade)
├── 03_app_streamlit.py            # Application web (4 pages, vrais modèles + base SQL)
├── 04_lab_kinetics_analysis.py    # Analyse de cinétique virale (figures + tests)
├── 05_image_gradcam.py            # Explicabilité Grad-CAM (diagnostic du biais image)
├── 06_dataset_audit.py            # Audit anti-biais du jeu d'images
├── 07_rf_analysis.py              # RF + variable ESSAI (interaction, reproductibilité)
├── 08_classification_infection.py # Classification LR / RF / XGBoost (sans fuite)
├── requirements.txt · .streamlit/config.toml
├── artifacts_lab/                 # modèles + figures (cinétique, ROC, confusion…)
└── artifacts_image/               # modèle image + matrice + gradcam/
```

## Installation

```bash
pip install -r requirements.txt
# Volet labo + base de données : pas besoin de torch.
# Volet image (02, 05) : pip install torch torchvision timm
# Classification (08) : pip install xgboost
```

## Exécution — code (corrige/)

```bash
# 1) Volet laboratoire — Random Forest (rapide, CPU)
python 01_train_lab_rf.py --csv "../01_BTV copy numbers midge.csv"

# 2) Volet image — EfficientNet (torch requis ; défaut : ../fco_dataset_binaire)
python 02_train_image_efficientnet.py --epochs 25

# 3) Application web (4 pages : Accueil, Mode Laboratoire, Mode Éleveur, Contacts)
streamlit run 03_app_streamlit.py

# 4) Analyse de cinétique virale (figures + tests statistiques)
python 04_lab_kinetics_analysis.py --csv "../01_BTV copy numbers midge.csv"

# 5) Grad-CAM — où regarde le modèle image (torch + modèle entraîné)
python 05_image_gradcam.py

# 6) Audit anti-biais du jeu d'images (--apply pour mettre en quarantaine)
python 06_dataset_audit.py --data ../fco_dataset_final

# 7) RF + variable ESSAI : interaction essai×sérotype + validation inter-essais
python 07_rf_analysis.py --csv "../01_BTV copy numbers midge.csv"

# 8) Classification binaire LR / RF / XGBoost (anti-fuite, CV, importance, ROC)
python 08_classification_infection.py --csv "../01_BTV copy numbers midge.csv"
```

## Base de données (bdd/)

Base **SQLite** unifiant trois formats (CSV + JSON + XLSX), conforme au référentiel
(§ Exploitation des données). Option serveur MySQL/phpMyAdmin documentée.

```bash
python ../bdd/build_database.py        # ETL -> fco.db (+ dictionnaire + dump SQL)
python ../bdd/optimisation_requetes.py # comparaison requêtes : SCAN -> SEARCH USING INDEX
python ../bdd/ml_depuis_base.py        # modèle supervisé lu DEPUIS la base (SQL)
python ../bdd/securite_rgpd.py         # vue masquée (emails) + accès lecture seule
```

Livrables : `fco.db`, `fco_dump.sql`, `dictionnaire_donnees.md`, `schema.sql` /
`schema_mysql.sql`, `MIGRATION_MYSQL.md`, `securite_rgpd.md`, `charte_ethique.md`,
`suivi_problemes_techniques.md`. L'application (onglet **Base de données** du Mode
Laboratoire) lit directement `bdd/fco.db` par requête SQL.

## Mémoire & livrables (memoire/)

`Memoire_FCO_MALIEDJE_Nelly.docx` + `.pdf` (mémoire de thèse professionnelle, plan
conforme au guide) et `Livrable_technique_FCO.zip` (code + dump SQL + configs).

## Choix méthodologiques clés

- **Anti-fuite de données** : la charge virale définissant le label, elle est exclue
  des variables ; on prédit la détectabilité à partir de sérotype / DPI / essai.
- **Détection = test qPCR** : dans l'app, `copies > 0` → infecté, `copies = 0` → NC,
  confiance croissant avec la charge. Le RF reste l'outil d'**analyse** (07/08).
- **Évaluation honnête** : comparaison à la baseline, F1 et ROC-AUC, validation croisée.
- **Explicabilité** : Grad-CAM (image) + importance des variables (tabulaire).

## Ce qui a été corrigé (vs projet d'origine)

| Problème d'origine | Correction |
|---|---|
| Labels du RF **dérivés d'une feature** (fuite) ou données **fabriquées** | Vraies étiquettes, split stratifié, CV, anti-fuite explicite |
| Modèle image = backbone + **tête aléatoire** non entraînée | Transfer learning réel en 2 phases |
| App Streamlit **simulant** le diagnostic (`np.random`) | Inférence des vrais modèles + lecture base SQL |
| `val/` absent ; `Thumbs.db` cassait ImageFolder | Splits cohérents, filtre des fichiers non-image |
| 36 % d'images « malade » = **diapositives/texte** du PDF | Audit (06) + quarantaine |

## Limites assumées (documentées dans le mémoire)

1. **BTV3 vs BTV8 non séparables** par la charge virale, et relation **non reproductible**
   entre essais (paradoxe de Simpson). Le volet labo fait de la **détection**, pas du typage.
2. **Biais de source** des images (stock vs PDF clinique) : un test à 100 % reflète
   surtout ce biais, pas une reconnaissance des lésions.
3. **Détectable ≠ infecté** : un animal ayant éliminé le virus est légitimement « non détecté ».
4. Dataset image **très petit** ; performances à interpréter avec prudence.
