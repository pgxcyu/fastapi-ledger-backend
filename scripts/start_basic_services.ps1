#!/usr/bin/env pwsh
# 启动基本服务的PowerShell脚本

Write-Host "正在启动基本服务（数据库、Redis和API）..." -ForegroundColor Green

# 使用简化的docker-compose文件启动服务
docker-compose -f docker-compose-basic.yml up -d

# 检查启动状态
Write-Host "\n服务启动状态："
Write-Host "--------------------------------" -ForegroundColor Cyan
docker-compose -f docker-compose-basic.yml ps
Write-Host "--------------------------------" -ForegroundColor Cyan

Write-Host "\n基本服务已启动！" -ForegroundColor Green
Write-Host "- 数据库 (PostgreSQL): http://localhost:5432"
Write-Host "- Redis: http://localhost:6379"
Write-Host "- API服务: http://localhost:9000"
Write-Host "\n如需停止服务，请运行: docker-compose -f docker-compose-basic.yml down" -ForegroundColor Yellow
