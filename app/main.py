import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_limiter import FastAPILimiter
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exception_handlers import (
    biz_exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import BizException
from app.core.logging import setup_logging
from app.core.middleware import (
    AuthenticationMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.audit_middleware import AuditMiddleware
from app.db.db_session import init_db
from app.db.redis_session import close_redis, init_redis
from app.routers import auth, basic, system, transactions, videoserver

app = FastAPI(title="FastAPI Ledger (Kickoff)")

setup_logging()

# CORS（前端联调方便）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["Authorization","Content-Type","Idempotency-Key",'X-Key-Id', 'X-Timestamp', 'X-Nonce', 'X-Body-Hash', 'X-Signature'],
)

# app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RequestContextMiddleware)
# app.add_middleware(AuditMiddleware)

app.add_exception_handler(BizException, biz_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

def setup_prometheus():
    print("[DEBUG] 正在配置 Prometheus 监控...")
    try:
        # 创建简单的 Instrumentator 实例
        instrumentator = Instrumentator(should_group_status_codes=True)
        # 添加基本指标
        instrumentator.add(metrics.latency())
        # 为应用添加指标收集
        instrumentator.instrument(app)
        # 暴露 /metrics 端点
        instrumentator.expose(app, endpoint="/metrics")
        print("[DEBUG] Prometheus 监控配置成功，/metrics 端点已启用")
    except Exception as e:
        print(f"[ERROR] Prometheus 监控配置失败: {e}")
        import traceback
        traceback.print_exc()
    
# setup_prometheus()

@app.on_event("startup")
async def startup_event():
    init_db()
    
    # 尝试初始化Redis和FastAPILimiter，但如果失败不要阻止应用启动
    try:
        redis_client = await init_redis()
        await FastAPILimiter.init(redis_client)
        app.state.redis = redis_client
    except Exception as e:
        print(f"Warning: Failed to initialize Redis or FastAPILimiter: {e}")
    
    # 文件清理任务已迁移到Celery Beat管理，不再使用APScheduler

@app.on_event("shutdown")
async def shutdown_event():
    await FastAPILimiter.close()
    await close_redis()


# @app.get("/docs", include_in_schema=False)
# async def custom_swagger_ui_html():
#     return get_swagger_ui_html(
#         openapi_url=app.openapi_url,
#         title=app.title + " - Swagger UI",
#         oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
#         swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
#         swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
#     )


# @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
# async def swagger_ui_redirect():
#     return get_swagger_ui_oauth2_redirect_html()


# @app.get("/redoc", include_in_schema=False)
# async def redoc_html():
#     return get_redoc_html(
#         openapi_url=app.openapi_url,
#         title=app.title + " - ReDoc",
#         redoc_js_url="https://unpkg.com/redoc@next/bundles/redoc.standalone.js",
#     )


STATIC_DIR = os.path.join("static")   # 指向 /static
os.makedirs(STATIC_DIR, exist_ok=True)   # 没有就创建（CI 下也安全）
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(basic.router, prefix="/basic", tags=["basic"])
app.include_router(videoserver.router, prefix="/videoserver", tags=["videoserver"])
app.include_router(system.router, prefix="/system", tags=["system"])
