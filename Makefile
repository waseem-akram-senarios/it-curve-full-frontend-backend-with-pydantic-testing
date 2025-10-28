.PHONY: help build up down logs restart clean ps shell-backend shell-frontend

help: ## Show this help message
	@echo "Voice Agent - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

restart: ## Restart all services
	docker-compose restart

rebuild: ## Rebuild and restart all services
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

clean: ## Stop services and remove volumes
	docker-compose down -v

ps: ## Show status of all services
	docker-compose ps

shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

status: ## Show running containers
	docker-compose ps

backend: ## Build and run only backend
	docker-compose up -d backend

frontend: ## Build and run only frontend
	docker-compose up -d frontend

# Individual build commands
build-backend: ## Build only backend image
	docker-compose build backend

build-frontend: ## Build only frontend image
	docker-compose build frontend

