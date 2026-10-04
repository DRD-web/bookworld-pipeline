# BookWorld : pipeline de données et API des ventes par pays

BookWorld est une entreprise fictive de vente de livres en ligne. Ses données sont dispersées entre plusieurs sources ; ce projet les rassemble dans un pipeline de données, produit une base SQL finale et expose les ventes agrégées par pays via une API REST.

Le pipeline (`pipeline.py`) :

1. lit un fichier CSV de ventes brutes ;
2. lit une base SQLite de référentiels métier (pays, canaux de vente) ;
3. scrape la première page du catalogue de https://books.toscrape.com/ ;
4. récupère les taux de change livre sterling vers euro via l'API publique Frankfurter ;
5. nettoie et enrichit les données, calcule le chiffre d'affaires par pays, puis crée la base finale `data/bookworld_final.db`.

L'API (`api.py`), développée avec Flask, met à disposition les ventes agrégées par pays, avec une authentification par token.

## Contenu du dépôt

| Fichier ou dossier | Rôle |
|---|---|
| `README.md` | Ce document |
| `pipeline.py` | Extraction, nettoyage, enrichissement, agrégation et création de la base finale |
| `api.py` | API REST : `GET /health` et `GET /sales-by-country` |
| `queries.sql` | Requêtes SQL du projet : extraction depuis la base de référence (requêtes 1 et 2) et lecture de l'agrégat par l'API (requête 3) |
| `schema_final.sql` | Structure de la base finale (5 tables, clés et contraintes), sans donnée personnelle |
| `requirements.txt` | Bibliothèques Python à installer |
| `.env.example` | Modèle du fichier `.env` qui contient le token de l'API |
| `.gitignore` | Fichiers exclus du dépôt (`.env`, `venv`, `__pycache__`) |
| `data/sales_raw.csv` | Ventes brutes (noms et prénoms supprimés : colonnes remplies par « anonyme ») |
| `data/bookworld_reference.db` | Base SQLite de référentiels métier |
| `data/bookworld_final.db` | Base finale produite par le pipeline, fournie pour tester l'API sans relancer le pipeline |
| `docs/schema_bookworld.png` | Schéma relationnel de la base finale |

## Récupérer le projet

Le dépôt est public : le cloner ne demande ni compte ni mot de passe.

```
git clone https://github.com/DRD-web/bookworld-pipeline.git
cd bookworld-pipeline
```

