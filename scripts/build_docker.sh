#!/bin/bash
# ============================================================
# Build Docker Image Script
# ============================================================

set -e  # Exit on error

echo "🐳 Building Chatbot Xanh SM Docker Image..."
echo "============================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Build image
echo -e "${YELLOW}📦 Building image...${NC}"
docker build -f backend_ai/Dockerfile -t xanhsm-agent:production backend_ai

# Check image size
echo ""
echo -e "${YELLOW}📊 Image size:${NC}"
docker images xanhsm-agent:production --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Get size in MB
SIZE=$(docker images xanhsm-agent:production --format "{{.Size}}")
echo ""
echo -e "${GREEN}✅ Build completed!${NC}"
echo -e "Image size: ${GREEN}${SIZE}${NC}"

# Recommendations
echo ""
echo "============================================================"
echo "📝 Next steps:"
echo "============================================================"
echo "1. Test locally:"
echo "   docker run -p 8000:8000 --env-file .env \\"
echo "     -v \$(pwd)/data_pipeline/db_setup:/app/data_pipeline/db_setup \\"
echo "     xanhsm-agent:production"
echo ""
echo "2. Test health check:"
echo "   curl http://localhost:8000/health"
echo ""
echo "3. Run with docker-compose:"
echo "   docker compose up"
echo ""
echo "4. Tag for registry (optional):"
echo "   docker tag xanhsm-agent:production your-registry/xanhsm-agent:v1.0.0"
echo "============================================================"
