# Optimisation des requêtes — comparaison avant/après index

Requête testée :

```sql
SELECT id_mesure, genome_copies FROM mesure_virale WHERE id_individu=? AND id_essai=?
```

Exécutée **120000 fois** (table = 1249 lignes).

| Version | Index | Temps total | Plan d'exécution |
| --- | --- | --- | --- |
| Non optimisée | aucun | 8878 ms | SCAN mesure_virale |
| Optimisée | idx_mesure_indiv, idx_mesure_sero_dpi | 5650 ms | SEARCH mesure_virale USING INDEX idx_mesure_indiv (id_individu=? AND id_essai=?) |

**Accélération : ×1.6.** L'index transforme le parcours complet (SCAN) en recherche indexée (SEARCH USING INDEX).
