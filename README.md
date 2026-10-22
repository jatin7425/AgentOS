# AgentOS

Open-source, self-hosted platform to build and run AI agents.

## Docker (frontend, backend and database)

Requires Docker with Compose v2. From the repository root:

```sh
docker compose up --build -d --wait
# or: make up
```

No `.env` files or configuration steps are needed.

- Frontend: http://localhost:8080
- Health through frontend: http://localhost:8080/api/v1/health
- Backend health: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/api/docs

Use `make logs` to follow logs and `make down` to stop all services.
The frontend image builds React and serves it with Nginx. `/api/*` is proxied to `server:8000` preserving the `/api` prefix. Compose waits for the API health check before starting the frontend. All services have health checks. The backend waits for PostgreSQL to become healthy.

Ports are defined directly in `docker-compose.yml`. To change a host port, edit the left side of its port mapping; internal container ports stay the same. After changing code, run `make up` to rebuild.

## Update the backend

The backend runs only in Docker. After changing backend code:

```sh
make update-server
```

This rebuilds the backend image and recreates its container as needed, waits for it to become healthy, and leaves the frontend container running. `make dev-server` starts the backend and its database dependency, including on a fresh checkout. Use `make logs-server` for backend logs and `make status` to check all services.

`make build` builds both Docker images without starting them. Run `make` to see all available commands.

## Local frontend development

Requires Node.js 22.12+ (or 24+) and Docker with Compose v2. The API still runs in Docker; no local Python environment is needed.

```sh
make install
```

Start the Docker backend, then run Vite:

```sh
make dev-server
make dev-client
```

- Frontend: http://localhost:5173
- API health: http://127.0.0.1:8000/api/v1/health → `{"status":"ok"}`
- Interactive API docs: http://127.0.0.1:8000/api/docs

The React page requests `/api/v1/health`. Vite proxies `/api/*` to FastAPI on port 8000, preserving the `/api` prefix. The Docker frontend includes the equivalent Nginx proxy.

## Checks

```sh
make build-client
cd apps/client && npm run lint
curl http://127.0.0.1:8000/api/v1/health
```

The frontend lives in `apps/client`; the backend entry point is `apps/server/api/app.py`. Backend dependencies are in `apps/server/requirements.txt`, with installed versions pinned in `requirements.lock.txt`. Startup verifies both database connections before serving requests.

## PostgreSQL and pgvector

Compose runs PostgreSQL 17 with pgvector 0.8.6 in the `db` service. On first initialization, `docker/postgres/init.sql` creates two databases: `agentos` for relational data and `agentos_vectors` for vectors. The `vector` extension is enabled in `agentos_vectors`.

- Host connection: `postgresql://agentos:agentos@localhost:5432/agentos`
- Backend container: `postgresql://agentos:agentos@db:5432/agentos` (provided as `DATABASE_URL`)
- Vector host connection: `postgresql://agentos:agentos@localhost:5432/agentos_vectors`
- Vector backend connection: `postgresql://agentos:agentos@db:5432/agentos_vectors` (`VECTOR_DB_URL`)
- User/password for both databases: `agentos` (local development defaults defined in Compose)

The backend opens separate SQLAlchemy async engines and connection pools for relational data and vectors at startup and closes both on shutdown. Application tables are not implemented yet. PostgreSQL is published only on the host loopback interface.

Data persists in the `postgres_data` named volume across container rebuilds and `make down`. Initialization scripts run only when that volume is first created. No `.env` files are required.

For an existing volume created before the database split, apply the initialization script without deleting data, then update the backend:

```sh
docker compose exec -T db psql -U agentos -d agentos -v ON_ERROR_STOP=1 < docker/postgres/init.sql
make update-server
```

The script is safe to rerun. It creates missing databases and enables pgvector; it does not migrate existing tables or remove any existing extensions.

Open a database shell or verify pgvector:

```sh
docker compose exec db psql -U agentos -d agentos
docker compose exec db psql -U agentos -d agentos_vectors -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

Run the database integration checks against the running Docker backend:

```sh
docker compose exec -T server python < apps/server/tests/test_db_integration.py
```

## Backend connections

`db/data_store.py` provides a SQLAlchemy 2 async engine, `async_sessionmaker`, and the FastAPI dependencies `get_data_store` and `get_data_session`. Use `async with store.session() as session` for ORM work, or `async with store.connection() as connection` for SQLAlchemy Core. Both contexts commit on success and roll back on errors. Raw SQL must be wrapped in `sqlalchemy.text()`.

```python
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from db.data_store import get_data_session

async def read_database(session: AsyncSession = Depends(get_data_session)):
    result = await session.execute(text("SELECT current_database()"))
    return {"database": result.scalar_one()}
```

Compose URLs stay unchanged; the connection layer selects SQLAlchemy's async Psycopg driver (`postgresql+psycopg`). SQLAlchemy manages pooling; no separate Psycopg pool is used.

`db/vector_store.py` provides the `VectorStore` lifecycle protocol, a `PgVectorStore` SQLAlchemy adapter with registered vector types, the `create_vector_store` factory, and `get_vector_store`. FastAPI stores both instances on `app.state`; startup verifies both connections and releases pools if initialization fails.

Configuration is defined directly in Compose:

- `DATABASE_URL`: relational PostgreSQL connection.
- `VECTOR_DB_URL`: vector database connection, pointing to `agentos_vectors` on the same PostgreSQL instance. Defaults to `DATABASE_URL` if omitted.
- `VECTOR_STORE_BACKEND`: currently `pgvector`; unknown backends fail at startup.

For a future Qdrant migration, implement a Qdrant adapter and register it in the factory, then change the vector backend and URL in Compose. The relational store remains PostgreSQL. This adds the connection boundary only: future vector insert/search/delete methods must use backend-neutral inputs/results on the protocol, with provider-specific queries inside adapters. Existing vectors will need migration to Qdrant.

Backend environment access is centralized in `apps/server/config/env.py`. `get_env()` reads and validates `DATABASE_URL`, `VECTOR_DB_URL`, and `VECTOR_STORE_BACKEND` at startup. Missing or blank values fail with the variable name, without logging its value. Docker Compose supplies these variables directly; no `.env` file is loaded.
