#!/bin/bash
# Start WeChat Article Crawler Console
# This script sets up and starts the WeChat console services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Crawl4AI - WeChat Article Crawler Console Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found. Creating from template...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file${NC}"
        echo -e "${YELLOW}⚠ WARNING: Please edit .env and change POSTGRES_PASSWORD before production use!${NC}"
        echo ""
    else
        echo -e "${RED}❌ Error: .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Check if .llm.env exists
if [ ! -f deploy/docker/.llm.env ]; then
    echo -e "${YELLOW}⚠ LLM configuration not found${NC}"
    if [ -f deploy/docker/.llm.env.example ]; then
        cp deploy/docker/.llm.env.example deploy/docker/.llm.env
        echo -e "${GREEN}✓ Created .llm.env file${NC}"
        echo -e "${YELLOW}  Note: Add your LLM API keys to deploy/docker/.llm.env if needed${NC}"
    fi
else
    echo -e "${GREEN}✓ LLM configuration exists${NC}"
fi

echo ""
echo -e "${BLUE}Starting services...${NC}"
echo ""

# Start services
docker compose up -d

# Wait for services to be healthy
echo ""
echo -e "${BLUE}Waiting for services to be ready...${NC}"
sleep 5

# Check backend health
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:11235/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Backend failed to start${NC}"
        echo "Check logs with: docker compose logs crawl4ai"
        exit 1
    fi
    echo -e "${YELLOW}  Waiting... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

# Check database health
if docker compose exec -T postgres pg_isready -U crawl4ai > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database is ready${NC}"
else
    echo -e "${RED}❌ Database is not ready${NC}"
    echo "Check logs with: docker compose logs postgres"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 WeChat Console is ready!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}📡 Backend API:${NC}        http://localhost:11235"
echo -e "${GREEN}📚 API Documentation:${NC}  http://localhost:11235/docs"
echo -e "${GREEN}🏥 Health Check:${NC}       http://localhost:11235/health"
echo ""
echo -e "${YELLOW}Frontend:${NC} To enable the web UI, run:"
echo -e "  ${BLUE}cd frontend && npm install && npm run build${NC}"
echo -e "  Then uncomment frontend service in docker-compose.yml and run:"
echo -e "  ${BLUE}docker compose up -d${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  View logs:        ${BLUE}docker compose logs -f${NC}"
echo -e "  Stop services:    ${BLUE}docker compose down${NC}"
echo -e "  Restart services: ${BLUE}docker compose restart${NC}"
echo -e "  Check status:     ${BLUE}docker compose ps${NC}"
echo ""
echo -e "${YELLOW}Quick test:${NC}"
echo -e "  ${BLUE}curl http://localhost:11235/api/tasks${NC}"
echo ""
echo -e "${GREEN}Happy crawling! 🕷️${NC}"
