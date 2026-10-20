.PHONY: install dev-client dev-server build

install:
	cd apps/client && npm ci
	python3 -m venv apps/server/.venv
	apps/server/.venv/bin/python -m pip install -r apps/server/requirements.lock.txt

dev-client:
	cd apps/client && npm run dev

dev-server:
	cd apps/server && .venv/bin/python -m uvicorn api.app:app --reload --host 127.0.0.1 --port 8000

build:
	cd apps/client && npm run build
