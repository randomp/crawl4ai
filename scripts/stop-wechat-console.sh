#!/bin/bash
# Stop WeChat Article Crawler Console

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Stopping WeChat Console services...${NC}"
echo ""

# Stop services
docker compose down

echo ""
echo -e "${GREEN}✓ Services stopped${NC}"
echo ""
echo -e "To remove all data (including database):"
echo -e "  ${BLUE}docker compose down -v${NC}"
echo ""
echo -e "To start again:"
echo -e "  ${BLUE}./scripts/start-wechat-console.sh${NC}"
