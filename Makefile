install:
	pip install -r requirements.txt
	cd frontend && npm install

run-backend:
	uvicorn backend.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

run-ollama:
	ollama pull llama3.2:3b
	ollama serve

scrape:
	python backend/scripts/scrape_books.py
	python backend/scripts/scrape_articles.py

index:
	python backend/scripts/index_all_sources.py

test:
	pytest backend/tests/

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

deploy-backend:
	git push origin main
	# Render.com auto-deploy

deploy-frontend:
	cd frontend && npm run build
	vercel --prod