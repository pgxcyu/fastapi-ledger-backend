# PowerShell 脚本用于分阶段安装依赖
# 解决Windows环境下一次性安装失败的问题

Write-Host "=== 开始安装 FastAPI Ledger 项目依赖 ==="
Write-Host ""

# 步骤1: 升级pip
Write-Host "[步骤1] 升级pip..."
pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip升级失败，请手动检查环境"
    exit 1
}
Write-Host "pip升级完成"
Write-Host ""

# 步骤2: 安装核心FastAPI依赖
Write-Host "[步骤2] 安装核心FastAPI依赖..."
pip install --prefer-binary fastapi>=0.110.0,<0.120.0 uvicorn[standard]>=0.29.0,<0.31.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "核心FastAPI依赖安装失败"
    exit 1
}
Write-Host "核心FastAPI依赖安装完成"
Write-Host ""

# 步骤3: 安装ORM和数据库依赖
Write-Host "[步骤3] 安装ORM和数据库依赖..."
pip install --prefer-binary SQLAlchemy>=2.0.30,<2.1.0 redis>=5.0.0,<6.0.0 alembic>=1.13.0,<1.14.0 psycopg[binary]>=3.2.0,<3.3.0 aiosqlite>=0.19.0,<0.21.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "ORM和数据库依赖安装失败"
    exit 1
}
Write-Host "ORM和数据库依赖安装完成"
Write-Host ""

# 步骤4: 安装安全相关依赖
Write-Host "[步骤4] 安装安全相关依赖..."
pip install --prefer-binary passlib[bcrypt]==1.7.4 bcrypt==4.0.1 python-jose[cryptography]>=3.3.0,<4.0.0 fastapi-limiter>=0.1.6,<0.2.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "安全相关依赖安装失败"
    exit 1
}
Write-Host "安全相关依赖安装完成"
Write-Host ""

# 步骤5: 安装任务队列和调度依赖
Write-Host "[步骤5] 安装任务队列和调度依赖..."
pip install --prefer-binary celery>=5.5.0,<6.0.0 flower>=1.2.0,<1.3.0 eventlet>=0.36.0,<0.37.0 APScheduler>=3.10.0,<3.11.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "任务队列和调度依赖安装失败"
    exit 1
}
Write-Host "任务队列和调度依赖安装完成"
Write-Host ""

# 步骤6: 安装数据处理依赖 (使用--only-binary避免编译)
Write-Host "[步骤6] 安装数据处理依赖..."
pip install --only-binary=numpy,pandas --prefer-binary numpy>=2.3.0,<2.4.0 pandas>=2.3.0,<2.4.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "数据处理依赖安装失败"
    exit 1
}
Write-Host "数据处理依赖安装完成"
Write-Host ""

# 步骤7: 安装HTTP和数据交互依赖
Write-Host "[步骤7] 安装HTTP和数据交互依赖..."
pip install --prefer-binary python-multipart>=0.0.16,<0.0.21 requests>=2.32.0,<3.0.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "HTTP和数据交互依赖安装失败"
    exit 1
}
Write-Host "HTTP和数据交互依赖安装完成"
Write-Host ""

# 步骤8: 安装Pydantic相关依赖
Write-Host "[步骤8] 安装Pydantic相关依赖..."
pip install --only-binary=pydantic,pydantic-core,pydantic-settings --prefer-binary pydantic>=2.9.1 pydantic_settings>=2.4.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pydantic相关依赖安装失败"
    exit 1
}
Write-Host "Pydantic相关依赖安装完成"
Write-Host ""

# 步骤9: 安装视频处理库
Write-Host "[步骤9] 安装视频处理库..."
pip install --prefer-binary opencv-python-headless>=4.10.0,<4.11.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "视频处理库安装失败"
    exit 1
}
Write-Host "视频处理库安装完成"
Write-Host ""

# 步骤10: 安装环境变量配置和日志依赖
Write-Host "[步骤10] 安装环境变量配置和日志依赖..."
pip install --prefer-binary python-dotenv>=1.0.0,<2.0.0 loguru>=0.7.0,<0.8.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "环境变量配置和日志依赖安装失败"
    exit 1
}
Write-Host "环境变量配置和日志依赖安装完成"
Write-Host ""

# 步骤11: 安装监控依赖
Write-Host "[步骤11] 安装监控依赖..."
pip install --prefer-binary prometheus-fastapi-instrumentator>=7.0.0,<8.0.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "监控依赖安装失败"
    exit 1
}
Write-Host "监控依赖安装完成"
Write-Host ""

# 步骤12: 安装测试相关依赖（可选）
Write-Host "[步骤12] 安装测试相关依赖..."
pip install --prefer-binary pytest>=8.0.0,<9.0.0 pytest-cov>=5.0.0,<6.0.0 pytest-asyncio>=0.23.0,<0.25.0 httpx>=0.27.0,<0.28.0 tqdm>=4.66.0,<5.0.0
if ($LASTEXITCODE -ne 0) {
    Write-Host "测试相关依赖安装失败，但不影响项目运行"
}
Write-Host "测试相关依赖安装完成"
Write-Host ""

Write-Host "=== 所有依赖安装完成！==="
Write-Host "提示：如需运行项目，请确保已配置正确的环境变量和数据库连接"
Write-Host "推荐使用以下命令启动项目：uvicorn app.main:app --reload"