#!/bin/bash

# AIDO-Lab Quick Setup for Mac
# Run this script in your aido-lab directory

echo "🚀 Setting up AIDO-Lab on Mac..."

# Create all necessary directories
echo "📁 Creating project structure..."

# Backend directories
mkdir -p backend/app/{api/routes,services,models,utils,core}
mkdir -p backend/{tests,alembic/versions,scripts}

# Frontend directories
mkdir -p frontend/{app,components/{ui,chat,code-viewer,history-tree,plots},lib,public,styles,hooks,store,types}

# Other directories
mkdir -p docker/kernels
mkdir -p workspaces
mkdir -p docs/{api,guides,architecture}
mkdir -p .github/workflows

echo "✅ Directory structure created"

# Create Python service files
echo "📝 Creating Python service files..."

# Create empty Python files for services
touch backend/app/__init__.py
touch backend/app/services/__init__.py
touch backend/app/services/kernel_manager.py
touch backend/app/services/git_service.py
touch backend/app/services/llm_service.py
touch backend/app/models/__init__.py
touch backend/app/models/schemas.py
touch backend/app/utils/__init__.py
touch backend/app/utils/session_manager.py
touch backend/app/utils/file_manager.py
touch backend/app/utils/auth.py
touch backend/app/core/__init__.py
touch backend/app/core/config.py
touch backend/app/main.py

echo "✅ Python files created"

# Create requirements.txt
cat > backend/requirements.txt << 'EOF'
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
python-dotenv==1.0.0

# Docker & Jupyter
docker==6.1.3
jupyter-client==8.6.0
ipykernel==6.27.1
pyzmq==25.1.1

# LLM
openai==1.3.7
anthropic==0.7.7

# Git
GitPython==3.1.40

# Data Science
pandas==2.1.3
numpy==1.26.2
matplotlib==3.8.2
seaborn==0.13.0

# Utils
pydantic==2.5.2
aiofiles==23.2.1
EOF

echo "✅ Requirements.txt created"

# Create package.json
cat > frontend/package.json << 'EOF'
{
  "name": "aido-lab-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.0.3",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-tabs": "^1.0.4",
    "lucide-react": "^0.294.0",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.3.2"
  }
}
EOF

echo "✅ Package.json created"

# Create .env.example
cat > .env.example << 'EOF'
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Environment
ENVIRONMENT=development
DEBUG=true

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

echo "✅ Environment template created"

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./workspaces:/app/workspaces
      - ./backend/app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
    command: npm run dev

volumes:
  workspaces:
EOF

echo "✅ Docker Compose created"

# Create backend Dockerfile
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    git \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

echo "✅ Backend Dockerfile created"

# Create frontend Dockerfile
cat > frontend/Dockerfile << 'EOF'
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
EOF

echo "✅ Frontend Dockerfile created"

# Create kernel Dockerfile
cat > docker/kernels/Dockerfile << 'EOF'
FROM jupyter/scipy-notebook:latest

USER root

RUN pip install --no-cache-dir \
    pandas matplotlib seaborn scikit-learn plotly

RUN mkdir -p /workspace && \
    chown -R ${NB_UID}:${NB_GID} /workspace

USER ${NB_UID}

WORKDIR /workspace

ENV JUPYTER_ENABLE_LAB=no
ENV JUPYTER_TOKEN=disabled

CMD ["jupyter", "kernel", "--kernel", "python3"]
EOF

echo "✅ Kernel Dockerfile created"

# Create a simple README
cat > README.md << 'EOF'
# AIDO-Lab

AI-Driven Data Science Platform

## Quick Start

1. Copy `.env.example` to `.env` and add your API keys
2. Install dependencies:
   - Backend: `cd backend && pip install -r requirements.txt`
   - Frontend: `cd frontend && npm install`
3. Run with Docker: `docker-compose up`
4. Access at http://localhost:3000

## Features

- Natural language to code generation
- Sandboxed code execution
- Git-based version control
- Real-time collaboration
EOF

echo "✅ README created"

# Create Makefile
cat > Makefile << 'EOF'
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
EOF

echo "✅ Makefile created"

echo ""
echo "✅ Project structure created successfully!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Copy the Python service code into these files:"
echo "   - backend/app/services/kernel_manager.py"
echo "   - backend/app/services/git_service.py"
echo "   - backend/app/services/llm_service.py"
echo "   - backend/app/main.py"
echo "   - backend/app/models/schemas.py"
echo ""
echo "2. Set up your environment:"
echo "   cp .env.example .env"
echo "   # Edit .env and add your OpenAI API key"
echo ""
echo "3. Install and run:"
echo "   # With Docker (recommended):"
echo "   docker-compose up"
echo ""
echo "   # Or run locally:"
echo "   cd backend && python -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   uvicorn app.main:app --reload"
echo ""
echo "Ready to start development! 🚀"
