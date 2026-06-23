-- ===========================================================================
--  BASE DE DONNÉES FCO — Schéma MySQL / MariaDB (option « serveur »)
--  Équivalent du schéma SQLite, pour héberger la base avec identifiants de
--  connexion et back-office phpMyAdmin (cf. MIGRATION_MYSQL.md).
-- ===========================================================================

CREATE DATABASE IF NOT EXISTS fco_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fco_db;

DROP TABLE IF EXISTS mesure_virale;
DROP TABLE IF EXISTS image;
DROP TABLE IF EXISTS veterinaire;
DROP TABLE IF EXISTS serotype;
DROP TABLE IF EXISTS essai;

CREATE TABLE essai (
    id_essai  INT PRIMARY KEY,
    libelle   VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE serotype (
    id_serotype     INT PRIMARY KEY,
    code            VARCHAR(10) NOT NULL UNIQUE,
    libelle         VARCHAR(100) NOT NULL,
    est_infectieux  TINYINT NOT NULL
) ENGINE=InnoDB;

CREATE TABLE mesure_virale (
    id_mesure      INT PRIMARY KEY AUTO_INCREMENT,
    id_individu    INT NOT NULL,
    id_essai       INT NOT NULL,
    id_serotype    INT NOT NULL,
    dpi            INT NOT NULL,
    genome_copies  DOUBLE NOT NULL,
    detectable     TINYINT NOT NULL,
    CONSTRAINT fk_mesure_essai    FOREIGN KEY (id_essai)    REFERENCES essai(id_essai),
    CONSTRAINT fk_mesure_serotype FOREIGN KEY (id_serotype) REFERENCES serotype(id_serotype)
) ENGINE=InnoDB;

CREATE TABLE image (
    id_image  INT PRIMARY KEY AUTO_INCREMENT,
    fichier   VARCHAR(255) NOT NULL,
    classe    VARCHAR(20) NOT NULL,
    severite  VARCHAR(20),
    source    VARCHAR(20),
    split     VARCHAR(10)
) ENGINE=InnoDB;

CREATE TABLE veterinaire (
    id_vet     INT PRIMARY KEY AUTO_INCREMENT,
    nom        VARCHAR(150) NOT NULL,
    clinique   VARCHAR(150),
    type       VARCHAR(60),
    ville      VARCHAR(80),
    telephone  VARCHAR(30),
    email      VARCHAR(120)
) ENGINE=InnoDB;

-- Index d'optimisation (version OPTIMISÉE)
CREATE INDEX idx_mesure_indiv    ON mesure_virale (id_individu, id_essai);
CREATE INDEX idx_mesure_sero_dpi ON mesure_virale (id_serotype, dpi);
