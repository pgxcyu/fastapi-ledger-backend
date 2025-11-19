# app/core/audit_middleware.py
import json
import time
import socket
import struct
import hashlib
import re
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.request_ctx import get_request_id, get_user_context
from app.core.audit_service import audit_service
from app.core.audit import OperationType, ResourceType, AuditLevel, RiskLevel, AuditResult

class AuditMiddleware(BaseHTTPMiddleware):
    """审计中间件 - 自动记录所有API访问"""
    
    def __init__(self, app, skip_paths: Optional[list] = None, skip_methods: Optional[list] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        self.skip_methods = skip_methods or ["OPTIONS", "HEAD"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = str(request.url.path)
        method = request.method.upper()

        # 跳过白名单
        if path in self.skip_paths or method in self.skip_methods:
            return await call_next(request)
        
        # 记录请求开始时间
        start = time.time()
        
        # 推断操作类型 / 模块 / 资源 / 风险
        op_type, op_module, resource_type, risk_level = audit_service.classify_by_method_path(method, path)

        # 请求信息（IP/UA/设备/地理）
        audit_data = audit_service.prepare_basic_audit_data(
            operation_description=f"{method} {path}",
            operation_type=op_type,
            resource_type=resource_type,
            audit_level=AuditLevel.INFO,
            risk_level=risk_level,
            operation_module=op_module,
        )
        
        # 获取客户端IP
        audit_service.add_request_info(audit_data, request)
        
        # 获取用户信息 - 直接从request.state获取，因为RequestContextMiddleware还没执行
        user_id, sid, role_id = get_user_context()
        if user_id:
            audit_data["user_id"] = user_id
            audit_data["user_name"] = audit_service.get_user_name_by_id(user_id)
        if sid:
            audit_data["session_id"] = sid
        if role_id:
            audit_data["role_id"] = role_id
                  
        # 添加request_id
        request_id = get_request_id()
        if request_id:
            audit_data['request_id'] = request_id
        
        # 执行请求
        try:
            response = await call_next(request)
        except Exception as e:
            cost = time.time() - start
            audit_data["response_time"] = cost
            audit_data["operation_result"] = AuditResult.FAILURE
            audit_data["audit_level"] = AuditLevel.ERROR
            audit_data["error_message"] = str(e)
            audit_data["response_status"] = 500
            audit_data["business_context"] = f"Middleware error: {e}"

            audit_service.save_audit_log(db=None, audit_data=audit_data, use_separate_session=True)
            raise

        # 7. 成功/失败信息
        cost = time.time() - start
        audit_data["response_time"] = cost
        audit_data["response_status"] = response.status_code
        if response.status_code >= 400:
            audit_data["operation_result"] = AuditResult.FAILURE
            audit_data["audit_level"] = AuditLevel.WARNING if response.status_code < 500 else AuditLevel.ERROR
        else:
            audit_data["operation_result"] = AuditResult.SUCCESS

        audit_service.save_audit_log(db=None, audit_data=audit_data, use_separate_session=True)

        return response