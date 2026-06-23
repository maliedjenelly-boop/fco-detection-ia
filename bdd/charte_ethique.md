# Charte éthique & cartographie des risques liés aux données

## 1. Cartographie des risques (qualité, sécurité, éthique)

| Risque | Nature | Gravité | Mesure d'atténuation |
| --- | --- | --- | --- |
| Biais de source des images | Qualité des données | Élevée | Audit du dataset + Grad-CAM ; biais documenté et assumé, pas masqué |
| Données personnelles (vétérinaires) | Sécurité / RGPD | Moyenne | Vue masquant les emails, accès lecture seule, données d'exemple |
| Sur-interprétation médicale (faux négatif) | Éthique / sécurité | Élevée | Outil présenté comme aide à la décision, jamais comme diagnostic ; renvoi systématique au vétérinaire |
| Confondants statistiques (essai) | Qualité de l'analyse | Moyenne | Stratification + validation inter-essais ; conclusions nuancées |
| Reproductibilité | Fiabilité | Moyenne | Graines aléatoires fixées, scripts versionnés et réexécutables |
| Empreinte environnementale | Sociétal | Faible | Petits modèles (EfficientNet-B0, RF), entraînement court, transfer learning |

## 2. Charte éthique du projet

1. **Transparence sur les limites.** Chaque performance est présentée avec sa baseline et ses biais. Aucun résultat n'est embelli.
2. **Pas de diagnostic automatisé.** L'outil aide à la décision ; la confirmation relève d'un vétérinaire. Un avertissement est affiché dans l'application.
3. **Protection des données.** Respect du RGPD : minimisation, contrôle d'accès, finalité explicite, aucune donnée personnelle réelle stockée.
4. **Non-discrimination.** Le modèle ne traite ni espèce, ni origine d'élevage de façon discriminante ; il vise un usage sanitaire collectif.
5. **Responsabilité scientifique.** Les biais détectés (source des images, confondant essai) sont publiés dans le mémoire comme résultats à part entière.
6. **Sobriété.** Choix de modèles et d'un SGBD dimensionnés au besoin réel (volumétrie), pour limiter le coût et l'empreinte.

## 3. Conformité réglementaire — points de contrôle

- FCO = maladie animale **réglementée à déclaration obligatoire** : l'outil oriente vers le vétérinaire sanitaire et la DD(ec)PP.
- Données personnelles : voir `securite_rgpd.md`.
- Sources externes (images du PDF clinique) : usage documenté et cité.
