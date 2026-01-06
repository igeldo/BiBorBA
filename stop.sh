#!/bin/bash

set -e

echo "==================================="
echo "LangGraph RAG - Shutdown Script"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Stop backend containers
echo -e "${YELLOW}Stopping backend services...${NC}"
cd langgraph-rag
docker-compose down
cd ..
echo -e "${GREEN}✓ Backend services stopped${NC}"

# Stop frontend (kill all node processes running vite)
echo -e "${YELLOW}Stopping frontend...${NC}"
pkill -f "vite" 2>/dev/null || echo -e "${YELLOW}  No Vite processes found${NC}"
echo -e "${GREEN}✓ Frontend stopped${NC}"

echo ""
echo -e "${GREEN}==================================="
echo "All services have been stopped!"
echo "===================================${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} Ollama is still running (if you started it separately)"
echo "  - To stop Ollama Desktop: Quit from menu bar"
echo "  - To stop Docker Ollama: cd langgraph-rag && docker-compose --profile ollama down"
echo ""
