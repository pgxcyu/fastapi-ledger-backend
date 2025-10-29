from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_limiter import FastAPILimiter
from pydantic import ValidationError
import redis.asyncio as redis
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exception_handlers import (
    biz_exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import BizException
from app.core.middleware import (
    AuthenticationMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.logging import setup_logging
from app.db.init_db import init_db
from app.db.redis_session import close_redis, init_redis
from app.db.session import get_db
from app.routers import auth, basic, transactions, videoserver
from app.schemas.response import R
from app.tasks.cleanup import cleanup_files


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

app.add_exception_handler(BizException, biz_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

scheduler = AsyncIOScheduler()

async def run_cleanup_job(dry_run: bool = False):
    db = next(get_db())
    try:
        cleanup_files(db, dry_run=dry_run)
    finally:
        db.close()

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
    
    scheduler.add_job(
        run_cleanup_job,
        CronTrigger.from_crontab(settings.CLEANUP_CRON),
        id="cleanup_files",
        name="清理孤立文件",
        replace_existing=True,
    )
    # scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    await FastAPILimiter.close()
    await close_redis()

    if scheduler.running:
        scheduler.shutdown()


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


app.mount("/static", StaticFiles(directory="app/static"), name="static")


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(basic.router, prefix="/basic", tags=["basic"])
app.include_router(videoserver.router, prefix="/videoserver", tags=["videoserver"])