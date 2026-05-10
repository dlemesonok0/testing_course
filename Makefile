.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend build seed test test-backend test-backend-api test-backend-unit test-backend-coverage

help:
	@echo "Available targets:"
	@echo "  make install                 Install backend and frontend dependencies"
	@echo "  make install-backend         Create backend venv and install Python requirements"
	@echo "  make install-frontend        Install frontend npm dependencies"
	@echo "  make dev                     Run backend and frontend dev servers"
	@echo "  make dev-backend             Run FastAPI dev server"
	@echo "  make dev-frontend            Run frontend dev server"
	@echo "  make build                   Build frontend"
	@echo "  make seed                    Seed backend test data"
	@echo "  make test                    Run all backend tests"
	@echo "  make test-backend            Run all backend tests"
	@echo "  make test-backend-api        Run backend API integration tests"
	@echo "  make test-backend-unit       Run backend unit tests"
	@echo "  make test-backend-coverage   Run backend tests with coverage"

install:
	npm run install:all

install-backend:
	npm run install:backend

install-frontend:
	npm run install:frontend

dev:
	npm run dev

dev-backend:
	npm run dev:backend

dev-frontend:
	npm run dev:frontend

build:
	npm run build

seed:
	npm run seed

test:
	npm run test

test-backend:
	npm run test:backend

test-backend-api:
	npm run test:backend:api

test-backend-unit:
	npm run test:backend:unit

test-backend-coverage:
	npm run test:backend:coverage
