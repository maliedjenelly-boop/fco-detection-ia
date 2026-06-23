# Analyse supervisée depuis la base — détection NC vs infecté

Données extraites par requête SQL sur `fco.db` (jointure mesure_virale × serotype).

- Lignes : 1249 (train 874 / test 375, soit 70% en entraînement)
- Modèle : RandomForestClassifier (class_weight équilibré)
- **Accuracy = 0.979**
- Baseline (classe majoritaire) = 0.949 → gain réel = +2.9 points

| | prédit NC | prédit infecté |
| --- | --- | --- |
| **réel NC** | 11 | 8 |
| **réel infecté** | 0 | 356 |

> Lecture honnête : le jeu étant à ~95 % d'infectés, l'accuracy doit être comparée à la baseline. Le modèle reconnaît surtout les NC à 0 dpi (cf. analyse du mémoire).
