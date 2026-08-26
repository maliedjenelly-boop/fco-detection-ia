# FCO Studio — Détection de la Fièvre Catarrhale Ovine par IA supervisée

Système d'**aide à la décision** pour la détection précoce de la fièvre catarrhale
ovine (FCO), combinant deux volets complémentaires et une application web :

- 🧪 **Volet laboratoire** — détection à partir de la charge virale (Random Forest, sans fuite de données) ;
- 🖼️ **Volet image** — vision par ordinateur (EfficientNet-B0, apprentissage par transfert, explicabilité Grad-CAM) ;
- 🗄️ **Base de données** relationnelle (SQLite / MySQL) unifiant CSV, JSON et Excel ;
- 💻 **Application Streamlit** (modes Laboratoire, Éleveur, Conseiller, Contacts).

> Projet de thèse professionnelle — Mastère Data & Intelligence Artificielle
> (RNCP 37137, Nexa Digital School). Réalisé chez **Cerfrance Champagne Nord-Est
> Île-de-France**.

---

## 🔗 Liens

- **Application en ligne :** https://fco-detection-ia-xux2c4ulonysuunt34dv8y.streamlit.app/
- **Documentation technique détaillée :** [`corrige/README.md`](corrige/README.md)

## 🚀 Démarrage rapide

```bash
git clone https://github.com/maliedjenelly-boop/fco-detection-ia.git
cd fco-detection-ia
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
cd corrige && streamlit run 03_app_streamlit.py
```

Comptes de démonstration : `admin` / `labo` / `eleveur` / `conseiller` — mot de passe `fco2026`.

## 📂 Structure

```
├── corrige/         # code : application Streamlit + scripts ML (01 à 08)
├── bdd/             # base de données, dump SQL, scripts ETL, documentation
├── memoire/         # mémoire (thèse)
├── LICENCE.md       # conditions d'utilisation
└── README.md        # ce fichier
```

## 🎯 Résultats clés (lecture honnête)

- Détection labo : apport réel **modeste** (AUC ≈ 0,70) — l'information décisive est la charge, mesurée directement.
- **BTV-3 vs BTV-8 non séparables** par la charge, relation **non reproductible** entre essais (paradoxe de Simpson).
- Volet image : un test à **100 % est un signal d'alarme** (biais de source), pas une réussite → diagnostic de biais documenté.

La contribution principale n'est pas un score, mais une **démarche rigoureuse** (anti-fuite de données, biais documentés, baselines).

---

## 📜 Licence

**© 2025-2026 MALIEDJE Nelly Leaticia — Tous droits réservés.**

Ce projet est publié à des fins de **consultation et d'évaluation académique**.
**Toute exploitation commerciale ou à des fins lucratives est interdite** sans
autorisation écrite préalable de l'autrice. Toute utilisation non autorisée
constitue une **contrefaçon** (art. L.335-2 du Code de la propriété intellectuelle)
et pourra donner lieu à des **poursuites judiciaires**.

👉 Conditions complètes : [**LICENCE.md**](LICENCE.md)
