# Migration vers MySQL / MariaDB (option « serveur » avec back-office)

La base de travail est SQLite (cohérente avec la volumétrie). Pour répondre au
point du guide demandant des **identifiants de connexion à la base SQL** et un
**accès administrateur au back-office**, voici comment héberger la même base sur
un serveur MySQL/MariaDB avec phpMyAdmin.

## 1. Installer le serveur + back-office

- Installer **XAMPP** (https://www.apachefriends.org) — fournit MariaDB + phpMyAdmin en un clic.
- Démarrer les modules **Apache** et **MySQL** depuis le panneau XAMPP.
- Ouvrir le back-office : **http://localhost/phpmyadmin**.

## 2. Créer la base et un utilisateur (identifiants de connexion)

Dans phpMyAdmin → onglet **SQL**, exécuter :

```sql
SOURCE schema_mysql.sql;   -- ou copier/coller le contenu de schema_mysql.sql

CREATE USER 'fco_user'@'localhost' IDENTIFIED BY 'MotDePasse_a_changer';
GRANT SELECT, INSERT, UPDATE, DELETE ON fco_db.* TO 'fco_user'@'localhost';
FLUSH PRIVILEGES;
```

**Identifiants de connexion (à mettre dans le dossier ZIP du rendu) :**

| Paramètre | Valeur |
| --- | --- |
| Hôte | localhost |
| Port | 3306 |
| Base | fco_db |
| Utilisateur | fco_user |
| Mot de passe | (celui défini ci-dessus) |
| Back-office | http://localhost/phpmyadmin |

## 3. Charger les données

Le schéma est créé ; il reste à insérer les données. Deux options :

**Option A — réutiliser l'ETL (recommandé).** Installer le connecteur puis pointer
le script sur MySQL :

```bash
pip install sqlalchemy pymysql
```

Adapter `build_database.py` pour écrire via SQLAlchemy :

```python
from sqlalchemy import create_engine
engine = create_engine("mysql+pymysql://fco_user:MotDePasse@localhost/fco_db")
# puis df.to_sql("mesure_virale", engine, if_exists="append", index=False)
```

**Option B — import direct.** Dans phpMyAdmin, onglet **Importer**, charger les
fichiers sources (CSV des mesures, etc.) table par table.

## 4. Dump SQL

Le dump SQLite (`fco_dump.sql`) est fourni. Pour un dump **MySQL** :

```bash
mysqldump -u fco_user -p fco_db > fco_db_mysql_dump.sql
```

> Remarque : le dump SQLite n'est pas directement importable dans MySQL (syntaxe
> différente). On régénère le schéma via `schema_mysql.sql` puis on recharge les
> données par l'ETL (Option A).
