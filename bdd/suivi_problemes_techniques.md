# Tableau de suivi des problématiques techniques

Suivi des incidents techniques rencontrés et résolus durant le projet (exigence §vii.2 du guide).

| # | Date | Problématique technique | Date résolution | Solution apportée |
| --- | --- | --- | --- | --- |
| 1 | 2026-06-16 | Le Random Forest était entraîné sur des labels dérivés d'une feature (seuil sur la charge) → fuite de données | 2026-06-16 | Étiquettes reconstruites à partir du sérotype de l'identifiant, sans dériver d'une variable explicative |
| 2 | 2026-06-16 | Le modèle image livré était un EfficientNet à tête aléatoire **non entraînée** | 2026-06-16 | Vrai transfer learning en 2 phases (tête puis fine-tuning) |
| 3 | 2026-06-16 | L'application Streamlit **simulait** le diagnostic image (`np.random`) | 2026-06-16 | Chargement et inférence des vrais modèles sauvegardés |
| 4 | 2026-06-16 | Le volet labo de l'app semblait figé : 1249 appels `predict_proba` + `n_jobs=-1` → avalanche d'avertissements | 2026-06-16 | Prédiction **vectorisée** (un seul appel) + `n_jobs=1` |
| 5 | 2026-06-16 | App lancée avec `python` au lieu de `streamlit run` (warnings ScriptRunContext) | 2026-06-16 | Lancement correct via `streamlit run` |
| 6 | 2026-06-17 | 36 % des images « malade » étaient des diapositives/texte du PDF (pas des animaux) | 2026-06-17 | Audit automatique (uniformité du fond) + mise en quarantaine des 48 images |
| 7 | 2026-06-17 | Classification 3 classes BTV3/BTV8 non séparable par la charge virale | 2026-06-17 | Recentrage sur la détection binaire NC vs infecté |
| 8 | 2026-06-17 | Analyse de cinétique confondue par la variable essai (paradoxe de Simpson) | 2026-06-17 | Stratification par essai + validation inter-essais (script 07) |
| 9 | 2026-06-17 | `class_weight='balanced'` faisait chuter l'accuracy (54 %) via la collision de features | 2026-06-17 | Random Forest par défaut, lecture honnête face à la baseline |
| 10 | 2026-06-17 | Outils de génération absents (Node.js pour Word, pdftoppm/pandoc) | 2026-06-17 | Bascule sur `python-docx` et `pypdf` |
