import os
import sqlite3
from contextlib import closing

import pandas as pd
import requests
from bs4 import BeautifulSoup

CSV_PATH = "data/sales_raw.csv"
REFERENCE_DB_PATH = "data/bookworld_reference.db"
FINAL_DB_PATH = "data/bookworld_final.db"
SCHEMA_PATH = "schema_final.sql"
CATALOG_URL = "https://books.toscrape.com/"
RATES_URL = "https://api.frankfurter.dev/v2/rates"

QUERY_CHANNELS = "SELECT * FROM channels WHERE is_active = 1"
QUERY_COUNTRIES = "SELECT * FROM countries"
PAYS_EXCLUS = []
NOMS_PAYS_MANQUANTS = {"NL": "Netherlands"}


def load_csv(chemin=CSV_PATH):
    """Lit sales_raw.csv et renvoie les ventes brutes (None en cas d'erreur)."""
    try:
        sales = pd.read_csv(chemin, parse_dates=["order_date"], date_format="%Y-%m-%d", encoding="utf-8")
        return sales
    except FileNotFoundError:
        print(f"Erreur : fichier {chemin} introuvable.")
        return None
    except Exception as e:
        print(f"Erreur inattendue lors de la lecture du CSV : {e}")
        return None


def load_sqlite(chemin=REFERENCE_DB_PATH):
    """Lit les canaux actifs et les pays ; renvoie (countries, channels), ou (None, None) si erreur."""
    if not os.path.exists(chemin):
        print(f"Erreur : fichier {chemin} introuvable.")
        return None, None
    try:
        with closing(sqlite3.connect(chemin)) as conn:
            channels = pd.read_sql_query(QUERY_CHANNELS, conn)
            countries = pd.read_sql_query(QUERY_COUNTRIES, conn)
        return countries, channels
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        print(f"Erreur lors de la lecture de la base SQLite : {e}")
        return None, None


def scrape_catalog(url=CATALOG_URL):
    """Scrape la première page de books.toscrape.com ; renvoie un DataFrame (title, price_gbp), ou None si erreur."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        html = response.text

        soup = BeautifulSoup(html, "html.parser")
        blocs = soup.find_all("article", class_="product_pod")

        if not blocs:
            print("Aucun livre trouvé sur la page : structure inattendue.")
            return None

        lignes = []
        for bloc in blocs:
            lien = bloc.find("h3").find("a")
            titre = lien["title"]
            texte_prix = bloc.find("p", class_="price_color").get_text(strip=True)
            prix = float(texte_prix.replace("£", ""))
            lignes.append({"title": titre, "price_gbp": prix})

        catalogue = pd.DataFrame(lignes)
        return catalogue
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête vers le site : {e}")
        return None
    except (AttributeError, KeyError, ValueError) as e:
        print(f"Structure de page inattendue : {e}")
        return None


def get_exchange_rates(date_debut, date_fin, url=RATES_URL):
    """
    Récupère les taux GBP vers EUR (source BCE) entre deux dates.
    Renvoie un DataFrame (date, gbp_eur_rate), ou None si erreur.
    """
    try:
        params = {
            "base": "GBP",
            "quotes": "EUR",
            "from": date_debut,
            "to": date_fin,
            "providers": "ecb",
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        donnees = response.json()

        if not donnees:
            print("Aucun taux de change reçu : réponse vide.")
            return None

        taux = pd.DataFrame(donnees)
        taux = taux[["date", "rate"]].rename(columns={"rate": "gbp_eur_rate"})
        taux["date"] = pd.to_datetime(taux["date"])
        taux = taux.sort_values("date").reset_index(drop=True)
        return taux
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête vers l'API de taux de change : {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Réponse de l'API inattendue : {e}")
        return None


def clean_sales(sales, countries, catalogue):
    """
    Retire les noms des clients (RGPD), ajoute le nom du pays
    (NL via NOMS_PAYS_MANQUANTS) et le prix de chaque livre.
    """
    orders = sales.drop(columns=["customer_first_name", "customer_last_name"])
    orders = orders[~orders["country_code"].isin(PAYS_EXCLUS)]
    orders = orders.merge(countries[["country_code", "country_name"]], on="country_code", how="left")
    orders["country_name"] = orders["country_name"].fillna(orders["country_code"].map(NOMS_PAYS_MANQUANTS))
    orders = orders.merge(catalogue, left_on="book_name", right_on="title", how="left").drop(columns="title")
    return orders


def add_exchange_rate(orders, taux):
    """
    Rattache à chaque commande le taux de sa date, ou du dernier jour publié avant
    (week-end, jour férié). Renvoie None si erreur.
    """
    orders = orders.sort_values("order_date")

    if orders["order_date"].dtype != taux["date"].dtype:
        print("Erreur : types de dates différents entre ventes et taux.")
        return None

    taux = taux.rename(columns={"date": "rate_date"})
    orders = pd.merge_asof(orders, taux, left_on="order_date", right_on="rate_date", direction="backward")

    return orders


def compute_revenue(orders):
    """Calcule le chiffre d'affaires de chaque commande en £ (remise incluse), puis en €."""
    orders["revenue_gbp"] = orders["quantity"] * orders["price_gbp"] * (1 - orders["discount_rate"])
    orders["revenue_eur"] = orders["revenue_gbp"] * orders["gbp_eur_rate"]

    return orders


