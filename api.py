import hmac
import os
import sqlite3
from contextlib import closing

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)
app.json.sort_keys = False

DB_PATH = "data/bookworld_final.db"
API_TOKEN = os.getenv("API_TOKEN")
TOKEN_MODELE = "change-me"

QUERY_SALES_BY_COUNTRY = """
SELECT country_code, country_name, total_orders, total_quantity,
       total_revenue_gbp, total_revenue_eur
FROM sales_by_country
ORDER BY total_revenue_gbp DESC
"""


def token_configure():
    """Indique si un vrai token est défini côté serveur (ni absent, ni la valeur du modèle)."""
    return bool(API_TOKEN) and API_TOKEN != TOKEN_MODELE


def token_valide():
    """Vérifie que l'en-tête Authorization contient « Bearer » suivi du bon token."""
    en_tete = request.headers.get("Authorization", "")
    if not en_tete.startswith("Bearer "):
        return False
    token_recu = en_tete[len("Bearer "):]
    return hmac.compare_digest(token_recu.encode(), API_TOKEN.encode())


@app.route("/health", methods=["GET"])
def health():
    """Indique si l'API fonctionne : serveur actif et base de données présente (accès public)."""
    if not os.path.exists(DB_PATH):
        return jsonify({"status": "error", "detail": "Base de données introuvable"}), 503
    return jsonify({"status": "ok"}), 200


@app.route("/sales-by-country", methods=["GET"])
def sales_by_country():
    """Renvoie les ventes agrégées par pays en JSON (accès protégé par token)."""
    if not token_configure():
        message = "Serveur mal configuré : définir API_TOKEN dans .env (voir README)"
        return jsonify({"error": message}), 500
    if not token_valide():
        return jsonify({"error": "Token manquant ou invalide"}), 401
    if not os.path.exists(DB_PATH):
        return jsonify({"error": "Base de données introuvable"}), 500
    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(QUERY_SALES_BY_COUNTRY).fetchall()
    except sqlite3.Error:
        return jsonify({"error": "Erreur lors de la lecture de la base"}), 500
    return jsonify([dict(row) for row in rows]), 200


if __name__ == "__main__":
    app.run()
