# Sécurisation des données & conformité RGPD

## Données personnelles identifiées
- Table `veterinaire` : `nom`, `telephone`, `email` (donnée à caractère personnel).

## Mesures mises en place
| Mesure | Principe RGPD | Mise en œuvre |
| --- | --- | --- |
| Minimisation | Art. 5.1.c | Vue `v_veterinaire_public` masquant l'email (`****@domaine`) |
| Contrôle d'accès | Intégrité & confidentialité | Connexion **lecture seule** pour les usages non administratifs |
| Données d'exemple | Pas de données réelles | Numéros de **fiction ARCEP**, domaine `exemple.fr` |
| Limitation de conservation | Art. 5.1.e | Base reconstructible à la demande, pas d'historique conservé |
| Traçabilité | Responsabilité | Scripts d'ETL versionnés et reproductibles |

## Points de contrôle RGPD
1. Aucune donnée personnelle réelle n'est stockée (jeu d'exemple).
2. Les accès applicatifs utilisent la **vue masquée**, pas la table brute.
3. L'accès en écriture est réservé à l'administrateur de la base.
4. Finalité explicite : mise en relation éleveur ↔ vétérinaire en cas de suspicion.
