# ============================================================
# Build Docker Image Script (PowerShell)
# ============================================================

Write-Host "🐳 Building Chatbot Xanh SM Docker Image..." -ForegroundColor Cyan
Write-Host "============================================================"

# Build image
Write-Host "📦 Building image..." -ForegroundColor Yellow
docker build -f backend_ai/Dockerfile -t xanhsm-agent:production backend_ai

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Check image size
Write-Host ""
Write-Host "📊 Image size:" -ForegroundColor Yellow
docker images xanhsm-agent:production --format "table {{.Repository}}`t{{.Tag}}`t{{.Size}}"

Write-Host ""
Write-Host "✅ Build completed!" -ForegroundColor Green

# Recommendations
Write-Host ""
Write-Host "============================================================"
Write-Host "📝 Next steps:"
Write-Host "============================================================"
Write-Host "1. Test locally:"
Write-Host "   docker run -p 8000:8000 --env-file .env -v `${PWD}/data_pipeline/db_setup:/app/data_pipeline/db_setup xanhsm-agent:production"
Write-Host ""
Write-Host "2. Test health check:"
Write-Host "   curl http://localhost:8000/health"
Write-Host ""
Write-Host "3. Run with docker-compose:"
Write-Host "   docker compose up"
Write-Host ""
Write-Host "4. Tag for registry (optional):"
Write-Host "   docker tag xanhsm-agent:production your-registry/xanhsm-agent:v1.0.0"
Write-Host "============================================================"



