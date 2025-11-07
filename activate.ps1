# PowerShell script to activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now install dependencies with: pip install -r requirements.txt" -ForegroundColor Yellow
Write-Host ""


