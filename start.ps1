# LangGraph RAG - Windows Startup Script
# Usage: .\start.ps1 [-ollama] [-tools]
#   -ollama  : Start Ollama in Docker container (with GPU support)
#   -tools   : Start additional tools (pgAdmin)

param(
    [switch]$ollama,
    [switch]$tools
)

$ErrorActionPreference = "Stop"

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "LangGraph RAG - Startup Script" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

if ($ollama) {
    Write-Host "Mode: Ollama in Docker container" -ForegroundColor Magenta
}
if ($tools) {
    Write-Host "Mode: Additional tools enabled (pgAdmin)" -ForegroundColor Magenta
}
Write-Host ""

# Check if Ollama is running
function Test-OllamaRunning {
    Write-Host "Checking for Ollama instance..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "Ollama is running" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "Ollama is not running" -ForegroundColor Red
        return $false
    }
    return $false
}

# Check required models
function Test-OllamaModels {
    Write-Host "Checking required Ollama models..." -ForegroundColor Yellow

    $requiredModels = @("nomic-embed-text", "llama3.1:8b")
    $missingModels = @()

    # Use API instead of CLI to avoid Win32 errors
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -UseBasicParsing
        $models = ($response.Content | ConvertFrom-Json).models
        $installedModelNames = $models | ForEach-Object { $_.name }
    }
    catch {
        Write-Host "Could not retrieve model list from Ollama API" -ForegroundColor Red
        return
    }

    foreach ($model in $requiredModels) {
        $found = $false
        foreach ($installed in $installedModelNames) {
            if ($installed -like "$model*") {
                $found = $true
                break
            }
        }
        if ($found) {
            Write-Host "Model $model is available" -ForegroundColor Green
        }
        else {
            Write-Host "Model $model is missing" -ForegroundColor Red
            $missingModels += $model
        }
    }

    if ($missingModels.Count -gt 0) {
        Write-Host "Installing missing models..." -ForegroundColor Yellow
        foreach ($model in $missingModels) {
            Write-Host "Pulling $model (this may take a while)..." -ForegroundColor Yellow
            # Use API to pull models
            try {
                $body = @{ name = $model } | ConvertTo-Json
                Invoke-WebRequest -Uri "http://localhost:11434/api/pull" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 600
                Write-Host "Model $model pulled successfully" -ForegroundColor Green
            }
            catch {
                Write-Host "Failed to pull $model - please pull manually: ollama pull $model" -ForegroundColor Red
            }
        }
    }
}

# Start backend services
function Start-Backend {
    param(
        [bool]$useOllamaDocker = $false,
        [bool]$useTools = $false
    )

    Write-Host "Starting backend services..." -ForegroundColor Yellow
    Push-Location langgraph-rag

    # Build the docker-compose command with profiles
    $profiles = @()
    if ($useOllamaDocker) {
        $profiles += "--profile"
        $profiles += "ollama"
        Write-Host "  - Including Ollama Docker container (GPU)" -ForegroundColor Yellow
    }
    if ($useTools) {
        $profiles += "--profile"
        $profiles += "tools"
        Write-Host "  - Including tools (pgAdmin)" -ForegroundColor Yellow
    }

    $services = @("db", "chroma", "app")
    if ($useOllamaDocker) {
        $services += "ollama"
    }
    if ($useTools) {
        $services += "pgadmin"
    }

    # Execute docker-compose with profiles
    if ($profiles.Count -gt 0) {
        & docker-compose $profiles up -d $services
    }
    else {
        docker-compose up -d $services
    }

    Pop-Location
    Write-Host "Backend services started" -ForegroundColor Green

    # If Ollama Docker was started, wait for it to be ready
    if ($useOllamaDocker) {
        Write-Host "Waiting for Ollama container to be ready..." -NoNewline
        for ($i = 1; $i -le 30; $i++) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2 -UseBasicParsing
                if ($response.StatusCode -eq 200) {
                    Write-Host " ready!" -ForegroundColor Green
                    break
                }
            }
            catch {
                Write-Host "." -NoNewline
                Start-Sleep -Seconds 2
            }
        }
    }
}

