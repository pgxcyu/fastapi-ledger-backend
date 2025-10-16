# app/core/exception_handlers.py
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.exceptions import BizException
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
    return JSONResponse(
        status_code=exc.status_code,
        content=R.fail(code=exc.status_code, message=str(exc.detail)).model_dump()
    )

async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(
        status_code=200,
        content=R.fail(code=exc.code, message=exc.message).model_dump()
    )

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=200,
        content=R.fail(code=422, message="参数校验错误", data={"errors": _format_pydantic_errors(exc)}).model_dump()
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=200,
        content=R.fail(code=422, message="参数校验错误", data={"errors": _format_pydantic_errors(exc)}).model_dump()
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    # 兜底错误，记录日志并返回 500
    return JSONResponse(
        status_code=200,
        content=R.fail(code=500, message="服务器内部错误").model_dump()
    )