Le dossier cloné contient déjà les données (`data/`), mais pas le fichier `.env` (voir « Configuration du token de l'API »). Toutes les commandes suivantes se lancent depuis ce dossier.

## Authentification : token de l'API, token GitHub, clé SSH

Trois mécanismes à ne pas confondre :

| Mécanisme | Ce qu'il protège | Dans ce projet |
|---|---|---|
| Token de l'API (`API_TOKEN` dans `.env`) | la route `/sales-by-country` de l'API | utilisé (voir plus bas) |
| Token GitHub (Git Credential Manager) | l'écriture (`git push`) sur le dépôt GitHub | utilisé |
| Clé SSH | l'écriture sur le dépôt, en alternative au token GitHub | non utilisée |

Lire et cloner le dépôt ne demande aucune authentification, car il est public. Il en faut une pour y écrire.

**Token GitHub (méthode utilisée).** Le projet est cloné et poussé en HTTPS. Au premier `git push`, le Git Credential Manager (fourni avec Git pour Windows) ouvre le navigateur : on se connecte à GitHub et on autorise l'accès. Le jeton obtenu est conservé dans le gestionnaire d'identifiants de Windows et réutilisé aux envois suivants. Aucun mot de passe n'est saisi dans le terminal et aucun jeton n'est stocké dans le dépôt.

**Clé SSH (alternative, non testée dans ce projet).** Procédure standard :

1. Créer une paire de clés : `ssh-keygen -t ed25519 -C "adresse-e-mail"`. La clé privée reste sur l'ordinateur et ne se partage jamais.
2. Copier le contenu du fichier `.pub` (clé publique) dans GitHub : Settings, SSH and GPG keys, New SSH key.
3. Cloner avec l'adresse SSH : `git clone git@github.com:DRD-web/bookworld-pipeline.git`.
4. Tester la connexion : `ssh -T git@github.com`.

## Installation

Il faut Python 3.11 ou plus récent (minimum exigé par pandas 3.0.6). Le projet a été testé avec Python 3.13.9 ; les versions 3.11 et 3.12 n'ont pas été testées. Toutes les commandes se lancent depuis la racine du projet (le dossier qui contient `pipeline.py`).

**1. Créer et activer un environnement virtuel**

Windows (PowerShell) :

```
python -m venv venv
venv\Scripts\Activate.ps1
```

Si plusieurs versions de Python sont installées, créer l'environnement avec `py -3.13 -m venv venv` (remplacer 3.13 par une version 3.11 ou plus récente).

Si PowerShell refuse d'exécuter le script d'activation, autoriser les scripts pour la session en cours, puis relancer l'activation :

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

macOS ou Linux :

```
python3 -m venv venv
source venv/bin/activate
```

**2. Installer les dépendances**

```
python -m pip install -r requirements.txt
```

Versions testées le 1er octobre 2026 : Python 3.13.9, pandas 3.0.6, Flask 3.1.3, requests 2.34.2, beautifulsoup4 4.15.0, python-dotenv 1.2.3. Les dépendances indirectes (par exemple numpy 2.5.3) sont installées par pip dans la dernière version compatible au jour de l'installation ; si une version ultérieure pose problème, revenir aux versions indiquées ici.

## Configuration du token de l'API

L'API protège la route `/sales-by-country` par un token. Ce token n'est pas fourni avec le dépôt : chacun définit le sien dans un fichier `.env`, qui n'est pas versionné.

**1. Copier le modèle**

Windows (PowerShell) :

```
Copy-Item .env.example .env
```

macOS ou Linux :

```
cp .env.example .env
```

**2. Générer une valeur aléatoire**

```
python -c "import secrets; print(secrets.token_hex(24))"
```

**3. Renseigner le token**

Ouvrir `.env` et remplacer `change-me` par la valeur générée, sans espace ni guillemets :

```
API_TOKEN=la-valeur-generee
```

Cette valeur doit être différente de `change-me` : tant que le token n'est pas configuré, l'API répond par une erreur 500. C'est cette même valeur qu'il faudra envoyer dans chaque appel à `/sales-by-country`.

## Exécution du pipeline

Le pipeline a besoin d'une connexion internet : il interroge le site books.toscrape.com et l'API Frankfurter. Depuis la racine du projet, avec l'environnement virtuel activé :

```
python pipeline.py
```

Si tout se passe bien, deux messages s'affichent :

```
Extraction terminée : 240 ventes, 10 pays, 20 livres, 123 taux de change.
Base finale créée : data/bookworld_final.db (240 commandes, 8 pays).
```

Les 10 pays comptés à l'extraction sont ceux du référentiel. 8 pays ont des ventes (dont NL, absent du référentiel), et la table `countries` de la base finale en compte 11 (les 10 pays du référentiel plus NL).

Le pipeline recrée la base `data/bookworld_final.db` à chaque exécution, à partir de `schema_final.sql`. Si une source est indisponible (site, API, fichier manquant) ou si un contrôle de cohérence échoue, il s'arrête avec un message qui indique l'étape en cause.

## Lancement de l'API

Depuis la racine du projet, avec l'environnement virtuel activé et le token configuré dans `.env` :

```
python api.py
```

L'API est alors disponible à l'adresse `http://127.0.0.1:5000`. Le terminal reste occupé tant que le serveur tourne ; l'arrêter avec `Ctrl + C`. L'API lit `data/bookworld_final.db` avec un chemin relatif : elle doit être lancée depuis la racine du projet. Elle peut être testée sans relancer le pipeline, la base étant fournie dans le dépôt.

Sur certaines versions de macOS, le port 5000 peut être déjà utilisé par le service AirPlay. Dans ce cas, lancer l'API sur un autre port, puis remplacer 5000 par 5001 dans les adresses des exemples ci-dessous :

```
flask --app api run --port 5001
```

| Route | Accès | Rôle |
|---|---|---|
| `GET /health` | public | Indique si l'API fonctionne : `{"status": "ok"}` (code 200), ou le code 503 si la base de données est introuvable |
| `GET /sales-by-country` | protégé par token | Renvoie les ventes agrégées par pays, triées par chiffre d'affaires en livres sterling décroissant |

Pour appeler `/sales-by-country`, le client envoie le token dans l'en-tête `Authorization`, sous la forme `Bearer <token>` (la valeur définie dans `.env`). Codes de réponse :

| Code | Signification |
|---|---|
| 200 | Succès : la liste des pays est renvoyée |
| 401 | Token absent ou invalide |
| 500 | Token non configuré côté serveur (`.env` absent ou valeur `change-me`), ou base de données introuvable ou illisible |
| 503 | `/health` seulement : base de données introuvable |

Exemple de réponse (début) :

```json
[
  {
    "country_code": "DE",
    "country_name": "Germany",
    "total_orders": 40,
    "total_quantity": 110,
    "total_revenue_gbp": 4014.7,
    "total_revenue_eur": 4755.1
  }
]
```

## Tester l'API

Avec l'API lancée dans un premier terminal, ouvrir un second terminal à la racine du projet.

Windows (PowerShell) :

```
Invoke-RestMethod -Uri http://127.0.0.1:5000/health
$token = (Get-Content .env | Select-String "API_TOKEN=").ToString().Split("=")[1]
Invoke-RestMethod -Uri http://127.0.0.1:5000/sales-by-country -Headers @{Authorization = "Bearer $token"} | Format-Table
```

macOS ou Linux :

```
curl http://127.0.0.1:5000/health
TOKEN=$(grep API_TOKEN .env | cut -d= -f2)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/sales-by-country
```

Sans le token (ou avec un mauvais token), la seconde route répond par une erreur 401 : `{"error": "Token manquant ou invalide"}`. Si le token n'est pas configuré côté serveur, elle répond par une erreur 500 : `{"error": "Serveur mal configuré : définir API_TOKEN dans .env (voir README)"}`. Dans PowerShell, ces réponses s'affichent sous la forme d'une erreur, ce qui est normal.

Testé sous Windows (PowerShell) et Linux (bash) ; non testé sous macOS.

## Données personnelles (RGPD)

Le fichier de ventes brutes d'origine contient le nom et le prénom des clients. Ces informations ne sont pas nécessaires à l'usage final de la base : conformément au principe de minimisation des données (RGPD, article 5), le pipeline les supprime, et la base finale n'en contient aucune trace.

Pour la même raison, le fichier `data/sales_raw.csv` de ce dépôt n'est pas l'original : les noms et prénoms y sont supprimés (les colonnes `customer_first_name` et `customer_last_name` contiennent partout la valeur « anonyme »). Toutes les autres colonnes sont identiques, et le pipeline donne exactement le même résultat. Les données du projet sont fictives. Avec le fichier d'origine, placé dans `data/` sous le même nom, le pipeline fonctionne de la même façon.

## Limites connues

- **Catalogue** : seule la première page du site est scrapée (20 livres), comme demandé ; les 20 livres vendus s'y trouvent.
- **Pays absent du référentiel** : les 19 commandes du pays NL n'ont pas de nom de pays dans la base de référence ; le nom « Netherlands » est ajouté dans le code (`NOMS_PAYS_MANQUANTS`). Les ventes du Portugal, pays marqué inactif dans le référentiel, sont conservées : le filtre `is_active = 1` ne porte que sur les canaux de vente. Ces deux choix sont assumés.
- **Chiffre d'affaires** : calculé après remise (quantité × prix × (1 − remise)), hors taxes (le prix du site est sans taxe). Seul le chiffre d'affaires est converti en euros, commande par commande, au taux de sa date : le prix des livres n'est pas converti, car un prix en euros dépend de la date. Pour un week-end ou un jour férié, c'est le taux du dernier jour publié qui s'applique.
- **Table `category_rules`** : non utilisée, car la catégorie des livres n'apparaît pas sur la première page du site.
- **Première date de taux** : les taux sont demandés à partir de la date de la première vente (le 03/01/2025, un vendredi). Si une première vente tombait un week-end, aucun taux antérieur n'existerait et le pipeline s'arrêterait avec le message « taux de change non rattachés » ; avec ces données, ce cas ne se présente pas.
- **Services externes** : le pipeline dépend du site books.toscrape.com et de l'API Frankfurter. Si l'un d'eux est indisponible, il s'arrête ; la base finale fournie permet de tester l'API malgré tout.
- **Écriture de la base** : si l'écriture de la base finale est interrompue, elle peut rester incomplète ; relancer le pipeline la recrée entièrement.
- **Dépendances** : `requirements.txt` ne fige que les 5 bibliothèques utilisées directement.
- **API** : le token est unique et statique (sans expiration ni identité par utilisateur) et circule en HTTP simple, sans HTTPS. L'API utilise le serveur de développement intégré à Flask, non prévu pour la production, et lit un chemin relatif : elle doit être lancée depuis la racine du projet.
