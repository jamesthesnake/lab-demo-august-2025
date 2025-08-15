#!/bin/bash
# setup.sh - Complete setup script for AIDO-Lab Platform

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="aido-lab"
KERNEL_IMAGE_NAME="aido-kernel"
BACKEND_IMAGE_NAME="aido-backend"
FRONTEND_IMAGE_NAME="aido-frontend"

# Function to print colored output
print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

# ASCII Art Banner
show_banner() {
    echo -e "${BLUE}"
    cat << 'EOF'
     ___   _____  ____    ___         _         ___   ____  
    / _ \ |_   _||  _ \  / _ \       | |       / _ \ | __ ) 
   / /_\ \  | |  | | | || | | | ___  | |      / /_\ \|  _ \ 
  / /___\ \ | |  | |_| || |_| ||___| | |___  / /___\ \ |_) |
 /_/     \_\|_|  |____/  \___/       |_____||_/     \_\____/ 
                                                              
  AI-Driven Data Science Platform for GenBio AI
EOF
    echo -e "${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        missing_deps+=("nodejs")
    fi
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        missing_deps+=("npm")
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_info "Please install the missing dependencies and try again."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_status "All prerequisites met!"
}

# Setup environment variables
setup_env() {
    print_info "Setting up environment variables..."
    
    if [ ! -f backend/.env ]; then
        cat > backend/.env << 'EOF'
# ============================================================================
# AIDO-Lab Environment Configuration
# ============================================================================

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=info

# Security
SECRET_KEY=your-secret-key-here-replace-with-generated-key
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Database (for future use)
DATABASE_URL=postgresql://aido:aido@postgres:5432/aido_lab

# Redis (for future use)
REDIS_URL=redis://redis:6379

# Workspace Configuration
WORKSPACE_BASE=/app/workspaces
MAX_WORKSPACE_SIZE_MB=1000

# Kernel Configuration
KERNEL_IMAGE=aido-kernel:latest
MAX_KERNELS=10
KERNEL_TIMEOUT=3600
EXECUTION_TIMEOUT=30
KERNEL_MEMORY_LIMIT=2g
KERNEL_CPU_LIMIT=2

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Frontend Configuration
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Git Configuration
GIT_USER_NAME=AIDO-Lab
GIT_USER_EMAIL=aido@genbio.ai

# File Upload Configuration
MAX_UPLOAD_SIZE_MB=100
ALLOWED_EXTENSIONS=.csv,.json,.txt,.py,.ipynb,.xlsx,.xls,.tsv,.parquet,.h5,.hdf5,.pkl,.joblib

# Session Configuration
SESSION_TIMEOUT_MINUTES=60
MAX_SESSIONS_PER_USER=5
AUTO_CLEANUP_SESSIONS=true

# Development
DEBUG=false
ENVIRONMENT=development
EOF
        
        print_warning "Created .env file in backend/. Please update with your API keys!"
        print_info "To generate a secure secret key, run:"
        print_info "  openssl rand -hex 32"
    else
        print_status ".env file already exists in backend/"
    fi
    
    # Create frontend .env if needed
    if [ ! -f frontend/.env.local ]; then
        cat > frontend/.env.local << 'EOF'
# Frontend Environment Variables
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=AIDO-Lab
NEXT_PUBLIC_VERSION=0.1.0
EOF
        print_status "Created .env.local file in frontend/"
    fi
}

# Build Jupyter kernel Docker image
build_kernel_image() {
    print_info "Building Jupyter kernel Docker image..."
    
    # Create kernel Dockerfile if it doesn't exist
    mkdir -p docker/kernels
    cat > docker/kernels/Dockerfile << 'EOF'
FROM jupyter/scipy-notebook:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch back to jovyan user
USER $NB_UID

# Install Python packages for data science
RUN pip install --no-cache-dir \
    pandas==2.0.3 \
    numpy==1.24.3 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    scikit-learn==1.3.0 \
    scipy==1.11.1 \
    statsmodels==0.14.0 \
    plotly==5.15.0 \
    networkx==3.1 \
    biopython==1.81 \
    rdkit==2023.3.2 \
    lifelines==0.27.7 \
    xgboost==1.7.6 \
    lightgbm==4.0.0 \
    tensorflow==2.13.0 \
    torch==2.0.1 \
    transformers==4.31.0 \
    ipywidgets==8.1.0 \
    tqdm==4.65.0 \
    joblib==1.3.1 \
    openpyxl==3.1.2 \
    xlrd==2.0.1 \
    pyarrow==12.0.1 \
    fastparquet==2023.7.0 \
    h5py==3.9.0

# Enable extensions
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager

# Configure IPython kernel
RUN ipython profile create
RUN echo "c.InteractiveShellApp.matplotlib = 'inline'" >> ~/.ipython/profile_default/ipython_config.py

WORKDIR /home/jovyan/work

# Expose Jupyter port
EXPOSE 8888

CMD ["start.sh", "jupyter", "lab", "--NotebookApp.token=''", "--NotebookApp.password=''"]
EOF
    
    docker build -t ${KERNEL_IMAGE_NAME}:latest docker/kernels/
    print_status "Kernel image built successfully"
}