# Start frontend
function Start-Frontend {
    Write-Host "Starting frontend..." -ForegroundColor Yellow
    Push-Location frontend

    # Check if node_modules exists
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        & npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to install dependencies" -ForegroundColor Red
            Pop-Location
            return
        }
    }

    # Start in background using cmd to avoid Win32 errors
    Write-Host "Starting Vite dev server..." -ForegroundColor Yellow
    Start-Process cmd -ArgumentList "/c", "npm run dev" -WindowStyle Minimized
    Pop-Location
    Write-Host "Frontend started" -ForegroundColor Green
}

# Wait for services
function Wait-ForServices {
    Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow

    # Wait for backend
    Write-Host "Waiting for backend API..." -NoNewline
    $backendReady = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host " ready!" -ForegroundColor Green
                $backendReady = $true
                break
            }
        }
        catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 2
        }
    }
    if (-not $backendReady) {
        Write-Host " timeout!" -ForegroundColor Red
    }

    # Wait for frontend
    Write-Host "Waiting for frontend..." -NoNewline
    $frontendReady = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host " ready!" -ForegroundColor Green
                $frontendReady = $true
                break
            }
        }
        catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 2
        }
    }
    if (-not $frontendReady) {
        Write-Host " timeout!" -ForegroundColor Red
    }
}

# Main execution
try {
    # If using Ollama in Docker, start it first before checking
    if ($ollama) {
        Write-Host "Starting Ollama in Docker container..." -ForegroundColor Yellow
        Push-Location langgraph-rag
        & docker-compose --profile ollama up -d ollama
        Pop-Location

        # Wait for Ollama to be ready
        Write-Host "Waiting for Ollama container..." -NoNewline
        $ollamaReady = $false
        for ($i = 1; $i -le 60; $i++) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2 -UseBasicParsing
                if ($response.StatusCode -eq 200) {
                    Write-Host " ready!" -ForegroundColor Green
                    $ollamaReady = $true
                    break
                }
            }
            catch {
                Write-Host "." -NoNewline
                Start-Sleep -Seconds 2
            }
        }
        if (-not $ollamaReady) {
            Write-Host " timeout!" -ForegroundColor Red
            Write-Host "Ollama container did not start in time" -ForegroundColor Red
            exit 1
        }
    }

    # Check for Ollama
    if (-not (Test-OllamaRunning)) {
        Write-Host "Error: Ollama is not running!" -ForegroundColor Red
        Write-Host "Please start Ollama:" -ForegroundColor Yellow
        Write-Host "  - Ollama Desktop: Start the application" -ForegroundColor Yellow
        Write-Host "  - Docker Ollama: Run this script with -ollama parameter" -ForegroundColor Yellow
        Write-Host "    Example: .\start.ps1 -ollama" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Download Ollama from: https://ollama.ai/download" -ForegroundColor Yellow
        exit 1
    }

    # Check models
    Test-OllamaModels

    # Start services (without Ollama if already started above)
    Start-Backend -useOllamaDocker $false -useTools $tools
    Start-Sleep -Seconds 5
    Start-Frontend

    # Wait for everything to be ready
    Wait-ForServices

    Write-Host ""
    Write-Host "===================================" -ForegroundColor Green
    Write-Host "All services are running!" -ForegroundColor Green
    Write-Host "===================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Frontend: http://localhost:5173"
    Write-Host "Backend API: http://localhost:8000"
    Write-Host "API Docs: http://localhost:8000/docs"
    if ($ollama) {
        Write-Host "Ollama (Docker): http://localhost:11434"
    }
    if ($tools) {
        Write-Host "pgAdmin: http://localhost:5050"
        Write-Host "  Email: admin@langgraph.com"
        Write-Host "  Password: admin"
    }
    Write-Host ""
    Write-Host "To stop all services, run:" -ForegroundColor Yellow
    Write-Host "  .\stop.ps1"
    Write-Host ""
}
catch {
    Write-Host "Error occurred: $_" -ForegroundColor Red
    exit 1
}