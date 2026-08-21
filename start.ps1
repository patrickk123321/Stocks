# Starts both the backend (FastAPI) and frontend (Next.js) dev servers.
# Run from anywhere: powershell -File start.ps1

$root = $PSScriptRoot

$env:PYTHONPATH = "."
Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" `
    -WorkingDirectory "$root\backend"

Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory "$root\frontend"

Write-Output "Backend starting on http://localhost:8000, frontend on http://localhost:3000"
