.DEFAULT_GOAL := help

.PHONY: help up down build update-server logs logs-server status install dev-client dev-server build-client

help:
	@echo "make up             Build and start both Docker services"
	@echo "make down           Stop both Docker services"
	@echo "make build          Build both Docker images"
	@echo "make update-server  Rebuild and update only the backend in Docker"
	@echo "make dev-server     Start or update the backend in Docker"
	@echo "make logs           Follow all Docker service logs"
	@echo "make logs-server    Follow backend Docker logs"
	@echo "make status         Show Docker service status"
	@echo "make install        Install local frontend dependencies only"
	@echo "make dev-client     Run the local Vite frontend"
	@echo "make build-client   Build the frontend locally"

up:
	docker compose up --build -d --wait

down:
	docker compose down

build:
	docker compose build

update-server:
	docker compose up --build -d --no-deps --wait server

dev-server: update-server

logs:
	docker compose logs -f

logs-server:
	docker compose logs -f server

status:
	docker compose ps

install:
	cd apps/client && npm ci

dev-client:
	cd apps/client && npm run dev

build-client:
	cd apps/client && npm run build
