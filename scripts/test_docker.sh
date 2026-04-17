#!/bin/bash
# ============================================================
# Test Docker Image Script
# ============================================================

set -e

echo "🧪 Testing Chatbot Xanh SM Docker Image..."
echo "============================================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if image exists
if ! docker images xanhsm-agent:production | grep -q xanhsm-agent; then
    echo -e "${RED}❌ Image not found. Build it first:${NC}"
    echo "   ./scripts/build_docker.sh"
    exit 1
fi

# Test 1: Image size
echo -e "${YELLOW}Test 1: Image size${NC}"
SIZE_MB=$(docker images xanhsm-agent:production --format "{{.Size}}" | sed 's/MB//' | sed 's/GB/*1024/' | bc 2>/dev/null || echo "unknown")
echo "  Image size: $(docker images xanhsm-agent:production --format '{{.Size}}')"
if [ "$SIZE_MB" != "unknown" ] && [ $(echo "$SIZE_MB < 1000" | bc) -eq 1 ]; then
    echo -e "  ${GREEN}✅ Size OK (< 1GB)${NC}"
else
    echo -e "  ${YELLOW}⚠️  Size might be large${NC}"
fi

# Test 2: Non-root user
echo ""
echo -e "${YELLOW}Test 2: Non-root user${NC}"
USER=$(docker run --rm xanhsm-agent:production whoami)
if [ "$USER" = "appuser" ]; then
    echo -e "  ${GREEN}✅ Running as non-root user: $USER${NC}"
else
    echo -e "  ${RED}❌ Running as: $USER (should be appuser)${NC}"
fi

# Test 3: Health check defined
echo ""
echo -e "${YELLOW}Test 3: Health check${NC}"
if docker inspect xanhsm-agent:production | grep -q "Healthcheck"; then
    echo -e "  ${GREEN}✅ Health check defined${NC}"
else
    echo -e "  ${RED}❌ No health check defined${NC}"
fi

# Test 4: Start container
echo ""
echo -e "${YELLOW}Test 4: Container startup${NC}"
echo "  Starting container..."

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "  ${YELLOW}⚠️  .env not found, using minimal config${NC}"
    docker run -d --name xanhsm-test \
        -p 8001:8000 \
        -e ENVIRONMENT=development \
        -e OPENAI_API_KEY=test \
        xanhsm-agent:production
else
    docker run -d --name xanhsm-test \
        -p 8001:8000 \
        --env-file .env \
        xanhsm-agent:production
fi

# Wait for startup
echo "  Waiting for startup (30s)..."
sleep 30

# Test 5: Health endpoint
echo ""
echo -e "${YELLOW}Test 5: Health endpoint${NC}"
if curl -f -s http://localhost:8001/health > /dev/null; then
    HEALTH=$(curl -s http://localhost:8001/health)
    echo -e "  ${GREEN}✅ Health check passed${NC}"
    echo "  Response: $HEALTH"
else
    echo -e "  ${RED}❌ Health check failed${NC}"
    echo "  Container logs:"
    docker logs xanhsm-test --tail 20
fi

# Test 6: Root endpoint
echo ""
echo -e "${YELLOW}Test 6: Root endpoint${NC}"
if curl -f -s http://localhost:8001/ > /dev/null; then
    ROOT=$(curl -s http://localhost:8001/)
    echo -e "  ${GREEN}✅ Root endpoint OK${NC}"
    echo "  Response: $ROOT"
else
    echo -e "  ${RED}❌ Root endpoint failed${NC}"
fi

# Cleanup
echo ""
echo -e "${YELLOW}Cleaning up...${NC}"
docker stop xanhsm-test > /dev/null 2>&1
docker rm xanhsm-test > /dev/null 2>&1
echo -e "${GREEN}✅ Cleanup done${NC}"

# Summary
echo ""
echo "============================================================"
echo -e "${GREEN}✅ Docker image tests completed!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Run full stack: docker compose up"
echo "2. Test with real data: mount knowledge base volume"
echo "3. Deploy to cloud: Railway or Render"
