# Analyse de cinétique virale — FCO

## Statistiques descriptives (par sérotype × DPI)

| strain | dpi | n | pct_detectable | median | mean | max |
| --- | --- | --- | --- | --- | --- | --- |
| BTV3 | 0 | 32 | 100.0 | 44000.0 | 52603.1 | 159000.0 |
| BTV3 | 6 | 569 | 39.0 | 0.0 | 8793110.0 | 433000000.0 |
| BTV8 | 0 | 32 | 100.0 | 143000.0 | 162168.8 | 367000.0 |
| BTV8 | 6 | 552 | 55.6 | 56.9 | 1289276.0 | 128000000.0 |
| NC | 0 | 32 | 0.0 | 0.0 | 0.0 | 0.0 |
| NC | 6 | 32 | 0.0 | 0.0 | 0.0 | 0.0 |

## Tests statistiques

- **BTV3 vs BTV8 (6 dpi)** — Mann-Whitney U : p = 4.85e-08 → différence SIGNIFICATIVE. Médianes : BTV3 = 0, BTV8 = 57 copies.

- **Taux de détection (6 dpi)** — Fisher exact : p = 2.58e-08. Détectables : BTV3 = 39.0%, BTV8 = 55.6%.

- **Effet du temps (BTV3)** — la charge n'augmente pas significativement de 0 à 6 dpi (médiane 44000 → 0, p = 1).

- **Effet du temps (BTV8)** — la charge n'augmente pas significativement de 0 à 6 dpi (médiane 143000 → 57, p = 1).


> Lecture : la charge virale renseigne sur la **réplication/le temps**, pas sur l'identité du sérotype — ce qui justifie de ne PAS en faire un classifieur BTV3/BTV8.


> ⚠️ **CONFONDANT — à lire avant de conclure.** Les tests ci-dessus **regroupent les deux essais expérimentaux**. Or l'effet du sérotype **s'inverse entre les essais** (interaction essai × sérotype, cf. `07_rf_analysis.py`). La comparaison BTV3 vs BTV8 sur données regroupées est donc **confondue (paradoxe de Simpson)** : ces p-values ne doivent PAS être interprétées telles quelles. Utiliser l'analyse **stratifiée par essai** du script 07.
