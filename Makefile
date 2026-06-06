.PHONY: install run-backend run-frontend dev \
        docker-up docker-down docker-restart docker-logs docker-status \
        docker-build push \
        index test clean help

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

run-backend:
	cd backend && uvicorn main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

dev:
	make -j2 run-backend run-frontend

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-restart:
	docker compose down
	docker compose up -d

docker-build:
	docker compose build --no-cache

docker-status:
	docker compose ps

docker-logs:
	docker compose logs -f --tail=50

docker-logs-backend:
	docker compose logs backend -f --tail=50

docker-logs-infinity:
	docker compose logs infinity -f --tail=50

index:
	cd backend && python scripts/index_books_direct.py

test:
	cd backend && pytest tests/ -v

test-pipeline:
	cd backend && python scripts/test_generation.py

push:
	git add -A
	git status
	@read -p "Commit message: " msg; git commit -m "$$msg"
	git push

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

help:
	@echo ""
	@echo "AI Running Coach — Makefile"
	@echo "─────────────────────────────"
	@echo "  make install"
	@echo "  make dev"
	@echo "  make docker-up"
	@echo "  make docker-down"
	@echo "  make docker-restart"
	@echo "  make docker-status"
	@echo "  make docker-logs"
	@echo "  make docker-build"
	@echo "  make index"
	@echo "  make test"
	@echo "  make push"
	@echo "  make clean"
	@echo "─────────────────────────────"