# Build backend Docker image
build_backend_image() {
    print_info "Building backend Docker image..."
    
    # Create backend Dockerfile if it doesn't exist
    if [ ! -f backend/Dockerfile ]; then
        cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create workspaces directory
RUN mkdir -p /app/workspaces

# Create non-root user
RUN useradd -m -s /bin/bash aido && \
    chown -R aido:aido /app

USER aido

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF
    fi
    
    # Create requirements.txt if it doesn't exist
    if [ ! -f backend/requirements.txt ]; then
        cat > backend/requirements.txt << 'EOF'
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
python-multipart==0.0.6

# Async
aiofiles==23.2.1
asyncio==3.4.3
httpx==0.25.1

# Data Processing
pandas==2.0.3
numpy==1.24.3
matplotlib==3.7.2
seaborn==0.12.2

# Jupyter & Code Execution
jupyter-client==8.6.0
ipykernel==6.26.0
nbformat==5.9.2
nbconvert==7.11.0

# Git Integration
gitpython==3.1.40

# LLM Integration
openai==1.3.5
anthropic==0.7.7
langchain==0.0.340
tiktoken==0.5.1

# Docker
docker==6.1.3

# Database (for future use)
sqlalchemy==2.0.23
alembic==1.12.1
asyncpg==0.29.0

# Redis (for future use)
redis==5.0.1

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.7

# WebSockets
websockets==12.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Utilities
pyyaml==6.0.1
click==8.1.7
rich==13.7.0
EOF
    fi
    
    cd backend
    docker build -t ${BACKEND_IMAGE_NAME}:latest .
    cd ..
    print_status "Backend image built successfully"
}

# Build frontend Docker image
build_frontend_image() {
    print_info "Building frontend Docker image..."
    
    # Create frontend Dockerfile if it doesn't exist
    if [ ! -f frontend/Dockerfile ]; then
        cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Production image
FROM node:18-alpine AS runner

WORKDIR /app

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {r.statusCode === 200 ? process.exit(0) : process.exit(1)})"

# Start command
CMD ["npm", "start"]
EOF
    fi
    
    cd frontend
    docker build -t ${FRONTEND_IMAGE_NAME}:latest .
    cd ..
    print_status "Frontend image built successfully"
}

# Create docker-compose.yml
create_docker_compose() {
    print_info "Creating docker-compose configuration..."
    
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: aido-postgres
    environment:
      POSTGRES_USER: aido
      POSTGRES_PASSWORD: aido
      POSTGRES_DB: aido_lab
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aido"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - aido-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: aido-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - aido-network

  # Backend API
  backend:
    image: aido-backend:latest
    container_name: aido-backend
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
      - workspaces:/app/workspaces
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - aido-network
    restart: unless-stopped

  # Frontend Application
  frontend:
    image: aido-frontend:latest
    container_name: aido-frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "3000:3000"
    depends_on:
      - backend
    networks:
      - aido-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  workspaces:

networks:
  aido-network:
    driver: bridge
EOF
    
    print_status "docker-compose.yml created"
}

# Initialize database
init_database() {
    print_info "Initializing database..."
    
    # Start only postgres service
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    print_info "Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Create database schema
    docker-compose exec -T postgres psql -U aido -d aido_lab << 'EOF'
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    workspace_path TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create executions table
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    results JSONB DEFAULT '{}'::jsonb,
    commit_sha TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX idx_sessions_active ON sessions(active);
CREATE INDEX idx_executions_session_id ON executions(session_id);
CREATE INDEX idx_executions_created_at ON executions(created_at);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE
    ON sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOF
    
    print_status "Database initialized"
}

