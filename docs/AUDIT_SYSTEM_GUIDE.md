# 审计系统使用指南

## 概述

本系统提供了完整的审计日志功能，包括自动记录、查询分析、数据归档和清理等功能。审计系统已经从原来的Logger表迁移到专门的AuditLog表，结构更加优化和专业。

## 核心特性

### 1. 自动审计记录
- **装饰器模式**: 通过装饰器自动记录API操作
- **中间件模式**: 自动记录所有HTTP请求
- **手动记录**: 支持在业务逻辑中手动记录审计信息

### 2. 丰富的审计字段
- 用户信息：user_id, user_name, session_id
- 请求信息：ip_address, user_agent, request_method, request_path
- 操作信息：operation_type, operation_module, operation_description
- 资源信息：resource_type, resource_id, resource_name
- 审计结果：audit_level, risk_level, sensitive_flag, operation_result
- 详细数据：before_data, after_data, business_context, error_message

### 3. 完整的查询分析
- 多条件组合查询
- 分页显示
- 统计分析
- 详情查看

### 4. 数据归档管理
- 自动归档过期数据
- 压缩存储
- 数据恢复
- 定期清理

## 接口使用方法

### 1. 审计装饰器使用

#### 基础审计装饰器
```python
from app.core.audit import audit_log, OperationType, ResourceType, AuditLevel, RiskLevel

@router.post("/user/create")
@audit_log(
    operation_description="创建用户账户",
    operation_type=OperationType.CREATE,
    resource_type=ResourceType.USER,
    audit_level=AuditLevel.INFO,
    risk_level=RiskLevel.MEDIUM,
    sensitive_flag=True
)
async def create_user(user_data: dict):
    # 业务逻辑
    pass
```

#### 便捷审计装饰器
```python
from app.core.audit import audit_transaction, audit_user, audit_login, audit_sensitive

# 事务审计
@audit_transaction(operation_description="执行转账", risk_level=RiskLevel.HIGH)
async def transfer_money():
    pass

# 用户操作审计
@audit_user(operation_description="更新用户信息")
async def update_user():
    pass

# 登录审计
@audit_login(operation_description="用户登录")
async def login():
    pass

# 敏感操作审计
@audit_sensitive(operation_description="删除用户", risk_level=RiskLevel.CRITICAL)
async def delete_user():
    pass
```

### 2. 手动审计记录
```python
from app.core.audit import _save_audit_log, OperationType, AuditResult

async def some_business_logic():
    try:
        # 业务逻辑
        result = do_something()
        
        # 手动记录成功审计
        audit_data = {
            "operation_type": OperationType.UPDATE,
            "operation_description": "手动记录的操作",
            "operation_result": AuditResult.SUCCESS,
            "business_context": {"result": result}
        }
        _save_audit_log(db, audit_data, current_user)
        
    except Exception as e:
        # 手动记录失败审计
        audit_data = {
            "operation_type": OperationType.UPDATE,
            "operation_description": "手动记录的操作",
            "operation_result": AuditResult.FAILURE,
            "error_message": str(e)
        }
        _save_audit_log(db, audit_data, current_user)
```

### 3. 审计查询API

#### 获取审计日志列表
```http
GET /audit/logs?page=1&size=20&user_id=user123&operation_type=CREATE&risk_level=HIGH
```

**查询参数：**
- `page`: 页码（默认1）
- `size`: 每页数量（默认20，最大100）
- `user_id`: 用户ID
- `operation_type`: 操作类型（CREATE/UPDATE/DELETE/READ/LOGIN/LOGOUT/EXPORT/IMPORT）
- `resource_type`: 资源类型（USER/TRANSACTION/ROLE/FILE/SYSTEM）
- `audit_level`: 审计级别（INFO/WARNING/ERROR/CRITICAL）
- `risk_level`: 风险级别（LOW/MEDIUM/HIGH/CRITICAL）
- `operation_result`: 操作结果（SUCCESS/FAILURE/PARTIAL）
- `start_time`: 开始时间（ISO格式）
- `end_time`: 结束时间（ISO格式）
- `keyword`: 关键词搜索
- `sensitive_only`: 仅显示敏感操作

#### 获取审计日志详情
```http
GET /audit/logs/{audit_id}
```

#### 获取审计统计
```http
GET /audit/stats?days=7
```

#### 获取枚举值
```http
GET /audit/enums
```

### 4. 归档管理API

#### 获取归档信息
```http
GET /audit-management/archive/info
```

#### 执行归档
```http
POST /audit-management/archive/run?days=90
```

#### 执行清理
```http
POST /audit-management/cleanup/run?days=365
```

#### 恢复归档数据
```http
POST /audit-management/restore/audit_logs_2024-01.json.gz
```

