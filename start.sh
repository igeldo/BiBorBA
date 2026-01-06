#!/bin/bash

set -e

echo "==================================="
echo "LangGraph RAG - Startup Script"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Ollama is running locally
check_ollama() {
    echo -e "${YELLOW}Checking for local Ollama instance...${NC}"
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Ollama is running locally${NC}"
        return 0
    else
        echo -e "${RED}✗ Ollama is not running locally${NC}"
        return 1
    fi
}

# Check required models
check_models() {
    echo -e "${YELLOW}Checking required Ollama models...${NC}"

    REQUIRED_MODELS=("embeddinggemma" "gemma3:12b")
    MISSING_MODELS=()

    for model in "${REQUIRED_MODELS[@]}"; do
        if ollama list | grep -q "$model"; then
            echo -e "${GREEN}✓ Model $model is available${NC}"
        else
            echo -e "${RED}✗ Model $model is missing${NC}"
            MISSING_MODELS+=("$model")
        fi
    done

    if [ ${#MISSING_MODELS[@]} -ne 0 ]; then
        echo -e "${YELLOW}Installing missing models...${NC}"
        for model in "${MISSING_MODELS[@]}"; do
            echo -e "${YELLOW}Pulling $model...${NC}"
            ollama pull "$model"
        done
    fi
}

# Start backend services
start_backend() {
    echo -e "${YELLOW}Starting backend services (PostgreSQL, ChromaDB, FastAPI)...${NC}"
    cd langgraph-rag
    docker-compose up -d db chroma app
    cd ..
    echo -e "${GREEN}✓ Backend services started${NC}"
}

# Start frontend
start_frontend() {
    echo -e "${YELLOW}Starting frontend...${NC}"
    cd frontend

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm install
    fi

    # Start in background
    echo -e "${YELLOW}Starting Vite dev server...${NC}"
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
}

# Wait for services to be ready
wait_for_services() {
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"

    # Wait for backend
    echo -n "Waiting for backend API..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e " ${GREEN}ready!${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done

    # Wait for frontend
    echo -n "Waiting for frontend..."
    for i in {1..30}; do
        if curl -s http://localhost:5173 > /dev/null 2>&1; then
            echo -e " ${GREEN}ready!${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
}

# Main execution
main() {
    # Check for Ollama
    if ! check_ollama; then
        echo -e "${RED}Error: Ollama is not running!${NC}"
        echo -e "${YELLOW}Please start Ollama first:${NC}"
        echo "  - macOS: Ollama should be running from the menu bar"
        echo "  - Linux: Run 'ollama serve' in a separate terminal"
        echo ""
        echo "Download Ollama from: https://ollama.ai/download"
        exit 1
    fi

    # Check models
    check_models

    # Start services
    start_backend
    sleep 5
    start_frontend

    # Wait for everything to be ready
    wait_for_services

    echo ""
    echo -e "${GREEN}==================================="
    echo "All services are running!"
    echo "===================================${NC}"
    echo ""
    echo "Frontend: http://localhost:5173"
    echo "Backend API: http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}To stop all services, run:${NC}"
    echo "  ./stop.sh"
    echo ""
}

main
