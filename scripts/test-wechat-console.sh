#!/bin/bash
# Test WeChat Article Crawler Console

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:11235"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Testing WeChat Console API${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Test 1: Health check
echo -e "${BLUE}[1/6] Testing health endpoint...${NC}"
if curl -sf "${BASE_URL}/health" > /dev/null; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi

# Test 2: List tasks (should be empty initially)
echo -e "${BLUE}[2/6] Testing list tasks...${NC}"
RESPONSE=$(curl -sf "${BASE_URL}/api/tasks")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ List tasks passed${NC}"
    echo "  Response: $RESPONSE"
else
    echo -e "${RED}✗ List tasks failed${NC}"
    exit 1
fi

# Test 3: Create a task
echo -e "${BLUE}[3/6] Testing create task...${NC}"
TASK_DATA='{
  "name": "Test Task",
  "description": "Test task created by test script",
  "wechat_urls": ["https://mp.weixin.qq.com/test"],
  "schedule_type": "once",
  "schedule_config": {},
  "status": "paused"
}'

CREATE_RESPONSE=$(curl -sf -X POST "${BASE_URL}/api/tasks" \
  -H "Content-Type: application/json" \
  -d "$TASK_DATA")

if [ $? -eq 0 ]; then
    TASK_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
    echo -e "${GREEN}✓ Create task passed (ID: ${TASK_ID})${NC}"
else
    echo -e "${RED}✗ Create task failed${NC}"
    exit 1
fi

# Test 4: Get task details
echo -e "${BLUE}[4/6] Testing get task...${NC}"
if curl -sf "${BASE_URL}/api/tasks/${TASK_ID}" > /dev/null; then
    echo -e "${GREEN}✓ Get task passed${NC}"
else
    echo -e "${RED}✗ Get task failed${NC}"
    exit 1
fi

# Test 5: Update task status
echo -e "${BLUE}[5/6] Testing update task status...${NC}"
if curl -sf -X PATCH "${BASE_URL}/api/tasks/${TASK_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}' > /dev/null; then
    echo -e "${GREEN}✓ Update status passed${NC}"
else
    echo -e "${RED}✗ Update status failed${NC}"
    exit 1
fi

# Test 6: Delete task
echo -e "${BLUE}[6/6] Testing delete task...${NC}"
if curl -sf -X DELETE "${BASE_URL}/api/tasks/${TASK_ID}" > /dev/null; then
    echo -e "${GREEN}✓ Delete task passed${NC}"
else
    echo -e "${RED}✗ Delete task failed${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  • View API docs: ${BLUE}${BASE_URL}/docs${NC}"
echo -e "  • Check logs:    ${BLUE}docker compose logs -f${NC}"
echo -e "  • Build frontend: ${BLUE}cd frontend && npm install && npm run build${NC}"
