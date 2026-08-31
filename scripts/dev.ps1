# Start backend then print frontend command.
Set-Location $PSScriptRoot\..
Start-Process python -ArgumentList "-m","uvicorn","app.main:app","--app-dir","backend","--host","127.0.0.1","--port","8000"
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: npm run dev -> http://localhost:3000"
