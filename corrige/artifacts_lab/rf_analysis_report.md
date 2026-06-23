# Exploitation du Random Forest avec la variable ESSAI

## 1. Effectifs et charge virale par essai × sérotype (6 dpi)

| essai | strain | n | mediane | pct_detectable |
| --- | --- | --- | --- | --- |
| 1 | BTV3 | 319 | 0.0 | 27.9 |
| 1 | BTV8 | 330 | 60.3 | 59.7 |
| 2 | BTV3 | 250 | 56.0 | 53.2 |
| 2 | BTV8 | 222 | 0.0 | 49.5 |

> L'effet du sérotype **s'inverse** entre les essais : regrouper les essais (comme le faisait `04_lab_kinetics_analysis.py`) est donc confondu (paradoxe de Simpson). Il faut **stratifier par essai**.


## 2. RF en régression — log_copies ~ sérotype + dpi + essai

- R² (test) = **0.151**
- Importance par permutation (plus c'est haut, plus la variable explique la charge) :
  - **dpi** : 0.25
  - **sérotype (BTV8?)** : 0.03
  - **essai** : 0.017

> Le RF capte automatiquement l'interaction. Si `essai` pèse autant ou plus que le sérotype, la charge virale n'est pas un marqueur stable du sérotype.


## 3. Validation inter-essais (reproductibilité) — BTV3 vs BTV8 à 6 dpi

- Niveau du hasard (classe majoritaire) : **0.508**
- Intra (essais mélangés, split aléatoire) : **0.516**
- Train essai 1 → test essai 2 : **0.504**
- Train essai 2 → test essai 1 : **0.424**

> Si l'accuracy inter-essais tombe au niveau (ou en dessous) du hasard, le modèle appris sur un essai ne se transfère pas à l'autre : la relation charge↔sérotype **n'est pas reproductible**. C'est LE résultat à retenir.
