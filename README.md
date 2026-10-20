# AgentOS

Open-source, self-hosted platform to build and run AI agents.

## Docker (both services)

Requires Docker with Compose v2. From the repository root:

```sh
docker compose up --build -d --wait
# or: make up
```

No `.env` files or configuration steps are needed.

- Frontend: http://localhost:8080
- Health through frontend: http://localhost:8080/api/health
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

Use `make logs` to follow logs and `make down` to stop both services.
The frontend image builds React and serves it with Nginx. `/api/*` is proxied to `server:8000` with the `/api` prefix removed. Compose waits for the API health check before starting the frontend. Both containers have health checks.

Ports are defined directly in `docker-compose.yml`. To change a host port, edit the left side of its port mapping; internal container ports stay the same. After changing code, run `make up` to rebuild.

## Update the backend

The backend runs only in Docker. After changing backend code:

```sh
make update-server
```

This rebuilds the backend image and recreates its container as needed, waits for it to become healthy, and leaves the frontend container running. `make dev-server` is an alias for the same command. Use `make logs-server` for backend logs and `make status` to check both services.

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
- API health: http://127.0.0.1:8000/health → `{"status":"ok"}`
- Interactive API docs: http://127.0.0.1:8000/docs

The React page requests `/api/health`. Vite proxies `/api/*` to FastAPI on port 8000, removing the `/api` prefix. The Docker frontend includes the equivalent Nginx proxy.

## Checks

```sh
make build-client
cd apps/client && npm run lint
curl http://127.0.0.1:8000/health
```

The frontend lives in `apps/client`; the backend entry point is `apps/server/api/app.py`. Backend dependencies are in `apps/server/requirements.txt`, with installed versions pinned in `requirements.lock.txt`. No database or secrets are required for the health endpoint.
