-- ===========================================================================
--  BASE DE DONNÉES FCO — Schéma relationnel (SQLite)
--  Projet de détection de la Fièvre Catarrhale Ovine.
--
--  Choix du SGBD : SQLite, embarqué et sans serveur — cohérent avec la
--  volumétrie réelle (≈ 1 250 lignes). Le schéma est portable : pour migrer
--  vers MySQL/MariaDB, voir les notes [MySQL] en commentaire.
-- ===========================================================================

PRAGMA foreign_keys = ON;   -- [MySQL] : moteur InnoDB (clés étrangères natives)

DROP TABLE IF EXISTS mesure_virale;
DROP TABLE IF EXISTS image;
DROP TABLE IF EXISTS veterinaire;
DROP TABLE IF EXISTS serotype;
DROP TABLE IF EXISTS essai;

-- --- Table de référence : essai expérimental --------------------------------
CREATE TABLE essai (
    id_essai  INTEGER PRIMARY KEY,        -- [MySQL] INT PRIMARY KEY
    libelle   TEXT NOT NULL
);

-- --- Table de référence : sérotype ------------------------------------------
CREATE TABLE serotype (
    id_serotype     INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,  -- NC / BTV3 / BTV8
    libelle         TEXT NOT NULL,
    est_infectieux  INTEGER NOT NULL       -- 0 = non (NC), 1 = oui
);

-- --- Table de faits : mesures de charge virale (source CSV) -----------------
CREATE TABLE mesure_virale (
    id_mesure      INTEGER PRIMARY KEY,    -- [MySQL] INT AUTO_INCREMENT
    id_individu    INTEGER NOT NULL,
    id_essai       INTEGER NOT NULL,
    id_serotype    INTEGER NOT NULL,
    dpi            INTEGER NOT NULL,        -- jour post-infection (0 ou 6)
    genome_copies  REAL    NOT NULL,        -- charge virale
    detectable     INTEGER NOT NULL,        -- 1 si genome_copies > 0
    FOREIGN KEY (id_essai)    REFERENCES essai(id_essai),
    FOREIGN KEY (id_serotype) REFERENCES serotype(id_serotype)
);

-- --- Catalogue des images (source JSON) -------------------------------------
CREATE TABLE image (
    id_image  INTEGER PRIMARY KEY,
    fichier   TEXT NOT NULL,
    classe    TEXT NOT NULL,               -- sain / malade
    severite  TEXT,                         -- healthy / mild / moderate / severe
    source    TEXT,                         -- stock / pdf_clinique
    split     TEXT                          -- train / val / test
);

-- --- Contacts vétérinaires (source XLSX, données personnelles -> RGPD) -------
CREATE TABLE veterinaire (
    id_vet     INTEGER PRIMARY KEY,
    nom        TEXT NOT NULL,
    clinique   TEXT,
    type       TEXT,
    ville      TEXT,
    telephone  TEXT,                         -- numéros fictifs ARCEP (exemples)
    email      TEXT
);

-- NB : les index d'optimisation sont créés par optimisation_requetes.py afin
-- de mesurer le temps des requêtes AVANT / APRÈS optimisation (cf. guide).
