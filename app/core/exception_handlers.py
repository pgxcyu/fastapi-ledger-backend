# app/core/exception_handlers.py
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.datastructures import MutableHeaders

from app.core.exceptions import BizException
from app.core.logging import logger
from app.schemas.response import R

def _format_pydantic_errors(exc) -> list[dict]:
    """
    把 Pydantic/FastAPI 的 errors() 结构，转成更易读的数组：
    [{'loc':'body.amount', 'msg':'Input should be greater than 0', 'type':'greater_than'}]
    """
    items = []
    for e in exc.errors():
        loc = ".".join(map(str, e.get("loc", [])))  # ('body','amount') -> 'body.amount'
        items.append({
            "loc": loc,
            "msg": e.get("msg"),
            "type": e.get("type"),
        })
    return items


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Exception: {exc.detail}")
    response = JSONResponse(
        status_code=exc.status_code,
        content=R.fail(code=exc.status_code, message=str(exc.detail)).model_dump()
    )
    # 如果是 401 Unauthorized，可能需要保留 headers
    if exc.headers:
        response.headers.update(exc.headers)
    return response

async def biz_exception_handler(request: Request, exc: BizException):
    logger.error(f"Business Exception: {exc}")
    
    response = JSONResponse(
        status_code=200,
        content=R.fail(code=exc.code, message=exc.message).model_dump()
    )
    # 业务异常可能需要自定义 headers
    if exc.headers:
        response.headers.update(exc.headers)
    return response

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request Validation Error: {exc.errors()}")
    response = JSONResponse(
        status_code=422,
        content=R.fail(code=422, message="参数校验错误", data={"errors": _format_pydantic_errors(exc)}).model_dump()
    )
    return response

async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.error(f"Pydantic Validation Error: {exc.errors()}")
    # 特别检查是否是response_model验证错误
    response = JSONResponse(
        status_code=422,
        content=R.fail(code=422, message="参数校验错误", data={"errors": _format_pydantic_errors(exc)}).model_dump()
    )
    return response

async def unhandled_exception_handler(request: Request, exc: Exception):
    # 兜底错误，记录日志并返回 500
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content=R.fail(code=500, message="服务器内部错误").model_dump()
    )
    return response