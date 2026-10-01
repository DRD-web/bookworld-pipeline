-- queries.sql : version finale lisible des requêtes SQL utilisées dans le projet
-- Requêtes 1 et 2 : extraction depuis data/bookworld_reference.db (pipeline.py)
-- Requête 3 : lecture de l'agrégat dans data/bookworld_final.db (api.py)

-- Requête 1 : canaux de vente actifs (requête avec filtre)
-- Rôle : ne garde que les canaux actifs (is_active = 1). Écarte AFF, canal
-- inactif sans aucune vente ; WEB, APP et MKT sont conservés.
SELECT * FROM channels WHERE is_active = 1;

-- Requête 2 : référentiel des pays (requête d'enrichissement)
-- Rôle : fournit country_name pour joindre le nom du pays aux ventes
-- (clean_sales, sur country_code). NL est absent du référentiel : son nom
-- est complété dans pipeline.py.
SELECT * FROM countries;

-- Requête 3 : ventes agrégées par pays (lecture de l'agrégat par l'API)
-- Rôle : exécutée par api.py sur la base finale, pas sur la base de référence.
-- Pays triés par chiffre d'affaires en livres sterling, du plus élevé au plus faible.
SELECT country_code, country_name, total_orders, total_quantity,
       total_revenue_gbp, total_revenue_eur
FROM sales_by_country
ORDER BY total_revenue_gbp DESC;
