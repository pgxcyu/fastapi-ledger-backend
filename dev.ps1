# dev.ps1 - Create/activate virtual environment, install dependencies and start service (PowerShell)
param(
  [string]$HostAddr = "0.0.0.0",
  [int]$Port = 9000,
  [string]$App = "app.main:app",
  [switch]$Clean # Optional: Clean old dependencies before reinstallation
)

$ErrorActionPreference = "Stop"

# 1) 选择 Python 可执行文件
$py = "python"
try { & $py --version | Out-Null } catch {
  Write-Host "Python not found. Please ensure it's installed and added to PATH." -ForegroundColor Red
  exit 1
}

# 2) 创建 venv（若不存在）
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Host "Creating virtual environment .venv ..." -ForegroundColor Cyan
  & $py -m venv .venv
}

# 3) 激活 venv
Write-Host "Activating virtual environment ..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"

# 4) 升级安装工具
python -m pip install -U pip setuptools wheel

# 5) 安装依赖
if ($Clean) {
  Write-Host "Cleaning old dependencies and reinstalling ..." -ForegroundColor Yellow
  pip freeze | Out-File -Encoding ascii ._old_freeze.txt
  if (Test-Path ._old_freeze.txt) {
    pip uninstall -y -r ._old_freeze.txt
    Remove-Item ._old_freeze.txt -Force
  }
}
if (Test-Path ".\requirements.txt") {
  Write-Host "Installing requirements.txt ..." -ForegroundColor Cyan
  pip install -r requirements.txt
} else {
  Write-Host "requirements.txt not found, installing minimal dependencies ..." -ForegroundColor Yellow
  pip install fastapi uvicorn[standard]
}

# 6) 启动 Uvicorn 开发服务器
Write-Host "Starting Uvicorn: http://${HostAddr}:${Port}/docs" -ForegroundColor Green
# Add --reload-exclude parameters to exclude virtual environment and other directories
# Use single quotes to avoid PowerShell parsing issues
uvicorn $App --host $HostAddr --port $Port --reload --reload-exclude '.venv' --reload-exclude '__pycache__' --reload-exclude '*.pyc' --reload-exclude '*.pyo'
