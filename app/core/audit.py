# app/core/audit.py
import functools
from functools import wraps
import time
import traceback
from typing import Any, Callable, Dict, Optional

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
from app.core.request_ctx import get_request_id
from app.db.models import AuditLog



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
    business_context: Optional[str] = None
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
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 获取请求对象
            request = None
            db = None
            current_user = None
            
            # 从参数中提取关键对象
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif hasattr(arg, 'query'):  # Session 对象
                    db = arg
                    
            for key, value in kwargs.items():
                if key == 'request' and isinstance(value, Request):
                    request = value
                elif key == 'db' and hasattr(value, 'query'):
                    db = value
                elif key == 'current_user':
                    current_user = value
            
            # 如果没有db，尝试获取
            if db is None:
                try:
                    db = next(get_db())
                except:
                    pass
            
            # 准备基础审计数据
            audit_data = audit_service.prepare_basic_audit_data(
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
            
            # 获取资源ID
            if get_resource_id:
                try:
                    resource_id = get_resource_id(*args, **kwargs)
                    audit_data['resource_id'] = resource_id
                except:
                    pass
            
            # 获取操作前数据
            if get_before_data:
                try:
                    before_data = get_before_data(*args, **kwargs)
                    if before_data:
                        audit_data['before_data'] = json.dumps(before_data, ensure_ascii=False) if not isinstance(before_data, str) else before_data
                except:
                    pass
            
            # 执行原函数
            try:
                result = await func(*args, **kwargs)
                
                # 获取操作后数据
                if get_after_data:
                    try:
                        after_data = get_after_data(*args, **kwargs, result=result)
                        if after_data:
                            audit_data['after_data'] = json.dumps(after_data, ensure_ascii=False) if not isinstance(after_data, str) else after_data
                    except:
                        pass
                
                # 记录成功的审计日志
                audit_service.save_audit_log(db, audit_data)
                
                return result
                
            except Exception as e:
                # 记录失败的审计日志
                audit_data['operation_result'] = AuditResult.FAILURE
                audit_data['business_context'] = f"{business_context or ''} - Error: {str(e)}"
                audit_service.save_audit_log(db, audit_data)
                raise
                
        return wrapper
    return decorator

# 便捷的审计装饰器
def audit_transaction(operation_description: str, operation_type: str = OperationType.READ):
    """交易操作审计"""
    return audit_log(
        operation_description=operation_description,
        operation_type=operation_type,
        resource_type=ResourceType.TRANSACTION,
        operation_module="TRANSACTION",
        get_resource_id=lambda *args, **kwargs: kwargs.get('transaction_id') or getattr(kwargs.get('transaction', ''), 'transaction_id', None)
    )

def audit_user(operation_description: str, operation_type: str = OperationType.READ):
    """用户操作审计"""
    return audit_log(
        operation_description=operation_description,
        operation_type=operation_type,
        resource_type=ResourceType.USER,
        operation_module="USER",
        risk_level=RiskLevel.MEDIUM,
        sensitive_flag=True
    )

def audit_login(operation_description: str):
    """登录操作审计"""
    return audit_log(
        operation_description=operation_description,
        operation_type=OperationType.LOGIN,
        resource_type=ResourceType.USER,
        operation_module="AUTH",
        audit_level=AuditLevel.INFO,
        risk_level=RiskLevel.MEDIUM
    )

def audit_sensitive(operation_description: str, operation_type: str = OperationType.UPDATE):
    """敏感操作审计"""
    return audit_log(
        operation_description=operation_description,
        operation_type=operation_type,
        operation_module="SECURITY",
        audit_level=AuditLevel.WARNING,
        risk_level=RiskLevel.HIGH,
        sensitive_flag=True
    )