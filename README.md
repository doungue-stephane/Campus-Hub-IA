# CampusHub Backend

**Description**

Backend FastAPI pour CampusHub — plateforme de matching compétences, projets, clubs, mentorat et événements. API asynchrone avec SQLAlchemy Async + asyncpg, migrations gérées par Alembic, et exécution via Docker Compose.

**Ce qui a été réalisé**

- Architecture FastAPI modulaire (modules : `auth`, `users`, `skills`, etc.).
- Modèles SQLAlchemy asynchrones dans `app/modules/*/models.py`.
- Gestion des mots de passe via `passlib` (algorithme `bcrypt_sha256`).
- Migrations Alembic configurées et migrations appliquées :
  - `6bde11955290_create_users_and_refresh_tokens_tables.py`
  - `540495ebbcd4_create_skills_and_user_skills_tables.py`
- Containerisation avec `Dockerfile` et `docker-compose.yml`.
- Variables d'environnement centralisées dans `.env`.

**Structure principale**

- [app/main.py](app/main.py) — entrée FastAPI, enregistrement des routeurs
- [app/core](app/core) — configuration, base de données, sécurité
- [app/modules](app/modules) — modules fonctionnels (auth, users, skills...)
- [alembic/](alembic) — configuration et versions Alembic
- docker-compose.yml, Dockerfile, requirements.txt

**Variables d'environnement** (.env)

- `POSTGRES_USER` — utilisateur PostgreSQL (ex : `campushub`)
- `POSTGRES_PASSWORD` — mot de passe DB
- `POSTGRES_DB` — nom de la base (ex : `campushub`)
- `DATABASE_URL` — chaîne SQLAlchemy (ex : `postgresql+asyncpg://user:pw@db:5432/dbname`)
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- `DEBUG`, `APP_NAME`, `APP_VERSION`, `ENVIRONMENT`

**Exécution avec Docker (recommandé)**

1. Construire et démarrer les conteneurs :

```bash
docker compose up --build
```

2. Voir les logs :

```bash
docker compose logs -f api
```

3. Exécuter des commandes dans le conteneur API (ex. créer une migration) :

```bash
docker compose exec api bash
# puis, à l'intérieur du conteneur
alembic revision --autogenerate -m "message"
alembic upgrade head
pytest
```

4. Accès local :
- API : `http://localhost:8000`
- Docs Swagger : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

**Migrations Alembic**

- Pour générer une migration à partir des modèles :

```bash
docker compose exec api alembic revision --autogenerate -m "ma migration"
```

- Pour appliquer les migrations :

```bash
docker compose exec api alembic upgrade head
```

- Si la base contient déjà une version et que vous voulez aligner manuellement :

```bash
docker compose exec api alembic stamp <revision_id>
```

**Tests**

- Lancer la suite :

```bash
docker compose exec api pytest
```

- Remarque : le dossier `tests/` doit contenir des fichiers `test_*.py`.