def build_sales_by_country(orders):
    """
    Agrège les commandes par pays (commandes, quantités, CA en £ et en €),
    triées par CA en livres sterling décroissant.
    """
    sales_by_country = orders.groupby(["country_code", "country_name"], as_index=False).agg(
        total_orders=("order_id", "nunique"),
        total_quantity=("quantity", "sum"),
        total_revenue_gbp=("revenue_gbp", "sum"),
        total_revenue_eur=("revenue_eur", "sum"),
    )
    sales_by_country = sales_by_country.round(2)
    sales_by_country = sales_by_country.sort_values("total_revenue_gbp", ascending=False).reset_index(drop=True)
    return sales_by_country


def build_final_tables(countries, channels, orders, sales_by_country):
    """
    Prépare les cinq tables de la base finale, sans aucune donnée personnelle.
    countries : référentiel allégé (code, nom), complété par NL, absent du référentiel.
    channels : canaux actifs (code, nom).
    books : un livre par ligne, construit depuis les commandes.
    orders : les dix colonnes de la table orders, dates converties en texte AAAA-MM-JJ.
    """
    final_countries = countries[["country_code", "country_name"]]
    missing = pd.DataFrame(list(NOMS_PAYS_MANQUANTS.items()), columns=["country_code", "country_name"])
    missing = missing[~missing["country_code"].isin(final_countries["country_code"])]
    final_countries = pd.concat([final_countries, missing], ignore_index=True)

    final_channels = channels[["channel_code", "channel_name"]]

    final_books = orders[["book_id", "book_name", "price_gbp"]].drop_duplicates().rename(columns={"book_name": "title"})

    colonnes_orders = [
        "order_id", "order_date", "book_id", "country_code", "channel_code",
        "quantity", "discount_rate", "gbp_eur_rate", "revenue_gbp", "revenue_eur",
    ]
    final_orders = orders[colonnes_orders].copy()
    final_orders["order_date"] = final_orders["order_date"].dt.strftime("%Y-%m-%d")

    return {
        "countries": final_countries,
        "channels": final_channels,
        "books": final_books,
        "orders": final_orders,
        "sales_by_country": sales_by_country,
    }


def save_final_db(tables, schema_path=SCHEMA_PATH, db_path=FINAL_DB_PATH):
    """Crée la base finale avec schema_final.sql puis y charge les cinq tables ; renvoie True si tout s'est bien passé."""
    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = f.read()
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(schema)
            for name in ["countries", "channels", "books", "orders", "sales_by_country"]:
                tables[name].to_sql(name, conn, if_exists="append", index=False)
            conn.commit()
        return True
    except FileNotFoundError:
        print(f"Erreur : fichier {schema_path} introuvable.")
        return False
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        print(f"Erreur lors de l'écriture de la base finale : {e.__cause__ or e}")
        return False


def main():
    """Enchaîne extraction, nettoyage, enrichissement, agrégation puis création de la base finale."""
    sales = load_csv()
    if sales is None:
        print("Extraction interrompue : ventes indisponibles.")
        return

    countries, channels = load_sqlite()
    if countries is None:
        print("Extraction interrompue : référentiel SQLite indisponible.")
        return

    catalogue = scrape_catalog()
    if catalogue is None:
        print("Extraction interrompue : catalogue indisponible.")
        return

    date_debut = sales["order_date"].min().strftime("%Y-%m-%d")
    date_fin = sales["order_date"].max().strftime("%Y-%m-%d")
    taux = get_exchange_rates(date_debut, date_fin)
    if taux is None:
        print("Extraction interrompue : taux de change indisponibles.")
        return

    print(
        f"Extraction terminée : {len(sales)} ventes, {len(countries)} pays, "
        f"{len(catalogue)} livres, {len(taux)} taux de change."
    )

    try:
        orders = clean_sales(sales, countries, catalogue)
        if orders["country_name"].isna().any() or orders["price_gbp"].isna().any():
            print("Nettoyage interrompu : nom de pays ou prix manquant après jointure.")
            return

        orders = add_exchange_rate(orders, taux)
        if orders is None or orders["gbp_eur_rate"].isna().any():
            print("Enrichissement interrompu : taux de change non rattachés.")
            return

        orders = compute_revenue(orders)
        if orders[["revenue_gbp", "revenue_eur"]].isna().any().any():
            print("Calcul interrompu : chiffre d'affaires manquant.")
            return

        sales_by_country = build_sales_by_country(orders)
        if (sales_by_country["total_orders"].sum() != len(orders)
                or sales_by_country["total_quantity"].sum() != orders["quantity"].sum()):
            print("Agrégation interrompue : totaux incohérents avec les commandes.")
            return

        tables = build_final_tables(countries, channels, orders, sales_by_country)
    except (KeyError, ValueError) as e:
        print(f"Transformation interrompue : colonne manquante ou valeur inattendue ({e}).")
        return

    if not save_final_db(tables):
        print("Écriture interrompue : base finale non créée.")
        return
    print(f"Base finale créée : {FINAL_DB_PATH} ({len(orders)} commandes, {len(sales_by_country)} pays).")


if __name__ == "__main__":
    main()
