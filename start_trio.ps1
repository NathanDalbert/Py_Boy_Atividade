# Script PowerShell para iniciar os três componentes em janelas separadas.
# Execute:  powershell -ExecutionPolicy Bypass -File .\start_trio.ps1

if (-not $env:VENV_PATH) { $env:VENV_PATH = "$PSScriptRoot\.venv" }
$activate = Join-Path $env:VENV_PATH 'Scripts\Activate.ps1'
if (Test-Path $activate) {
	Write-Host "VENV detectada: $activate" -ForegroundColor Yellow
	$prefix = "& '$activate';"
} else {
	Write-Host "VENV não encontrada em $activate (seguindo sem ativar)" -ForegroundColor DarkYellow
	$prefix = ""
}

Write-Host "Iniciando Game Loop" -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit','-Command',"$prefix python src/game_loop.py"
Start-Sleep -Milliseconds 500

Write-Host "Iniciando Controller" -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit','-Command',"$prefix python src/controller.py"
Start-Sleep -Milliseconds 500

Write-Host "Iniciando Analytics" -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit','-Command',"$prefix python src/analytics.py"

Write-Host "Todos iniciados. Feche janelas para encerrar cada processo." -ForegroundColor Green
