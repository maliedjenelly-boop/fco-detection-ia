# Classification binaire — infecté (détecté) vs non détecté

- Individus : 1249 | label 0 = 656, label 1 = 593 (jeu quasi équilibré)

- Variables (anti-fuite) : dpi, essai, is_BTV3, is_BTV8 ; la charge virale est EXCLUE (elle définit le label)


## Comparaison des modèles

```
             Modèle  Accuracy       F1  ROC-AUC AUC (CV 5-fold)
Logistic Regression  0.624000 0.605042 0.663663   0.682 ± 0.028
      Random Forest  0.605333 0.658986 0.665631   0.707 ± 0.029
            XGBoost  0.605333 0.658986 0.665631   0.707 ± 0.029
```

## Importance des variables

```
Variable       RF  XGBoost  LR (coef)
     dpi 0.189028 0.287627  -0.791733
   essai 0.226320 0.150982   0.208342
 is_BTV3 0.257063 0.289034   2.365864
 is_BTV8 0.327590 0.272358   2.709026
```


> Démonstration de fuite : inclure la charge donne AUC = 1.00 (trivial). On l'évite volontairement.


Figures : charge_distribution.png, roc_curves.png
