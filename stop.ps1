# LangGraph RAG - Windows Shutdown Script
# Usage: .\stop.ps1 [-ollama] [-tools]
#   -ollama  : Also stop Ollama Docker container
#   -tools   : Also stop tools (pgAdmin)

param(
    [switch]$ollama,
    [switch]$tools,
    [switch]$all
)

$ErrorActionPreference = "Stop"

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "LangGraph RAG - Shutdown Script" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

try {
    # Stop frontend (kill all node processes running vite)
    Write-Host "Stopping frontend..." -ForegroundColor Yellow
    try {
        $viteProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*vite*" -or $_.Path -like "*frontend*" }
        if ($viteProcesses) {
            $viteProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
            Write-Host "Frontend stopped" -ForegroundColor Green
        }
        else {
            Write-Host "No Vite processes found" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "No Vite processes found" -ForegroundColor Yellow
    }

    # Stop backend containers
    Write-Host "Stopping backend services..." -ForegroundColor Yellow
    Push-Location langgraph-rag

    # Build docker-compose command with profiles if needed
    if ($all -or ($ollama -and $tools)) {
        & docker-compose --profile ollama --profile tools down
        Write-Host "All services stopped (including Ollama and tools)" -ForegroundColor Green
    }
    elseif ($ollama) {
        & docker-compose --profile ollama down
        Write-Host "Backend and Ollama stopped" -ForegroundColor Green
    }
    elseif ($tools) {
        & docker-compose --profile tools down
        Write-Host "Backend and tools stopped" -ForegroundColor Green
    }
    else {
        docker-compose down
        Write-Host "Backend services stopped" -ForegroundColor Green
    }

    Pop-Location

    Write-Host ""
    Write-Host "===================================" -ForegroundColor Green
    Write-Host "All services have been stopped!" -ForegroundColor Green
    Write-Host "===================================" -ForegroundColor Green
    Write-Host ""

    if (-not $ollama -and -not $all) {
        Write-Host "Note: " -ForegroundColor Yellow -NoNewline
        Write-Host "If you used -ollama to start, also use -ollama to stop:"
        Write-Host "  .\stop.ps1 -ollama"
        Write-Host ""
    }
}
catch {
    Write-Host "Error occurred: $_" -ForegroundColor Red
    Write-Host "Some services may still be running. Check manually if needed." -ForegroundColor Yellow
    exit 1
}