## 配置说明

在 `app/core/config.py` 中添加以下配置：

```python
# 审计配置
AUDIT_ARCHIVE_DIR = "archives/audit"  # 归档目录
AUDIT_RETENTION_DAYS = 365           # 保留天数
AUDIT_ARCHIVE_AFTER_DAYS = 90        # 归档天数
AUDIT_COMPRESSION_ENABLED = True     # 是否启用压缩
```

## 最佳实践

### 1. 选择合适的审计装饰器
- **audit_transaction**: 用于金融交易、订单等业务操作
- **audit_user**: 用于用户管理相关操作
- **audit_login**: 用于登录、登出等认证操作
- **audit_sensitive**: 用于删除、权限变更等敏感操作
- **audit_log**: 用于其他一般操作

### 2. 设置合适的风险级别
- **LOW**: 普通查询、信息查看
- **MEDIUM**: 数据更新、用户操作
- **HIGH**: 转账、订单创建、权限变更
- **CRITICAL**: 删除操作、系统配置变更

### 3. 记录有意义的业务上下文
```python
@audit_transaction(operation_description="创建订单")
async def create_order(order_data):
    # 审计系统会自动记录before_data和after_data
    # 可以在business_context中记录额外的业务信息
    return {
        "order_id": "12345",
        "business_context": {
            "customer_id": order_data["customer_id"],
            "product_ids": order_data["product_ids"],
            "payment_method": order_data["payment_method"]
        }
    }
```

### 4. 定期归档和清理
建议设置定时任务，定期执行归档和清理：

```python
# 在Celery Beat中设置定时任务
from app.core.audit_archive import schedule_archive_cleanup

# 每周执行一次归档和清理
# schedule_archive_cleanup()
```

## 数据迁移

如果从旧的Logger表迁移到新的AuditLog表，可以使用以下SQL脚本：

```sql
-- 数据迁移脚本
INSERT INTO audit_logs (
    audit_id, user_id, user_name, session_id, ip_address, user_agent,
    request_method, request_path, operation_type, operation_module,
    operation_description, resource_type, resource_id, resource_name,
    audit_level, risk_level, sensitive_flag, operation_result,
    error_message, before_data, after_data, business_context,
    created_at, updated_at
)
SELECT 
    id as audit_id,
    userid as user_id,
    NULL as user_name,
    session_id,
    ip_address,
    user_agent,
    request_method,
    request_path,
    action as operation_type,
    'SYSTEM' as operation_module,
    action as operation_description,
    'SYSTEM' as resource_type,
    NULL as resource_id,
    NULL as resource_name,
    'INFO' as audit_level,
    'LOW' as risk_level,
    compliance_flag as sensitive_flag,
    CASE WHEN status = 'success' THEN 'SUCCESS' ELSE 'FAILURE' END as operation_result,
    NULL as error_message,
    info as before_data,
    NULL as after_data,
    NULL as business_context,
    created_at,
    updated_at
FROM logger;
```

## 故障排除

### 1. 审计记录不显示
- 检查装饰器是否正确应用
- 确认数据库连接正常
- 查看应用日志是否有错误信息

### 2. 归档失败
- 检查归档目录权限
- 确认磁盘空间充足
- 查看归档配置是否正确

### 3. 查询性能问题
- 检查数据库索引
- 考虑增加查询条件
- 定期执行归档清理

## 扩展开发

### 1. 添加新的操作类型
在 `app/core/audit.py` 中扩展 `OperationType` 枚举：

```python
class OperationType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    READ = "READ"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    APPROVE = "APPROVE"  # 新增
    REJECT = "REJECT"     # 新增
```

### 2. 自定义审计处理器
可以继承审计装饰器，实现自定义的审计逻辑：

```python
from functools import wraps
from app.core.audit import _save_audit_log

def custom_audit(operation_description: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 自定义审计逻辑
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 3. 集成外部系统
可以将审计数据发送到外部系统：

```python
# 在审计保存时同时发送到外部系统
def send_to_external_system(audit_data):
    # 发送到ELK、Splunk等
    pass
```

## 总结

本审计系统提供了完整的审计日志解决方案，具有以下优势：

1. **自动化程度高**: 装饰器和中间件自动记录，减少手动工作
2. **数据结构完整**: 涵盖用户、请求、操作、资源等全方位信息
3. **查询功能强大**: 支持多条件查询、统计分析
4. **数据管理完善**: 自动归档、压缩存储、定期清理
5. **扩展性好**: 支持自定义装饰器、外部系统集成

通过合理使用审计系统，可以有效监控和追踪系统中的各种操作，满足合规要求，提高系统安全性。