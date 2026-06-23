# Option 4 — RF compétence vectorielle

**Question :** virus détectable à 6 dpi ? (n=1121, 47.2% positifs)

## Performance (validation croisée 5 plis)

| Modèle | accuracy | ROC-AUC |
| --- | --- | --- |
| RF (capte l'interaction) | 0.590 | 0.625 |
| Logistique (effets simples) | 0.583 | 0.604 |
| Baseline (classe majoritaire) | 0.528 | — |

## Importance des variables (RF)

- `serotype_BTV8` : 0.643
- `group_2` : 0.357

## Lecture

- Le RF bat la baseline « classe majoritaire » et la logistique sans interaction → l'apport du RF est de **capter l'interaction groupe × sérotype** (voir figure).

- Apport néanmoins **modeste** : seules 2 variables explicatives existent.


## Pour une vraie compétence vectorielle (à collecter)

Partie du corps (tête/saliva vs abdomen = dissémination), température d'incubation, espèce/population de *Culicoides*, plusieurs dpi (cinétique 0/3/6/10), titre du repas sanguin. Avec ces variables, le RF deviendrait réellement informatif.


> ⚠️ Préciser dans le mémoire ce que représente le facteur `group` (1/2) selon le protocole expérimental (réplicat ? population ? condition ?).
