# PineOS Referral System - Quick Start (Windows)
# Run with: .\quickstart.ps1

Write-Host "🌲 PineOS Referral System - Quick Start" -ForegroundColor Cyan
Write-Host "========================================"
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Create .env file if it doesn't exist
if (-not (Test-Path "backend/.env")) {
    Write-Host "📝 Creating backend/.env from .env.example..." -ForegroundColor Yellow
    Copy-Item "backend/.env.example" -Destination "backend/.env"
    Write-Host "✓ Created backend/.env" -ForegroundColor Green
} else {
    Write-Host "✓ backend/.env already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 Starting services with Docker Compose..." -ForegroundColor Cyan
Write-Host ""

docker-compose up -d

Write-Host ""
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if backend is healthy
Write-Host "Checking backend health..." -ForegroundColor Yellow
$maxAttempts = 30
$attempts = 0
$backendReady = $false

while (-not $backendReady -and $attempts -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
        }
    } catch {
        Write-Host "Waiting for backend..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $attempts++
    }
}

if ($backendReady) {
    Write-Host "✓ Backend is ready" -ForegroundColor Green
} else {
    Write-Host "⚠️  Backend may still be starting. Check logs with: docker-compose logs backend" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ All services are running!" -ForegroundColor Green
Write-Host ""
Write-Host "📌 Service URLs:" -ForegroundColor Cyan
Write-Host "   - Backend API:  http://localhost:8000"
Write-Host "   - API Docs:     http://localhost:8000/docs"
Write-Host "   - Frontend UI:  http://localhost:5173"
Write-Host "   - PostgreSQL:   localhost:5432"
Write-Host ""
Write-Host "📚 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Visit http://localhost:5173 to see the UI"
Write-Host "   2. Visit http://localhost:8000/docs for API documentation"
Write-Host "   3. Run 'docker-compose logs -f' to view logs"
Write-Host "   4. Run 'docker-compose down' to stop all services"
Write-Host ""
Write-Host "🧪 To run tests:" -ForegroundColor Cyan
Write-Host "   cd backend"
Write-Host "   pip install -r requirements.txt"
Write-Host "   pytest -v"
Write-Host ""
Write-Host "Happy coding! 🎉" -ForegroundColor Green
