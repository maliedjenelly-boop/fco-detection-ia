# Audit anti-biais du jeu d'images

Total : 156 images.

## Écart de SOURCE entre groupes (moyennes)

| Groupe | n | format (w/h) moyen | taille médiane | uniformité fond (dom_frac) |
| --- | --- | --- | --- | --- |
| sain | 24 | 1.39 | 2,503,680 px | 0.17 |
| malade | 132 | 1.36 | 1,166,400 px | 0.44 |

## Images « déchet » détectées dans le groupe malade

**48 image(s)** au fond quasi uniforme (dom_frac > 0.5) — très probablement des diapos/logos/pages de texte, pas des animaux :

- `mild_train_0003.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0008.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0015.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0017.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0022.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0024.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0025.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0030.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0037.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0039.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0049.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0052.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0057.png` (train/mild) — dom_frac=0.972, gray_std=11.5
- `moderate_train_0000.png` (train/moderate) — dom_frac=0.972, gray_std=11.5
- `moderate_train_0001.png` (train/moderate) — dom_frac=0.972, gray_std=11.5
- `mild_val_0000.png` (val/mild) — dom_frac=0.972, gray_std=11.5
- `mild_val_0001.png` (val/mild) — dom_frac=0.972, gray_std=11.5
- `mild_val_0005.png` (val/mild) — dom_frac=0.972, gray_std=11.5
- `mild_val_0009.png` (val/mild) — dom_frac=0.972, gray_std=11.5
- `mild_val_0012.png` (val/mild) — dom_frac=0.972, gray_std=11.5
- `mild_test_0000.png` (test/mild) — dom_frac=0.972, gray_std=11.5
- `mild_test_0008.png` (test/mild) — dom_frac=0.972, gray_std=11.5
- `mild_test_0009.png` (test/mild) — dom_frac=0.972, gray_std=11.5
- `mild_test_0014.png` (test/mild) — dom_frac=0.972, gray_std=11.5
- `mild_train_0000.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0006.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0010.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0011.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0021.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0023.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0029.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0032.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0035.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0051.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0053.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0055.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0058.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0059.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0062.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0064.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `mild_train_0069.png` (train/mild) — dom_frac=0.962, gray_std=9.9
- `moderate_train_0002.png` (train/moderate) — dom_frac=0.962, gray_std=9.9
- `mild_val_0007.png` (val/mild) — dom_frac=0.962, gray_std=9.9
- `mild_val_0010.png` (val/mild) — dom_frac=0.962, gray_std=9.9
- `mild_val_0013.png` (val/mild) — dom_frac=0.962, gray_std=9.9
- `mild_test_0003.png` (test/mild) — dom_frac=0.962, gray_std=9.9
- `mild_test_0004.png` (test/mild) — dom_frac=0.962, gray_std=9.9
- `moderate_test_0000.png` (test/moderate) — dom_frac=0.962, gray_std=9.9

> Interprétation : plus `dom_frac` est élevé, plus l'image est un aplat uniforme (diapo). Une vraie photo d'animal dépasse rarement 0,40.


## Recommandations

1. **Retirer** ces images du jeu (option `--apply` -> quarantaine).

2. Le biais de fond subsistera : photos saines (extérieur) vs malades (intérieur clinique). Pour le casser durablement : **recadrer les DEUX groupes sur la zone d'intérêt** (museau/bouche/yeux) ou collecter des images saines de même nature (gros plans, même contexte).

3. Re-vérifier avec le Grad-CAM après nettoyage.
