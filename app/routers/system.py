import asyncio
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.redis_session import get_redis_client
from app.db.session import get_db
from app.schemas.response import R
from app.core.deps import get_current_user
from app.core.request_ctx import get_request_id, get_user_context

router = APIRouter(tags=["system"])

# --- 内部检查 ---
async def _check_db(db: Session, timeout: float = 1.5) -> tuple[bool, str | None]:
    try:
        # 同步 Session 放线程池里跑，设置超时
        def _run():
            db.execute(text("SELECT 1"))
        await asyncio.wait_for(asyncio.to_thread(_run), timeout=timeout)
        return True, None
    except Exception as e:
        return False, str(e)

async def _check_redis(timeout: float = 1.0) -> tuple[bool, str | None]:
    try:
        r = get_redis_client()
        await asyncio.wait_for(r.ping(), timeout=timeout)
        return True, None
    except Exception as e:
        return False, str(e)

# --- 存活：不依赖外部 ---
@router.get("/healthz", summary="Liveness probe (no deps)")
async def healthz():
    return {
        "ok": True,
        "ts": int(time.time() * 1000)
    }

# --- 就绪：依赖外部 ---
@router.get("/readyz", summary="Readiness probe (check DB & Redis)")
async def readyz(db: Session = Depends(get_db)):
    t0 = time.time()
    db_ok, db_err = await _check_db(db)
    redis_ok, redis_err = await _check_redis()
    ok = db_ok and redis_ok

    payload = {
        "ok": ok,
        "ts": int(time.time() * 1000),
        "latency_ms": int((time.time() - t0) * 1000),
        "checks": {
            "db": {"ok": db_ok, "err": db_err},
            "redis": {"ok": redis_ok, "err": redis_err},
        },
    }
    if ok:
        return R.ok(data=payload)
    return JSONResponse(
        status_code=503,
        content={"code": 503, "message": "not ready", "data": payload}
    )

@router.get("/_whoami", summary="Get current user info", dependencies=[Depends(get_current_user)])
async def whoami():
    rid = get_request_id()
    uid, sid = get_user_context()
    return R.ok(data={
        "request_id": rid,
        "user_id": uid,
        "sid": sid,
    })