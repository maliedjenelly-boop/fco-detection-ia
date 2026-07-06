# Déploiement sur Streamlit Community Cloud

Guide pour mettre l'application FCO en ligne gratuitement, depuis le dépôt GitHub
`fco-detection-ia`.

## 1. Prérequis
- Le dépôt GitHub est prêt : **maliedjenelly-boop/fco-detection-ia** (branche `main`).
- Un compte sur https://share.streamlit.io (connexion avec GitHub).

## 2. Déployer l'application
1. Aller sur **https://share.streamlit.io** et se connecter avec GitHub.
2. Cliquer sur **« Create app »** puis **« Deploy a public app from GitHub »**
   (Streamlit Cloud peut aussi déployer un dépôt **privé** après autorisation).
3. Renseigner :
   - **Repository** : `maliedjenelly-boop/fco-detection-ia`
   - **Branch** : `main`
   - **Main file path** : `corrige/03_app_streamlit.py`
4. (Optionnel) *Advanced settings* → **Python version : 3.11**.
5. Cliquer **« Deploy »**. La première construction prend quelques minutes.

## 3. Dépendances
Streamlit Cloud installe automatiquement le fichier **`requirements.txt`** à la racine
du dépôt. Il est volontairement **léger** (pas de PyTorch) pour respecter le tier gratuit :
l'application fonctionne pour le **Mode Laboratoire** et la page **Contacts**.

## 4. Base de données
- Les identifiants MySQL pointent sur `localhost` : **inaccessible depuis le cloud**.
- L'application **bascule automatiquement sur la base SQLite** `bdd/fco.db` (incluse dans
  le dépôt). **Aucun secret n'est nécessaire** pour un déploiement fonctionnel.
- *Option serveur* : pour utiliser un vrai MySQL hébergé, renseigner dans
  *App → Settings → Secrets* :
  ```toml
  [mysql]
  host = "adresse_du_serveur"
  port = 3306
  user = "fco_user"
  password = "•••••"
  database = "fco_db"
  ```

## 5. Limites du tier gratuit
- Le **Mode Éleveur** (image, EfficientNet/PyTorch) est **désactivé en ligne** : PyTorch est
  trop lourd pour le tier gratuit. Il reste **pleinement fonctionnel en local**
  (`corrige/requirements.txt` installe torch, torchvision, timm, opencv).
- Pour l'activer en ligne, il faudrait un tier payant et ajouter ces dépendances.

## 6. Après déploiement
- L'URL publique est de la forme `https://<votre-app>.streamlit.app`.
- Chaque `git push` sur `main` redéploie automatiquement l'application.
