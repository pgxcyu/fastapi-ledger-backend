# dev.ps1 — 一键创建/激活虚拟环境、安装依赖并启动服务（PowerShell）
param(
  [string]$HostAddr = "0.0.0.0",
  [int]$Port = 9000,
  [string]$App = "app.main:app",
  [switch]$Clean # 可选：清理旧依赖后重装
)

$ErrorActionPreference = "Stop"

# 1) 选择 Python 可执行文件
$py = "python"
try { & $py --version | Out-Null } catch {
  Write-Host "找不到 python，请确认已安装并加入 PATH" -ForegroundColor Red
  exit 1
}

# 2) 创建 venv（若不存在）
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Host "创建虚拟环境 .venv ..." -ForegroundColor Cyan
  & $py -m venv .venv
}

# 3) 激活 venv
Write-Host "激活虚拟环境 ..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"

# 4) 升级安装工具
python -m pip install -U pip setuptools wheel

# 5) 安装依赖
if ($Clean) {
  Write-Host "清理旧依赖并重装 ..." -ForegroundColor Yellow
  pip freeze | Out-File -Encoding ascii ._old_freeze.txt
  if (Test-Path ._old_freeze.txt) {
    pip uninstall -y -r ._old_freeze.txt
    Remove-Item ._old_freeze.txt -Force
  }
}
if (Test-Path ".\requirements.txt") {
  Write-Host "安装 requirements.txt ..." -ForegroundColor Cyan
  pip install -r requirements.txt
} else {
  Write-Host "未找到 requirements.txt，安装最小依赖 ..." -ForegroundColor Yellow
  pip install fastapi uvicorn[standard]
}

# 6) 启动 Uvicorn 开发服务器
Write-Host "启动 Uvicorn: http://${HostAddr}:${Port}/docs" -ForegroundColor Green
uvicorn $App --host $HostAddr --port $Port --reload
