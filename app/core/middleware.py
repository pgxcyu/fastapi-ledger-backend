import time
import uuid
from app.core.logging import middleware_logger, auth_logger, access_logger

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            resp = await call_next(request)
            # 基础安全头
            resp.headers.setdefault("X-Content-Type-Options", "nosniff")
            resp.headers.setdefault("X-Frame-Options", "DENY")
            resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            resp.headers.setdefault("Permissions-Policy",
                "geolocation=(), microphone=(), camera=()")
            # 如果全站 HTTPS，可开启：
            resp.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
            # 修改CSP配置以允许Swagger UI加载必要的外部资源
            resp.headers.setdefault("Content-Security-Policy",
                "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "img-src 'self' https://fastapi.tiangolo.com; "
                "font-src 'self' data:; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
            )
            return resp
        except Exception as e:
            middleware_logger.error(f"Error in SecurityHeadersMiddleware: {str(e)}")
            raise


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """认证中间件 - 仅从JWT令牌中提取用户ID并设置到request.state"""
    async def dispatch(self, request: Request, call_next):
        try:
            token = None
            
            # 从Authorization头中提取JWT令牌
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
            
            # 如果找到了令牌，尝试解码它
            if token:
                try:
                    # 解码JWT令牌
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    user_id = payload.get("sub")
                    sid = payload.get("sid")

                    if user_id: request.state.user_id = user_id
                    if sid: request.state.sid = sid
                    auth_logger.debug(f"Authenticated user: {user_id}")
                except JWTError as e:
                    # 令牌无效，忽略错误
                    auth_logger.debug(f"Invalid token: {str(e)}")
            
            # 继续处理请求
            response = await call_next(request)
            return response
        except Exception as e:
            middleware_logger.error(f"Error in AuthenticationMiddleware: {str(e)}")
            raise


from app.core.request_ctx import set_request_id, set_user_context

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
            set_request_id(rid)

            start = time.perf_counter()
            response = await call_next(request)
            elapsed = int((time.perf_counter() - start) * 1000)
            response.headers["X-Request-ID"] = rid

            user_id = getattr(request.state, "user_id", "")
            sid = getattr(request.state, "sid", "")
            set_user_context(user_id, sid)

            ctx = {
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed,
                "user_id": user_id,
                "sid": sid,
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent", ""),
            }

            access_logger.bind(**ctx).info("request")
            
            return response
        except Exception as e:
            middleware_logger.error(f"Error in RequestContextMiddleware: {str(e)}")
            raise
