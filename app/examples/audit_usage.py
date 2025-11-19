# app/examples/audit_usage.py
"""
审计功能使用示例
展示如何在不同的业务接口中使用审计装饰器和中间件
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.core.audit import (
    audit_log, 
    audit_transaction, 
    audit_user, 
    audit_login, 
    audit_sensitive,
    OperationType, 
    ResourceType, 
    AuditLevel, 
    RiskLevel,
    AuditResult
)
from app.schemas.response import R

router = APIRouter(prefix="/examples", tags=["审计使用示例"])

# ==================== 基础审计装饰器使用示例 ====================

@router.post("/user/create")
@audit_log(
    operation_description="创建用户账户",
    operation_type=OperationType.CREATE,
    resource_type=ResourceType.USER,
    audit_level=AuditLevel.INFO,
    risk_level=RiskLevel.MEDIUM,
    sensitive_flag=True
)
async def create_user_example(
    user_data: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建用户示例 - 使用基础审计装饰器
    自动记录：操作描述、操作类型、资源类型、审计级别、风险级别、敏感操作标志
    """
    # 业务逻辑
    try:
        # 模拟创建用户
        new_user_id = "user_12345"
        
        return R.ok(
            data={"user_id": new_user_id},
            message="用户创建成功"
        )
    except Exception as e:
        # 异常会被审计装饰器自动捕获并记录为失败
        raise HTTPException(status_code=400, detail=str(e))

# ==================== 便捷审计装饰器使用示例 ====================

