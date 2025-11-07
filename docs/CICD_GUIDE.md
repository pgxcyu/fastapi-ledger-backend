# CI 配置指南

本文档详细介绍了 fastapi-ledger 项目的持续集成(CI)配置流程。

## CI 流程概述

我们使用 GitHub Actions 实现了完整的持续集成流程，包括：

1. **持续集成 (CI)**：
   - 代码提交或 PR 时自动运行测试
   - 测试数据库和 Redis 服务自动化配置
   - 数据库迁移自动化执行
   - 测试覆盖率报告生成
   - 主分支代码自动构建 Docker 镜像（不推送）

## 配置详解

### GitHub Actions 工作流配置

工作流文件位于 `.github/workflows/ci.yml`，主要包含以下几个作业：

#### 1. `test` 作业
- 运行环境：Ubuntu latest
- 服务：PostgreSQL 15 和 Redis 7
- 步骤：
  - 检出代码
  - 设置 Python 环境
  - 安装依赖
  - 创建数据库表
  - 执行数据库迁移
  - 运行测试并生成覆盖率报告
  - 上传覆盖率报告

具体实现中，通过正确设置PYTHONPATH环境变量并直接在命令行中执行Python代码来初始化数据库表，确保Python可以找到app模块并避免模块导入错误

#### 2. `build` 作业
- 依赖：test 作业成功
- 触发条件：推送到主分支时
- 步骤：
  - 设置 Docker Buildx
  - 构建 Docker 镜像（仅本地构建，不推送）
  - 验证镜像构建成功

## 使用指南

### 基本使用

1. **提交代码**：
   - 推送到 main/master 分支时，会自动运行测试并构建镜像
   - 创建 Pull Request 时，会自动运行测试验证

## 常见问题排查

1. **测试失败**：
   - 检查数据库连接配置是否正确
   - 确认依赖项是否都已正确安装
   - 查看 GitHub Actions 日志了解具体错误

2. **镜像构建失败**：
   - 检查 Dockerfile 是否有语法错误
   - 确认项目依赖是否都在 requirements.txt 中

3. **数据库迁移错误**：
   - **问题**: 在GitHub Actions中出现`ModuleNotFoundError: No module named 'app'`错误
  **解决方法**: 正确设置`PYTHONPATH=$PWD`环境变量，确保Python可以找到app模块，并通过命令行直接执行初始化代码

4. **数据库驱动错误**：
   - 问题：运行测试时出现 `ModuleNotFoundError: No module named 'psycopg2'`
   - 解决方法：在 CI 配置中将环境变量 `DATABASE_URL` 中的数据库驱动从 `psycopg2` 改为 `psycopg`，以匹配项目使用的 `psycopg[binary]` 依赖

## 最佳实践

1. **分支策略**：
   - 使用 feature 分支进行开发
   - 通过 Pull Request 合并到 main/master 分支

2. **安全考虑**：
   - 所有敏感信息通过 GitHub Secrets 管理（如需）
   - 定期更新依赖项以修复安全漏洞

## 未来扩展

当你准备好部署环境后，可以按以下步骤添加 CD 功能：

1. 修改 `.github/workflows/ci.yml`，添加部署作业
2. 配置必要的部署凭证（SSH 密钥、云服务凭证等）
3. 实现具体的部署逻辑（Docker 镜像推送、服务更新等）

---

请根据实际项目需求调整 CI 配置，本指南提供了基本框架和示例，可根据具体情况进行扩展和定制。