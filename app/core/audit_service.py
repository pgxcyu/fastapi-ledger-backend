# app/core/audit_service.py
import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.request_ctx import get_user_context
from app.db.models import AuditLog, User


# ==== 统一枚举（原来散在多个文件里） ====

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
    """
    统一审计服务：
    - 所有“怎么算”的逻辑都集中在这里
    - 装饰器 / 中间件只负责在合适时机调用它
    """

    # ---------- ID / 基础构建 ----------

    @staticmethod
    def generate_audit_id(user_id: Optional[str] = None) -> str:
        """生成审计ID；可以用 user_id + 时间戳 混合生成，避免冲突"""
        base = f"{user_id or ''}-{time.time_ns()}"
        return hashlib.md5(base.encode("utf-8")).hexdigest()

    @staticmethod
    def prepare_basic_audit_data(
        operation_description: str,
        operation_type: str = OperationType.READ,
        resource_type: str = ResourceType.SYSTEM,
        audit_level: str = AuditLevel.INFO,
        risk_level: str = RiskLevel.LOW,
        sensitive_flag: bool = False,
        operation_module: str = "SYSTEM",
        business_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """准备基础审计数据（不含请求/用户信息）"""
        return {
            "operation_description": operation_description,
            "operation_type": operation_type,
            "resource_type": resource_type,
            "audit_level": audit_level,
            "risk_level": risk_level,
            "sensitive_flag": sensitive_flag,
            "operation_module": operation_module,
            "business_context": business_context,
            "operation_result": AuditResult.SUCCESS,
        }

    # ---------- 用户信息（装饰器 + 中间件复用） ----------

    @staticmethod
    def get_user_info(current_user: Optional[User] = None) -> Dict[str, Any]:
        """
        获取用户信息：
        - 有 current_user 就从 User 模型取
        - 没有就从 get_user_context() 里取 (user_id, sid, role_id)
        """
        user_info: Dict[str, Any] = {}

        if current_user is not None:
            user_info["user_id"] = getattr(current_user, "userid", None)
            user_info["user_name"] = getattr(current_user, "username", None)
            user_info["role_id"] = getattr(current_user, "role_id", None)
            user_info["session_id"] = getattr(current_user, "sid", None)
        else:
            user_id, sid, role_id = get_user_context()
            if user_id:
                user_info["user_id"] = user_id
            if sid:
                user_info["session_id"] = sid
            if role_id:
                user_info["role_id"] = role_id

        return user_info

    @staticmethod
    def get_user_name_by_id(user_id: str) -> Optional[str]:
        """给中间件等场景用：只有 user_id 时查用户名"""
        try:
            db = next(get_db())
            user = db.query(User).filter(User.userid == user_id).first()
            return user.username if user else None
        except Exception:
            return None

    # ---------- 请求 / 设备信息（原来在中间件里的逻辑，抽出来共用） ----------

    @staticmethod
    def _classify_browser_os(user_agent: str) -> Tuple[str, str]:
        ua = user_agent or ""
        browser_type = "未知"
        os_type = "未知"

        # 浏览器
        if "Chrome" in ua:
            browser_type = "Chrome"
        elif "Firefox" in ua:
            browser_type = "Firefox"
        elif "Safari" in ua and "Chrome" not in ua:
            browser_type = "Safari"
        elif "Edge" in ua:
            browser_type = "Edge"
        elif "Opera" in ua:
            browser_type = "Opera"
        elif "MSIE" in ua or "Trident" in ua:
            browser_type = "Internet Explorer"

        # 操作系统
        if "Windows" in ua:
            os_type = "Windows"
        elif "Macintosh" in ua or "Mac OS" in ua:
            os_type = "macOS"
        elif "Android" in ua:
            os_type = "Android"
        elif "iPhone" in ua or "iPad" in ua:
            os_type = "iOS"
        elif "Linux" in ua:
            os_type = "Linux"

        return browser_type, os_type

    @staticmethod
    def _geo_from_ip(ip_address: str) -> Tuple[str, str, str]:
        """
        简单的 IP -> 地理信息：
        - 内网：本地
        - 若干国内段：标记中国
        """
        if not ip_address:
            return "未知", "未知", "未知"

        if ip_address.startswith(("127.", "192.168.", "10.")):
            return "本地", "本地", "本地"

        if ip_address.startswith(("1.", "58.", "59.", "60.", "61.")):
            return "中国", "未知", "未知"

        return "未知", "未知", "未知"

    @staticmethod
    def add_request_info(audit_data: Dict[str, Any], request: Any) -> Dict[str, Any]:
        """从 Request 中抽取所有请求/设备信息"""
        if not request:
            return audit_data

        # IP：优先 X-Forwarded-For
        ip_address = None
        try:
            if request.headers.get("x-forwarded-for"):
                ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host
        except Exception:
            pass

        user_agent = request.headers.get("User-Agent") or "未知"

        audit_data["ip_address"] = ip_address
        audit_data["user_agent"] = user_agent
        audit_data["request_method"] = request.method
        audit_data["request_path"] = str(request.url.path)

        # 浏览器 / OS
        browser_type, os_type = AuditService._classify_browser_os(user_agent)
        audit_data["browser_type"] = browser_type
        audit_data["os_type"] = os_type

        # 地理信息
        country, region, city = AuditService._geo_from_ip(ip_address or "")
        audit_data["country"] = country
        audit_data["region"] = region
        audit_data["city"] = city

        # 设备指纹
        try:
            base = f"{user_agent}_{ip_address}"
            device_fingerprint = hashlib.md5(base.encode("utf-8")).hexdigest()[:16]
        except Exception:
            device_fingerprint = None
        audit_data["device_fingerprint"] = device_fingerprint

        return audit_data

    # ---------- HTTP -> 操作类型 / 模块 / 资源类型 ----------

    @staticmethod
    def classify_by_method_path(method: str, path: str) -> Tuple[str, str, str, str]:
        """
        根据 HTTP 方法与路径推断：
        - operation_type
        - operation_module
        - resource_type
        - risk_level
        """
        method = method.upper()
        operation_type = {
            "GET": OperationType.READ,
            "POST": OperationType.CREATE,
            "PUT": OperationType.UPDATE,
            "PATCH": OperationType.UPDATE,
            "DELETE": OperationType.DELETE,
        }.get(method, OperationType.READ)

        # 模块 & 资源
        operation_module = "API"
        resource_type = ResourceType.SYSTEM

        if "/auth" in path or "/user" in path:
            operation_module = "USER"
            resource_type = ResourceType.USER
        elif "/transaction" in path or "/bill" in path:
            operation_module = "TRANSACTION"
            resource_type = ResourceType.TRANSACTION
        elif "/role" in path:
            operation_module = "ROLE"
            resource_type = ResourceType.ROLE
        elif "/file" in path:
            operation_module = "FILE"
            resource_type = ResourceType.FILE

        # 风险等级（越删/改用户/账单越高）
        risk_level = RiskLevel.LOW
        if method == "DELETE":
            risk_level = RiskLevel.MEDIUM
            if resource_type in (ResourceType.USER, ResourceType.TRANSACTION):
                risk_level = RiskLevel.HIGH
        elif method in ("POST", "PUT", "PATCH") and resource_type in (
            ResourceType.USER,
            ResourceType.TRANSACTION,
        ):
            risk_level = RiskLevel.MEDIUM

        return operation_type, operation_module, resource_type, risk_level

    # ---------- 脱敏 / 序列化 ----------

    @staticmethod
    def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """对 dict 中的敏感字段做脱敏"""
        if not isinstance(data, dict):
            return data

        sensitive_keys = ["password", "pwd", "token", "secret", "key", "auth", "credential"]
        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = AuditService.sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    AuditService.sanitize_data(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def serialize_data(data: Any) -> Optional[str]:
        """将数据安全转成 JSON 字符串"""
        if data is None:
            return None
        if isinstance(data, str):
            return data
        try:
            if isinstance(data, dict):
                data = AuditService.sanitize_data(data)
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            try:
                return str(data)
            except Exception:
                return None

    # ---------- ORM 转换 ----------

    @staticmethod
    def create_audit_log_from_data(audit_data: Dict[str, Any]) -> AuditLog:
        """从 audit_data 构造 AuditLog ORM 对象"""
        audit_log = AuditLog()

        # 标识
        audit_log.audit_id = audit_data.get("audit_id") or AuditService.generate_audit_id(
            audit_data.get("user_id")
        )
        audit_log.user_id = audit_data.get("user_id")
        audit_log.user_name = audit_data.get("user_name")
        audit_log.session_id = audit_data.get("session_id")
        audit_log.role_id = audit_data.get("role_id")
        audit_log.request_id = audit_data.get("request_id")

        # 请求信息
        audit_log.ip_address = audit_data.get("ip_address")
        audit_log.user_agent = audit_data.get("user_agent")
        audit_log.request_method = audit_data.get("request_method")
        audit_log.request_path = audit_data.get("request_path")
        audit_log.response_status = audit_data.get("response_status")
        audit_log.response_time = audit_data.get("response_time")
        audit_log.country = audit_data.get("country")
        audit_log.region = audit_data.get("region")
        audit_log.city = audit_data.get("city")
        audit_log.device_fingerprint = audit_data.get("device_fingerprint")
        audit_log.browser_type = audit_data.get("browser_type")
        audit_log.os_type = audit_data.get("os_type")

        # 操作信息
        audit_log.operation_type = audit_data.get("operation_type") or OperationType.READ
        audit_log.operation_module = audit_data.get("operation_module") or "SYSTEM"
        audit_log.operation_description = audit_data.get("operation_description") or "Unknown operation"
        audit_log.resource_type = audit_data.get("resource_type") or ResourceType.SYSTEM
        audit_log.resource_id = audit_data.get("resource_id")
        audit_log.resource_name = audit_data.get("resource_name")

        # 审计信息
        audit_log.audit_level = audit_data.get("audit_level") or AuditLevel.INFO
        audit_log.risk_level = audit_data.get("risk_level") or RiskLevel.LOW
        audit_log.sensitive_flag = audit_data.get("sensitive_flag", False)
        audit_log.operation_result = audit_data.get("operation_result") or AuditResult.SUCCESS
        audit_log.error_message = audit_data.get("error_message")

        # 业务数据
        audit_log.before_data = audit_data.get("before_data")
        audit_log.after_data = audit_data.get("after_data")
        audit_log.business_context = audit_data.get("business_context")

        return audit_log

    # ---------- 持久化：装饰器 + 中间件共用 ----------

    @staticmethod
    def save_audit_log(
        db: Optional[Session],
        audit_data: Dict[str, Any],
        *,
        use_separate_session: bool = False,
    ) -> bool:
        """
        保存审计日志到数据库：
        - db 不为 None 且 use_separate_session=False：复用当前 Session，并在这里 commit 以确保落库
        - 其他情况（db 为 None 或 use_separate_session=True）：使用独立 Session，独立事务
        """
        # 复用当前 Session
        if db is not None and not use_separate_session:
            try:
                audit_log = AuditService.create_audit_log_from_data(audit_data)
                db.add(audit_log)
                db.commit()
                return True
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                return False

        # 独立 Session
        local_db: Optional[Session] = None
        try:
            local_db = next(get_db())
            audit_log = AuditService.create_audit_log_from_data(audit_data)
            local_db.add(audit_log)
            local_db.commit()
            return True
        except Exception:
            if local_db is not None:
                try:
                    local_db.rollback()
                except Exception:
                    pass
            return False
        finally:
            if local_db is not None:
                try:
                    local_db.close()
                except Exception:
                    pass


# 全局实例
audit_service = AuditService()
