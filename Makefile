.PHONY: install source-data pipeline test lint format serve docker-build docker-up docker-down clean

install:
	pip install -r requirements.txt

source-data:
	python -m src.extract.generate_source_data

pipeline:
	python -m src.pipeline

test:
	pytest

lint:
	ruff check src tests

format:
	black src tests
	isort src tests

serve:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload

docker-build:
	docker build -f docker/Dockerfile -t retail-etl-warehouse:latest .

docker-up:
	docker compose --profile etl run --rm etl
	docker compose up -d api

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
