$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$backendPort = 8000
$frontendPort = 5173

function Test-Endpoint {
    param([string]$Url)

    try {
        $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

function Test-PortListening {
    param([int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $connection.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($connection)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $script = "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location -LiteralPath '$($WorkingDirectory.Replace("'", "''"))'; $Command"
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encodedCommand) `
        -WorkingDirectory $WorkingDirectory
}

if (-not (Test-Path (Join-Path $backendRoot "app\main.py"))) {
    throw "Backend was not found at $backendRoot."
}
if (-not (Test-Path (Join-Path $frontendRoot "package.json"))) {
    throw "Frontend was not found at $frontendRoot."
}

if (-not (Test-Path $pythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Install Python 3.10 or later and run this script again."
    }
    & $pythonCommand.Source -m venv (Join-Path $projectRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the project virtual environment."
    }
}

$dependencyCheck = "import fastapi, uvicorn, pandas, numpy, multipart, openpyxl, docx, reportlab, PIL"
& $pythonPath -c $dependencyCheck 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend requirements into the project virtual environment..." -ForegroundColor Cyan
    & $pythonPath -m pip install -r (Join-Path $backendRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependency installation failed."
    }
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "npm was not found. Install Node.js 20 or later and restart PowerShell."
}
if (-not (Test-Path (Join-Path $frontendRoot "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $frontendRoot
    try {
        & $npmCommand.Source install
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend dependency installation failed."
        }
    } finally {
        Pop-Location
    }
}

$healthUrl = "http://127.0.0.1:$backendPort/api/health"
if (-not (Test-Endpoint $healthUrl)) {
    if (Test-PortListening $backendPort) {
        throw "Port $backendPort is occupied, but MediEval API health did not respond. Close the other service using port $backendPort, then run .\start.ps1 again."
    }

    $backendCommand = "& '$($pythonPath.Replace("'", "''"))' -m uvicorn app.main:app --host 127.0.0.1 --port $backendPort --reload --reload-dir ."
    Start-ServiceWindow -Title "MediEval Backend" -WorkingDirectory $backendRoot -Command $backendCommand

    $backendReady = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        if (Test-Endpoint $healthUrl) {
            $backendReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $backendReady) {
        throw "The backend did not become ready on port $backendPort. Check the MediEval Backend window for startup errors."
    }
} else {
    Write-Host "MediEval API is already running." -ForegroundColor Green
}

$frontendUrl = "http://127.0.0.1:$frontendPort"
if (-not (Test-Endpoint $frontendUrl)) {
    if (Test-PortListening $frontendPort) {
        throw "Port $frontendPort is occupied, but the MediEval frontend did not respond. Close the other service using port $frontendPort, then run .\start.ps1 again."
    }

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $nodeCommand) {
        throw "node.exe was not found. Install Node.js 20 or later and restart PowerShell."
    }
    $viteEntry = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
    if (-not (Test-Path $viteEntry)) {
        throw "Vite is not installed at $viteEntry. Run npm install in the frontend folder, then retry."
    }
    $frontendCommand = "& '$($nodeCommand.Source.Replace("'", "''"))' '$($viteEntry.Replace("'", "''"))' --host 127.0.0.1 --port $frontendPort --strictPort"
    Start-ServiceWindow -Title "MediEval Frontend" -WorkingDirectory $frontendRoot -Command $frontendCommand

    $frontendReady = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        if ((Test-Endpoint $frontendUrl) -and (Test-Endpoint "$frontendUrl/api/health")) {
            $frontendReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $frontendReady) {
        throw "The frontend or its proxied API did not become ready. Check the MediEval Frontend window for startup errors."
    }
} else {
    Write-Host "MediEval frontend is already running." -ForegroundColor Green
    if (-not (Test-Endpoint "$frontendUrl/api/health")) {
        throw "The frontend is running but cannot reach the API through its Vite proxy. Close the frontend terminal and run .\start.ps1 again so Vite reloads the proxy configuration."
    }
}

Write-Host ""
Write-Host "MediEval AI is ready." -ForegroundColor Green
Write-Host "Application: http://127.0.0.1:$frontendPort"
Write-Host "API health:  $healthUrl"
Write-Host "API docs:    http://127.0.0.1:$backendPort/docs"
Write-Host "Keep both MediEval service windows open while using the app. Close those windows to stop the services."
