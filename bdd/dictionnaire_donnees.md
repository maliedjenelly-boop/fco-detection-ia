# Dictionnaire de données — Base FCO

Base SQLite `fco.db`. Trois sources unifiées : CSV (labo), JSON (images), XLSX (vétérinaires).

## Table `essai`
| Colonne | Type | Description |
| --- | --- | --- |
| id_essai | INTEGER (PK) | Identifiant de l'essai expérimental |
| libelle | TEXT | Libellé de l'essai |

## Table `serotype`
| Colonne | Type | Description |
| --- | --- | --- |
| id_serotype | INTEGER (PK) | Identifiant du sérotype |
| code | TEXT | NC / BTV3 / BTV8 |
| libelle | TEXT | Libellé complet |
| est_infectieux | INTEGER | 0 = contrôle négatif, 1 = infectieux |

## Table `mesure_virale` (source CSV)
| Colonne | Type | Description |
| --- | --- | --- |
| id_mesure | INTEGER (PK) | Identifiant de la mesure |
| id_individu | INTEGER | N° de l'individu (moucheron) |
| id_essai | INTEGER (FK→essai) | Essai expérimental |
| id_serotype | INTEGER (FK→serotype) | Sérotype inoculé |
| dpi | INTEGER | Jour post-infection (0 ou 6) |
| genome_copies | REAL | Charge virale (copies du génome) |
| detectable | INTEGER | 1 si genome_copies > 0 |

## Table `image` (source JSON)
| Colonne | Type | Description |
| --- | --- | --- |
| id_image | INTEGER (PK) | Identifiant de l'image |
| fichier | TEXT | Nom du fichier image |
| classe | TEXT | sain / malade |
| severite | TEXT | healthy / mild / moderate / severe |
| source | TEXT | stock / pdf_clinique (trace le biais de source) |
| split | TEXT | train / val / test |

## Table `veterinaire` (source XLSX — données personnelles, RGPD)
| Colonne | Type | Description |
| --- | --- | --- |
| id_vet | INTEGER (PK) | Identifiant du vétérinaire |
| nom | TEXT | Nom de la clinique/du praticien |
| clinique | TEXT | Spécialité / structure |
| type | TEXT | Vétérinaire sanitaire / traitant / urgences |
| ville | TEXT | Ville |
| telephone | TEXT | Téléphone (numéros fictifs ARCEP en exemple) |
| email | TEXT | Email (donnée personnelle) |