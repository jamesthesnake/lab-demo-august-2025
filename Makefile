.PHONY: help dev build clean

help:
	@echo "Available commands:"
	@echo "  make dev    - Start development environment"
	@echo "  make build  - Build Docker images"
	@echo "  make clean  - Clean up containers"

dev:
	docker-compose up

build:
	docker-compose build

clean:
	docker-compose down -v