@router.post("/transaction/transfer")
@audit_transaction(
    operation_description="执行转账操作",
    operation_type=OperationType.UPDATE
)
async def transfer_example(
    from_account: str,
    to_account: str,
    amount: float,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    转账操作示例 - 使用事务审计装饰器
    自动设置：operation_type=TRANSACTION, resource_type=TRANSACTION, operation_module=TRANSACTION
    """
    try:
        # 模拟转账业务逻辑
        if amount <= 0:
            raise ValueError("转账金额必须大于0")
        
        # 记录操作前数据
        before_data = {
            "from_account_balance": 1000.0,
            "to_account_balance": 500.0
        }
        
        # 执行转账（模拟）
        # ... 转账逻辑 ...
        
        # 记录操作后数据
        after_data = {
            "from_account_balance": 1000.0 - amount,
            "to_account_balance": 500.0 + amount
        }
        
        return R.ok(
            data={
                "transaction_id": "txn_12345",
                "before_data": before_data,
                "after_data": after_data
            },
            message="转账成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/user/update")
@audit_user(
    operation_description="更新用户信息",
    operation_type=OperationType.UPDATE
)
async def update_user_example(
    user_id: str,
    update_data: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户信息示例 - 使用用户审计装饰器
    自动设置：operation_type=UPDATE, resource_type=USER, operation_module=USER
    """
    try:
        # 模拟更新用户信息
        # ... 更新逻辑 ...
        
        return R.ok(
            data={"user_id": user_id, "updated_fields": list(update_data.keys())},
            message="用户信息更新成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/login")
@audit_login(operation_description="用户登录")
async def login_example(
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    用户登录示例 - 使用登录审计装饰器
    自动设置：operation_type=LOGIN, resource_type=USER, operation_module=AUTH
    """
    try:
        # 模拟登录验证
        if username == "admin" and password == "password":
            return R.ok(
                data={"token": "jwt_token_here", "user_id": "user_123"},
                message="登录成功"
            )
        else:
            raise ValueError("用户名或密码错误")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.delete("/user/delete")
@audit_sensitive(
    operation_description="删除用户账户",
    operation_type=OperationType.DELETE
)
async def delete_user_example(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除用户示例 - 使用敏感操作审计装饰器
    自动设置：sensitive_flag=True, operation_type=DELETE, resource_type=USER, operation_module=SECURITY
    """
    try:
        # 模拟删除用户
        # ... 删除逻辑 ...
        
        return R.ok(
            data={"deleted_user_id": user_id},
            message="用户删除成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== 手动审计记录示例 ====================

@router.post("/manual/audit")
async def manual_audit_example(
    action: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动审计记录示例
    在业务逻辑中手动调用审计记录
    """
    from app.core.audit_service import audit_service
    
    try:
        # 业务逻辑
        result = f"执行操作: {action}"
        
        # 手动记录审计日志
        audit_data = audit_service.prepare_basic_audit_data(
            operation_type=OperationType.UPDATE,
            operation_module="MANUAL",
            operation_description=f"手动记录的操作: {action}",
            resource_type=ResourceType.SYSTEM,
            resource_name="手动审计示例",
            audit_level=AuditLevel.INFO,
            risk_level=RiskLevel.LOW,
            sensitive_flag=False,
            operation_result=AuditResult.SUCCESS,
            business_context={"action": action, "result": result}
        )
        
        # 添加用户信息
        audit_data.update(audit_service.get_user_info(current_user))
        
        audit_service.save_audit_log(db, audit_data)
        
        return R.ok(
            data={"result": result},
            message="操作完成并已记录审计日志"
        )
    except Exception as e:
        # 手动记录失败审计
        audit_data = audit_service.prepare_basic_audit_data(
            operation_type=OperationType.UPDATE,
            operation_module="MANUAL",
            operation_description=f"手动记录的操作: {action}",
            resource_type=ResourceType.SYSTEM,
            resource_name="手动审计示例",
            audit_level=AuditLevel.ERROR,
            risk_level=RiskLevel.MEDIUM,
            sensitive_flag=False,
            operation_result=AuditResult.FAILURE,
            error_message=str(e),
            business_context={"action": action}
        )
        
        # 添加用户信息
        audit_data.update(audit_service.get_user_info(current_user))
        
        audit_service.save_audit_log(db, audit_data)
        
        raise HTTPException(status_code=400, detail=str(e))

# ==================== 复杂业务场景审计示例 ====================

@router.post("/order/create")
@audit_log(
    operation_description="创建订单",
    operation_type=OperationType.CREATE,
    resource_type=ResourceType.TRANSACTION,
    audit_level=AuditLevel.INFO,
    risk_level=RiskLevel.HIGH,
    sensitive_flag=True
)
async def create_order_example(
    order_data: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    复杂业务场景审计示例 - 创建订单
    展示如何记录操作前后的数据变化
    """
    try:
        # 获取操作前状态
        before_data = {
            "user_balance": 1000.0,
            "product_stock": 100,
            "order_count": 5
        }
        
        # 模拟订单创建逻辑
        order_id = "order_12345"
        order_amount = order_data.get("amount", 0)
        
        # 更新相关数据
        # ... 业务逻辑 ...
        
        # 获取操作后状态
        after_data = {
            "user_balance": 1000.0 - order_amount,
            "product_stock": 99,
            "order_count": 6
        }
        
        # 业务上下文信息
        business_context = {
            "order_id": order_id,
            "order_amount": order_amount,
            "payment_method": order_data.get("payment_method"),
            "shipping_address": order_data.get("shipping_address")
        }
        
        return R.ok(
            data={
                "order_id": order_id,
                "before_data": before_data,
                "after_data": after_data,
                "business_context": business_context
            },
            message="订单创建成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== API接口使用说明 ====================

@router.get("/usage/guide")
async def audit_usage_guide():
    """
    审计功能使用指南
    """
    guide = {
        "title": "审计功能使用指南",
        "decorators": {
            "audit_log": "基础审计装饰器，需要手动指定所有参数",
            "audit_transaction": "事务审计装饰器，自动设置事务相关参数",
            "audit_user": "用户操作审计装饰器，自动设置用户相关参数",
            "audit_login": "登录审计装饰器，自动设置登录相关参数",
            "audit_sensitive": "敏感操作审计装饰器，自动标记为敏感操作"
        },
        "parameters": {
            "operation_description": "操作描述（必需）",
            "operation_type": "操作类型（CREATE/UPDATE/DELETE/READ/LOGIN/LOGOUT/EXPORT/IMPORT）",
            "resource_type": "资源类型（USER/TRANSACTION/ROLE/FILE/SYSTEM）",
            "audit_level": "审计级别（INFO/WARNING/ERROR/CRITICAL）",
            "risk_level": "风险级别（LOW/MEDIUM/HIGH/CRITICAL）",
            "sensitive_flag": "是否为敏感操作",
            "operation_module": "操作模块"
        },
        "automatic_data": {
            "user_info": "自动获取当前用户信息（user_id, user_name, session_id）",
            "request_info": "自动获取请求信息（ip_address, user_agent, request_method, request_path）",
            "timestamps": "自动记录创建和更新时间",
            "result": "自动根据函数执行结果设置操作结果"
        },
        "apis": {
            "audit_logs": "GET /audit/logs - 获取审计日志列表",
            "audit_detail": "GET /audit/logs/{audit_id} - 获取审计日志详情",
            "audit_stats": "GET /audit/stats - 获取审计统计数据",
            "audit_enums": "GET /audit/enums - 获取枚举值",
            "archive_info": "GET /audit-management/archive/info - 获取归档信息",
            "run_archive": "POST /audit-management/archive/run - 执行归档",
            "run_cleanup": "POST /audit-management/cleanup/run - 执行清理",
            "restore_archive": "POST /audit-management/restore/{filename} - 恢复归档"
        }
    }
    
    return R.ok(data=guide, message="审计功能使用指南")