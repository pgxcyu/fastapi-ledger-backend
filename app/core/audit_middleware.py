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
    
    def __init__(self, app, skip_paths: list = None, skip_methods: list = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        self.skip_methods = skip_methods or ["OPTIONS", "HEAD"]
    
    def _get_device_fingerprint(self, user_agent: str, ip_address: str) -> tuple:
        """生成设备指纹和识别浏览器、操作系统"""
        try:
            # 生成设备指纹（基于User-Agent和IP的简单哈希）
            fingerprint_data = f"{user_agent}_{ip_address}"
            device_fingerprint = hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
            
            # 解析浏览器类型
            browser_type = "未知"
            if "Chrome" in user_agent:
                browser_type = "Chrome"
            elif "Firefox" in user_agent:
                browser_type = "Firefox"
            elif "Safari" in user_agent and "Chrome" not in user_agent:
                browser_type = "Safari"
            elif "Edge" in user_agent:
                browser_type = "Edge"
            elif "Opera" in user_agent:
                browser_type = "Opera"
            elif "MSIE" in user_agent or "Trident" in user_agent:
                browser_type = "Internet Explorer"
            
            # 解析操作系统类型
            os_type = "未知"
            if "Windows" in user_agent:
                os_type = "Windows"
            elif "Macintosh" in user_agent or "Mac OS" in user_agent:
                os_type = "macOS"
            elif "Linux" in user_agent:
                os_type = "Linux"
            elif "Android" in user_agent:
                os_type = "Android"
            elif "iOS" in user_agent or "iPhone" in user_agent or "iPad" in user_agent:
                os_type = "iOS"
            
            return (device_fingerprint, browser_type, os_type)
            
        except:
            return ("未知", "未知", "未知")
    
    def _get_geo_location(self, ip_address: str) -> tuple:
        """根据IP地址获取地理位置信息（简化版本）"""
        try:
            # 这里使用简单的IP段判断，实际项目中可以使用更专业的IP地理位置库
            # 如：geoip2、ip-api.com、ipinfo.io等
            
            if ip_address.startswith('127.') or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
                return ('本地', '本地', '本地')
            
            # 简单的国内IP段判断
            if ip_address.startswith('1.') or ip_address.startswith('58.') or ip_address.startswith('59.') or ip_address.startswith('60.') or ip_address.startswith('61.'):
                return ('中国', '未知', '未知')
            
            # 其他IP默认为国外
            return ('未知', '未知', '未知')
            
        except:
            return ('未知', '未知', '未知')
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否跳过审计
        if (request.url.path in self.skip_paths or 
            request.method in self.skip_methods):
            return await call_next(request)
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 准备审计数据
        audit_data = {
            'operation_description': f"{request.method} {request.url.path}",
            'operation_type': self._get_operation_type(request.method),
            'resource_type': self._get_resource_type(request.url.path),
            'operation_module': self._get_operation_module(request.url.path),
            'audit_level': AuditLevel.INFO,
            'risk_level': self._get_risk_level(request.method, request.url.path),
            'ip_address': getattr(request.client, 'host', None) if request.client else None,
            'user_agent': request.headers.get('User-Agent'),
            'request_method': request.method,
            'request_path': str(request.url.path),
            'operation_result': AuditResult.SUCCESS
        }
        
        # 获取客户端IP
        client_ip = request.client.host
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # 获取User-Agent
        user_agent = request.headers.get("user-agent", "未知")
        
        # 获取地理位置信息
        country, region, city = self._get_geo_location(client_ip)
        
        # 获取设备指纹信息
        device_fingerprint, browser_type, os_type = self._get_device_fingerprint(user_agent, client_ip)
        
        # 获取用户信息 - 直接从request.state获取，因为RequestContextMiddleware还没执行
        user_info = {}
        user_id = getattr(request.state, 'user_id', None)
        sid = getattr(request.state, 'sid', None)
        role_id = getattr(request.state, 'role_id', None)
        
        if user_id:
            user_info['user_id'] = user_id
        if sid:
            user_info['session_id'] = sid
        if role_id:
            user_info['role_id'] = role_id
            
        audit_data.update(user_info)
        
        # 添加request_id
        request_id = get_request_id()
        if request_id:
            audit_data['request_id'] = request_id
        
        # 如果有user_id，查询用户名
        if audit_data.get('user_id'):
            user_name = audit_service.get_user_name_by_id(audit_data['user_id'])
            if user_name:
                audit_data['user_name'] = user_name
        
        # 添加IP和地理位置信息
        audit_data['ip_address'] = client_ip
        audit_data['country'] = country
        audit_data['region'] = region
        audit_data['city'] = city
        
        # 添加设备指纹信息
        audit_data['user_agent'] = user_agent
        audit_data['device_fingerprint'] = device_fingerprint
        audit_data['browser_type'] = browser_type
        audit_data['os_type'] = os_type
        
        # 记录请求参数（脱敏处理）
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8')
                    # 简单的脱敏处理
                    body_data = json.loads(body_str) if body_str else {}
                    sanitized_body = audit_service.sanitize_data(body_data)
                    audit_data['before_data'] = json.dumps(sanitized_body, ensure_ascii=False)
        except:
            pass
        
        # 执行请求
        response = None
        try:
            response = await call_next(request)
            
            # 计算响应时间
            response_time = time.time() - start_time
            audit_data['business_context'] = f"Response time: {response_time:.3f}s"
            audit_data['response_time'] = response_time
            
            # 获取响应状态码
            response_status = response.status_code
            audit_data['response_status'] = response_status
            
            # 检查响应状态
            if response_status >= 400:
                audit_data['operation_result'] = AuditResult.FAILURE
                audit_data['audit_level'] = AuditLevel.WARNING if response_status < 500 else AuditLevel.ERROR
            
            # 记录响应数据（部分）
            if response.status_code >= 400:
                try:
                    response_body = b""
                    async for chunk in response.body_iterator:
                        response_body += chunk
                    
                    if response_body:
                        response_str = response_body.decode('utf-8')
                        response_data = json.loads(response_str) if response_str else {}
                        sanitized_response = audit_service.sanitize_data(response_data)
                        audit_data['after_data'] = json.dumps(sanitized_response, ensure_ascii=False)
                    
                    # 重新创建响应
                    from fastapi import Response
                    response = Response(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                except:
                    pass
            
            # 保存审计日志
            audit_service.save_audit_log(None, audit_data)
            
            return response
            
        except Exception as e:
            # 记录异常
            audit_data['operation_result'] = AuditResult.FAILURE
            audit_data['audit_level'] = AuditLevel.ERROR
            audit_data['business_context'] = f"Error: {str(e)}"
            audit_service.save_audit_log(None, audit_data)
            raise
    
    def _get_operation_type(self, method: str) -> str:
        """根据HTTP方法确定操作类型"""
        mapping = {
            "GET": OperationType.READ,
            "POST": OperationType.CREATE,
            "PUT": OperationType.UPDATE,
            "PATCH": OperationType.UPDATE,
            "DELETE": OperationType.DELETE
        }
        return mapping.get(method, OperationType.READ)
    
    def _get_operation_module(self, path: str) -> str:
        """根据路径确定操作模块"""
        if "/user" in path or "/auth" in path:
            return "USER"
        elif "/transaction" in path:
            return "TRANSACTION"
        elif "/role" in path:
            return "ROLE"
        elif "/file" in path:
            return "FILE"
        elif "/system" in path:
            return "SYSTEM"
        else:
            return "API"

    def _get_resource_type(self, path: str) -> str:
        """根据路径确定资源类型"""
        if "/user" in path or "/auth" in path:
            return ResourceType.USER
        elif "/transaction" in path:
            return ResourceType.TRANSACTION
        elif "/role" in path:
            return ResourceType.ROLE
        elif "/file" in path:
            return ResourceType.FILE
        else:
            return ResourceType.SYSTEM
    
    def _get_risk_level(self, method: str, path: str) -> str:
        """根据方法和路径确定风险级别"""
        # 高风险操作
        if method in ["DELETE", "POST"] and "/user" in path:
            return RiskLevel.HIGH
        elif method == "DELETE":
            return RiskLevel.MEDIUM
        elif method in ["POST", "PUT", "PATCH"] and "/transaction" in path:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW