$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $repoRoot "backend"
$frontend = Join-Path $repoRoot "frontend"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$frontend'; npm run dev"
)
