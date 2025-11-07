# 在Windows上模拟GitHub Actions环境

## 为什么需要模拟GitHub Actions？
在本地模拟GitHub Actions环境可以：
- 快速测试CI/CD配置，避免频繁提交到GitHub
- 在推送前发现并修复CI环境中的问题
- 节省时间，特别是对于需要多次调试的情况

## 完整模拟方案：使用`act`工具

### 前提条件
✅ **Docker已安装** (您当前版本: Docker 28.5.1)
✅ **PowerShell 7+** (您当前版本: PowerShell 7.5.4)

### 1. 安装`act`工具

在PowerShell中执行以下命令安装`act`：

```powershell
# 使用Scoop包管理器安装（推荐）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
scoop install act

# 或者使用Chocolatey安装
# Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
# choco install act-cli -y
```

### 2. 配置`act`工具

```powershell
# 初始化act配置
act --help

# 查看可用的运行器镜像
act --list

# 为我们的CI工作流选择适当的镜像（ubuntu-latest通常对应于medium）
act -P ubuntu-latest=ghcr.io/nektos/act-environments-ubuntu:18.04
```

### 3. 运行特定的CI作业

```powershell
# 运行所有作业
act

# 只运行test作业（这是我们修复的重点）
act -j test

# 只运行build作业
act -j build

# 运行并显示详细输出（用于调试）
act -j test --verbose
```

### 4. 处理环境变量

如果CI工作流需要环境变量，可以通过以下方式提供：

```powershell
# 创建.env文件
@"
DATABASE_URL=postgresql://admin:password@localhost:5432/example_db
REDIS_URL=redis://localhost:6379/2
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
"@ | Out-File -FilePath .env -Encoding utf8

# 使用.env文件运行
act -j test
```

### 5. 启动本地服务（用于测试）

在运行测试前，确保必要的服务正在运行：

```powershell
# 使用docker-compose启动所需服务
docker-compose up -d postgres redis
```

## 6. 完整测试流程

```powershell
# 1. 启动必要的服务
cd f:\pxy\PycharmProjects\fastapi-ledger
docker-compose up -d postgres redis

# 2. 运行test作业
docker run -it --rm --network=host -v ${pwd}:/workspace -w /workspace ghcr.io/nektos/act-environments-ubuntu:18.04 \
  bash -c "
    apt-get update && apt-get install -y python3 python3-pip
    pip install -r requirements.txt
    export PYTHONPATH=$PWD
    pytest -q scripts/test_celery_result_retention.py
  "
```

## 替代方案：使用Docker直接模拟

如果不想安装`act`，也可以直接使用Docker模拟CI环境：

```powershell
# 使用Docker直接运行，模拟GitHub Actions环境
docker run -it --rm --network=host -v ${pwd}:/workspace -w /workspace python:3.10 \
  bash -c "
    pip install -r requirements.txt
    export PYTHONPATH=$PWD
    pytest -q scripts/test_celery_result_retention.py
  "
```

## 注意事项

1. **网络连接**：在Windows上，Docker的网络模式可能需要调整以访问主机服务
2. **环境差异**：本地模拟环境与GitHub Actions可能有细微差异
3. **服务依赖**：确保测试所需的所有服务（PostgreSQL、Redis等）都在运行

## 验证我们的修复

使用上述方法运行测试后，可以确认我们对`PYTHONPATH=$PWD`的设置是否成功解决了模块导入问题。如果测试通过，说明修复方案是有效的，提交到GitHub后应该也能通过CI验证。