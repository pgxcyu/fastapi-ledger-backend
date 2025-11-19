# app/core/audit.py
import functools
from functools import wraps
import json
import time
import traceback
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.audit_service import (
    AuditLevel,
    AuditResult,
    OperationType,
    ResourceType,
    RiskLevel,
    audit_service,
)
from app.core.deps import get_db
from app.core.logging import logger
from app.core.request_ctx import get_request_id
from app.db.models import AuditLog

audit_logger = logger.bind(module="audit")

# 类型别名
Handler = Callable[..., Awaitable[Any]]
GetDataFunc = Callable[..., Any]


async def _call_maybe_async(func: Optional[GetDataFunc], *args, **kwargs) -> Any:
    if not func:
        return None
    try:
        value = func(*args, **kwargs)
        if inspect.isawaitable(value):
            value = await value
        return value
    except Exception as e:
        audit_logger.debug(f"audit get_data func error: {e}")
        return None


def audit_log(
    operation_description: str,
    operation_type: str = OperationType.READ,
    resource_type: str = ResourceType.SYSTEM,
    audit_level: str = AuditLevel.INFO,
    risk_level: str = RiskLevel.LOW,
    sensitive_flag: bool = False,
    operation_module: str = "SYSTEM",
    get_resource_id: Optional[Callable] = None,
    get_before_data: Optional[Callable] = None,
    get_after_data: Optional[Callable] = None,
    business_context: Optional[str] = None,
    *,
    strict_require_db: bool = True,
    use_separate_session: bool = False,
):
    """
    审计日志装饰器
    
    Args:
        operation_description: 操作描述
        operation_type: 操作类型
        resource_type: 资源类型
        audit_level: 审计级别
        risk_level: 风险级别
        sensitive_flag: 是否为敏感操作
        operation_module: 操作模块
        get_resource_id: 获取资源ID的函数
        get_before_data: 获取操作前数据的函数
        get_after_data: 获取操作后数据的函数
        business_context: 业务上下文描述
        strict_require_db: 是否强制要求 db 参数（推荐 True；如果老代码较多，可先设 False 过渡）
        use_separate_session: 是否将审计写入独立 Session（不影响当前事务）
    """
    def decorator(func: Handler) -> Handler:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 1. 提取关键对象
            request: Optional[Request] = kwargs.get("request")
            db: Optional[Session] = kwargs.get("db")
            current_user = kwargs.get("current_user")

            if strict_require_db and db is None and not use_separate_session:
                # 强制约束：有审计就应该有 db（否则使用独立 Session）
                audit_logger.warning(
                    f"[audit_log] {func.__name__} 没有显式 db 参数，"
                    f"建议在路由中加 db: Session = Depends(get_db)"
                )
            
            # 准备基础审计数据
            audit_data: Dict[str, Any] = audit_service.prepare_basic_audit_data(
                operation_description=operation_description,
                operation_type=operation_type,
                resource_type=resource_type,
                audit_level=audit_level,
                risk_level=risk_level,
                sensitive_flag=sensitive_flag,
                operation_module=operation_module,
                business_context=business_context
            )
            
            # 添加请求信息
            audit_service.add_request_info(audit_data, request)
            
            # 获取用户信息
            user_info = audit_service.get_user_info(current_user)
            audit_data.update(user_info)
            
            # 添加request_id
            request_id = get_request_id()
            if request_id:
                audit_data['request_id'] = request_id
            
            # 资源 ID
            resource_id = await _call_maybe_async(get_resource_id, *args, **kwargs)
            if resource_id is not None:
                audit_data["resource_id"] = resource_id

            # 操作前数据
            before_data = await _call_maybe_async(get_before_data, *args, **kwargs)
            if before_data is not None:
                audit_data["before_data"] = audit_service.serialize_data(before_data)
            
            # 3. 执行业务函数
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                # 失败场景审计
                audit_data["operation_result"] = AuditResult.FAILURE
                audit_data["audit_level"] = AuditLevel.ERROR
                audit_data["error_message"] = str(e)

                # 失败时可附加上下文
                if business_context:
                    audit_data["business_context"] = f"{business_context} | Error: {e}"
                else:
                    audit_data["business_context"] = f"Error: {e}"

                audit_service.save_audit_log(
                    db, audit_data, use_separate_session=use_separate_session
                )
                raise

            # 4. 成功场景追加 after_data
            after_data = await _call_maybe_async(get_after_data, *args, **kwargs, result=result)
            if after_data is not None:
                audit_data["after_data"] = audit_service.serialize_data(after_data)
            
            audit_data["operation_result"] = AuditResult.SUCCESS
            audit_service.save_audit_log(
                db, audit_data, use_separate_session=use_separate_session
            )

            return result
                
        return wrapper
    return decorator

# 便捷的审计装饰器
def audit_transaction(
    operation_description: str, 
    operation_type: str = OperationType.READ, 
    get_resource_id: Optional[Callable] = None,
    **kwargs
):
    """交易操作审计"""
    # 如果没有提供 get_resource_id，使用默认的
    if get_resource_id is None:
        get_resource_id = lambda *args, **kw: kw.get("transaction_id") or getattr(kw.get("transaction", ""), "transaction_id", None)
    
    return audit_log(
        operation_description=operation_description,
        operation_type=operation_type,
        resource_type=ResourceType.TRANSACTION,
        operation_module="TRANSACTION",
        get_resource_id=get_resource_id,
        **kwargs,
    )


def audit_user(operation_description: str, operation_type: str = OperationType.READ, **kwargs):
    """用户操作审计"""
    return audit_log(
        operation_description=operation_description,
        operation_type=operation_type,
        resource_type=ResourceType.USER,
        operation_module="USER",
        risk_level=RiskLevel.MEDIUM,
        sensitive_flag=True,
        **kwargs,
    )


def audit_login(operation_description: str, **kwargs):
    """登录操作审计"""
    return audit_log(
        operation_description=operation_description,
        operation_type=OperationType.LOGIN,
        resource_type=ResourceType.USER,
        operation_module="AUTH",
        audit_level=AuditLevel.INFO,
        risk_level=RiskLevel.MEDIUM,
        sensitive_flag=True,
        **kwargs,
    )


def audit_sensitive(
    operation_description: str,
    operation_type: str = OperationType.UPDATE,
    **kwargs,
):
    """敏感操作审计"""
    return audit_log(
        operation_description=operation_description,
        operation_type=operation_type,
        operation_module="SECURITY",
        audit_level=AuditLevel.WARNING,
        risk_level=RiskLevel.HIGH,
        sensitive_flag=True,
        **kwargs,
    )