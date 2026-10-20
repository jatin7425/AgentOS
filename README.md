# AgentOS

Open-source, self-hosted platform to build and run AI agents.

## Local development

Requires Node.js 22.12+ (or 24+) and Python 3.10+.

```sh
make install
```

Run these in separate terminals:

```sh
make dev-server
make dev-client
```

- Frontend: http://localhost:5173
- API health: http://127.0.0.1:8000/health → `{"status":"ok"}`
- Interactive API docs: http://127.0.0.1:8000/docs

The React page requests `/api/health`. Vite proxies `/api/*` to FastAPI on port 8000, removing the `/api` prefix. For a production deployment, configure the same routing in your reverse proxy.

## Checks

```sh
make build
cd apps/client && npm run lint
curl http://127.0.0.1:8000/health
```

The frontend lives in `apps/client`; the backend entry point is `apps/server/api/app.py`. Backend dependencies are in `apps/server/requirements.txt`, with installed versions pinned in `requirements.lock.txt`. No database or secrets are required for the health endpoint.
