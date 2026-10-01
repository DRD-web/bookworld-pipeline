-- schema_final.sql : structure de la base finale BookWorld
-- Ce fichier crée uniquement la structure (tables vides, clés, relations).
-- Les données sont chargées ensuite par le pipeline (pipeline.py).
-- Aucune donnée personnelle : pas de nom ni de prénom de client (RGPD, 3.1).

-- On supprime d'abord les tables si elles existent (relance possible du
-- pipeline), en commençant par celles qui dépendent des autres (tables enfants).
DROP TABLE IF EXISTS sales_by_country;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS channels;
DROP TABLE IF EXISTS countries;

-- Pays (référentiel allégé : code et nom)
CREATE TABLE countries (
    country_code TEXT PRIMARY KEY,
    country_name TEXT NOT NULL
);

-- Canaux de vente actifs
CREATE TABLE channels (
    channel_code TEXT PRIMARY KEY,
    channel_name TEXT NOT NULL
);

-- Catalogue des livres vendus (identifiant du CSV, titre et prix du site scrapé)
CREATE TABLE books (
    book_id   TEXT PRIMARY KEY,
    title     TEXT NOT NULL,
    price_gbp REAL NOT NULL CHECK (price_gbp > 0)
);

-- Commandes : une ligne par commande, sans aucune donnée personnelle
CREATE TABLE orders (
    order_id      TEXT PRIMARY KEY,
    order_date    TEXT NOT NULL,
    book_id       TEXT NOT NULL,
    country_code  TEXT NOT NULL,
    channel_code  TEXT NOT NULL,
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    discount_rate REAL NOT NULL CHECK (discount_rate >= 0 AND discount_rate <= 1),
    gbp_eur_rate  REAL NOT NULL,
    revenue_gbp   REAL NOT NULL,
    revenue_eur   REAL NOT NULL,
    FOREIGN KEY (book_id)      REFERENCES books (book_id),
    FOREIGN KEY (country_code) REFERENCES countries (country_code),
    FOREIGN KEY (channel_code) REFERENCES channels (channel_code)
);

-- Ventes agrégées par pays (indicateur exposé par l'API)
CREATE TABLE sales_by_country (
    country_code      TEXT PRIMARY KEY,
    country_name      TEXT NOT NULL,
    total_orders      INTEGER NOT NULL,
    total_quantity    INTEGER NOT NULL,
    total_revenue_gbp REAL NOT NULL,
    total_revenue_eur REAL NOT NULL,
    FOREIGN KEY (country_code) REFERENCES countries (country_code)
);
