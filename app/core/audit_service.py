# app/core/audit_service.py
import json
import time
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.request_ctx import get_user_context
from app.db.models import AuditLog, User

# 直接定义枚举类，避免循环导入
class OperationType:
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    READ = "READ"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    TRANSACTION = "TRANSACTION"

class ResourceType:
    USER = "USER"
    TRANSACTION = "TRANSACTION"
    ROLE = "ROLE"
    FILE = "FILE"
    SYSTEM = "SYSTEM"

class AuditLevel:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AuditResult:
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"

class AuditService:
    """审计服务类 - 统一处理审计日志的保存逻辑"""
    
    @staticmethod
    def generate_audit_id(user_id: Optional[str] = None) -> str:
        """生成审计ID"""
        return f"audit_{int(time.time())}_{user_id or 'unknown'}"
    
    @staticmethod
    def get_user_info(current_user=None) -> Dict[str, Any]:
        """获取用户信息"""
        user_info = {}
        
        if current_user:
            user_info['user_id'] = current_user.userid
            user_info['user_name'] = getattr(current_user, 'username', None)
        else:
            user_id, sid, role_id = get_user_context()
            if user_id:
                user_info['user_id'] = user_id
            if sid:
                user_info['session_id'] = sid
            if role_id:
                user_info['role_id'] = role_id
        
        return user_info
    
    @staticmethod
    def get_user_name_by_id(user_id: str) -> Optional[str]:
        """根据用户ID查询用户名"""
        try:
            db = next(get_db())
            user = db.query(User).filter(User.userid == user_id).first()
            db.close()
            return user.username if user else None
        except:
            return None
    
    @staticmethod
    def create_audit_log_from_data(audit_data: Dict[str, Any]) -> AuditLog:
        """从审计数据字典创建AuditLog对象"""
        audit_log = AuditLog()
        
        # 基础字段
        audit_log.audit_id = audit_data.get('audit_id') or AuditService.generate_audit_id(audit_data.get('user_id'))
        audit_log.user_id = audit_data.get('user_id')
        audit_log.user_name = audit_data.get('user_name')
        audit_log.session_id = audit_data.get('session_id')
        audit_log.role_id = audit_data.get('role_id')
        audit_log.request_id = audit_data.get('request_id')
        
        # 请求信息
        audit_log.ip_address = audit_data.get('ip_address')
        audit_log.country = audit_data.get('country')
        audit_log.region = audit_data.get('region')
        audit_log.city = audit_data.get('city')
        audit_log.device_fingerprint = audit_data.get('device_fingerprint')
        audit_log.browser_type = audit_data.get('browser_type')
        audit_log.os_type = audit_data.get('os_type')
        audit_log.user_agent = audit_data.get('user_agent')
        audit_log.request_method = audit_data.get('request_method')
        audit_log.request_path = audit_data.get('request_path')
        audit_log.response_status = audit_data.get('response_status')
        audit_log.response_time = audit_data.get('response_time')
        
        # 操作信息
        audit_log.operation_type = audit_data.get('operation_type') or OperationType.READ
        audit_log.operation_module = audit_data.get('operation_module') or 'SYSTEM'
        audit_log.operation_description = audit_data.get('operation_description') or 'Unknown operation'
        audit_log.resource_type = audit_data.get('resource_type') or ResourceType.SYSTEM
        audit_log.resource_id = audit_data.get('resource_id')
        audit_log.resource_name = audit_data.get('resource_name')
        
        # 审计信息
        audit_log.audit_level = audit_data.get('audit_level') or AuditLevel.INFO
        audit_log.risk_level = audit_data.get('risk_level') or RiskLevel.LOW
        audit_log.sensitive_flag = audit_data.get('sensitive_flag', False)
        audit_log.operation_result = audit_data.get('operation_result') or AuditResult.SUCCESS
        audit_log.error_message = audit_data.get('error_message')
        
        # 业务数据
        audit_log.before_data = audit_data.get('before_data')
        audit_log.after_data = audit_data.get('after_data')
        audit_log.business_context = audit_data.get('business_context')
        
        return audit_log
    
    @staticmethod
    def save_audit_log(db: Optional[Session], audit_data: Dict[str, Any]) -> bool:
        """保存审计日志到数据库"""
        # 如果没有提供db，尝试获取一个
        if not db:
            try:
                db = next(get_db())
                should_close_db = True
            except:
                return False
        else:
            should_close_db = False
        
        try:
            # 创建审计日志对象
            audit_log = AuditService.create_audit_log_from_data(audit_data)
            
            # 保存到数据库
            db.add(audit_log)
            db.commit()
            return True
            
        except Exception as e:
            # 审计日志记录失败不应该影响主业务
            print(f"Failed to save audit log: {e}")
            if db:
                db.rollback()
            return False
        finally:
            # 如果是我们自己创建的db连接，需要关闭它
            if should_close_db and db:
                db.close()
    
    @staticmethod
    def prepare_basic_audit_data(
        operation_description: str,
        operation_type: str = OperationType.READ,
        resource_type: str = ResourceType.SYSTEM,
        audit_level: str = AuditLevel.INFO,
        risk_level: str = RiskLevel.LOW,
        sensitive_flag: bool = False,
        operation_module: str = "SYSTEM",
        business_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """准备基础审计数据"""
        return {
            'operation_description': operation_description,
            'operation_type': operation_type,
            'resource_type': resource_type,
            'audit_level': audit_level,
            'risk_level': risk_level,
            'sensitive_flag': sensitive_flag,
            'operation_module': operation_module,
            'business_context': business_context,
            'operation_result': AuditResult.SUCCESS
        }
    
    @staticmethod
    def add_request_info(audit_data: Dict[str, Any], request) -> Dict[str, Any]:
        """添加请求信息到审计数据"""
        if not request:
            return audit_data
        
        audit_data.update({
            'ip_address': getattr(request.client, 'host', None) if request.client else None,
            'user_agent': request.headers.get('User-Agent'),
            'request_method': request.method,
            'request_path': str(request.url.path)
        })
        
        return audit_data
    
    @staticmethod
    def sanitize_data(data: dict) -> dict:
        """脱敏处理敏感数据"""
        if not isinstance(data, dict):
            return data
        
        sensitive_keys = ['password', 'token', 'secret', 'key', 'auth', 'credential']
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = AuditService.sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [AuditService.sanitize_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized

# 全局审计服务实例
audit_service = AuditService()