# Start all services
start_services() {
    print_info "Starting all services..."
    
    docker-compose up -d
    
    print_info "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    if curl -s http://localhost:8000/health > /dev/null; then
        print_status "Backend is running"
    else
        print_warning "Backend may not be ready yet"
    fi
    
    if curl -s http://localhost:3000 > /dev/null; then
        print_status "Frontend is running"
    else
        print_warning "Frontend may not be ready yet"
    fi
    
    print_status "All services started!"
}

# Create demo notebook
create_demo_notebook() {
    print_info "Creating demo notebook..."
    
    cat > demo_analysis.py << 'EOF'
#!/usr/bin/env python3
"""
Demo script to test AIDO-Lab functionality
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

def test_platform():
    print("🧪 Testing AIDO-Lab Platform...")
    
    # 1. Check health
    print("\n1. Checking API health...")
    response = requests.get(f"{API_URL}/health")
    if response.status_code == 200:
        print("   ✓ API is healthy")
        print(f"   Services: {response.json()['services']}")
    
    # 2. Create session
    print("\n2. Creating new session...")
    response = requests.post(f"{API_URL}/api/sessions/create")
    if response.status_code == 200:
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"   ✓ Session created: {session_id}")
    else:
        print(f"   ✗ Failed to create session: {response.text}")
        return
    
    # 3. Execute natural language query
    print("\n3. Testing natural language to code...")
    queries = [
        "Create a sample dataset with 100 rows of sales data",
        "Show basic statistics of the data",
        "Create a bar chart of sales by category"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        response = requests.post(f"{API_URL}/api/execute", json={
            "session_id": session_id,
            "query": query,
            "is_natural_language": True,
            "task_type": "data_analysis"
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Generated code:")
            print("   " + "\n   ".join(result["code"].split("\n")[:5]))
            if result.get("results", {}).get("stdout"):
                print(f"   Output: {result['results']['stdout'][:100]}...")
        else:
            print(f"   ✗ Failed: {response.text}")
    
    # 4. Check history
    print("\n4. Checking execution history...")
    response = requests.get(f"{API_URL}/api/history/{session_id}")
    if response.status_code == 200:
        history = response.json()
        print(f"   ✓ Found {len(history['commits'])} commits")
    
    print("\n✅ Demo completed successfully!")
    print(f"\nAccess the platform at:")
    print(f"   Frontend: http://localhost:3000")
    print(f"   API Docs: http://localhost:8000/docs")
    print(f"   Session ID: {session_id}")

if __name__ == "__main__":
    test_platform()
EOF
    
    chmod +x demo_analysis.py
    print_status "Demo script created: demo_analysis.py"
}

# Main setup flow
main() {
    show_banner
    
    # Parse command line arguments
    case "${1:-}" in
        "build")
            check_prerequisites
            setup_env
            build_kernel_image
            build_backend_image
            build_frontend_image
            create_docker_compose
            print_status "Build completed successfully!"
            ;;
        "start")
            create_docker_compose
            init_database
            start_services
            print_status "Services started successfully!"
            print_info "Access the platform at:"
            print_info "  Frontend: http://localhost:3000"
            print_info "  API Docs: http://localhost:8000/docs"
            ;;
        "stop")
            print_info "Stopping services..."
            docker-compose down
            print_status "Services stopped"
            ;;
        "clean")
            print_warning "Cleaning up..."
            docker-compose down -v
            docker rmi ${KERNEL_IMAGE_NAME}:latest ${BACKEND_IMAGE_NAME}:latest ${FRONTEND_IMAGE_NAME}:latest 2>/dev/null || true
            rm -rf backend/workspaces/*
            print_status "Cleanup completed"
            ;;
        "demo")
            create_demo_notebook
            print_info "Running demo..."
            python3 demo_analysis.py
            ;;
        "logs")
            docker-compose logs -f ${2:-}
            ;;
        *)
            check_prerequisites
            setup_env
            build_kernel_image
            build_backend_image
            build_frontend_image
            create_docker_compose
            init_database
            start_services
            create_demo_notebook
            
            print_status "🎉 AIDO-Lab is ready!"
            print_info ""
            print_info "Access the platform:"
            print_info "  📊 Frontend: http://localhost:3000"
            print_info "  📚 API Docs: http://localhost:8000/docs"
            print_info "  🔍 Health:   http://localhost:8000/health"
            print_info ""
            print_info "Quick commands:"
            print_info "  ./setup.sh start  - Start services"
            print_info "  ./setup.sh stop   - Stop services"
            print_info "  ./setup.sh logs   - View logs"
            print_info "  ./setup.sh demo   - Run demo"
            print_info "  ./setup.sh clean  - Clean everything"
            ;;
    esac
}

# Run main function
main "$@"
