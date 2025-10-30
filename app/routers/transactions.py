from datetime import datetime, timezone
import json
from math import e
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.exceptions import BizException
from app.core.idempotency import (
    ensure_idempotency,
    idem_done,
    idem_unlock,
    save_idempotency_response,
)
from app.core.signing import verify_signature
from app.db.models import Fileassets, Transaction, User
from app.db.redis_session import get_redis_client
from app.domains.enums import FileStatus
from app.schemas.basic import PageResult
from app.schemas.response import R
from app.schemas.transactions import (
    TransactionCreate,
    TransactionListQuery,
    TransactionResponse,
)

router = APIRouter()


@router.post("/addRecord", response_model=R, description="添加交易记录")
async def create_transaction(
    request: Request,
    transaction: TransactionCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db),
    idem = Depends(ensure_idempotency),
    redis_client = Depends(get_redis_client),
):
    _, replay = idem
    if replay:
        return replay

    try:
        if transaction.transaction_id:
            # 检查是否已存在
            existing = db.query(Transaction).filter(Transaction.transaction_id == transaction.transaction_id).first()

            if not existing:
                raise BizException(message="交易ID不存在，无法修改")

            if existing.create_userid != current_user.userid:
                raise BizException(message="您没有权限修改此交易记录")

            data = transaction.model_dump(exclude={"filelist", "delFileids"})
            for k, v in data.items():
                setattr(existing, k, v)
            existing.update_userid = current_user.userid
            existing.update_at = datetime.now(timezone.utc)
            db_transaction = existing

            await redis_client.delete(f"transaction:{transaction.transaction_id}")
        else:
            db_transaction = Transaction(
                create_userid=current_user.userid, 
                created_at=datetime.now(timezone.utc),
                **transaction.model_dump(exclude={"filelist", "delFileids"})
            )
            db.add(db_transaction)

        db.commit()
        db.refresh(db_transaction)

        if transaction.filelist:
            for file in transaction.filelist:
                db_filelist = Fileassets(
                    business_id=db_transaction.transaction_id, 
                    filepath=file.filepath, 
                    type='transactions', 
                    userid=current_user.userid,
                    created_at=datetime.now(timezone.utc),
                    status=FileStatus.ACTIVE,
                    category=file.photo_id,
                )
                db.add(db_filelist)

        if transaction.delFileids:
            for fileid in transaction.delFileids.split(','):
                db_filelist = db.query(Fileassets).filter(Fileassets.fileid == fileid).first()
                if db_filelist:
                    db_filelist.status = FileStatus.DELETED
                    db_filelist.update_userid = current_user.userid
                    db_filelist.update_at = datetime.now(timezone.utc)
                    db.add(db_filelist)

        db.commit()

        # 统一返回体（包含业务主键更实用）
        resp_obj = R.ok(message="保存成功", data={
            "transaction_id": db_transaction.transaction_id
        }).model_dump()

        await idem_done(request, resp_obj, status_code=200)
        return resp_obj

    except BizException as e:
        db.rollback()
        await idem_unlock(request)
        raise
    except Exception as e:
        db.rollback()
        await idem_unlock(request)
        raise BizException(message=f"保存失败: {str(e)}")
    

@router.get("/getRecords", response_model=R[PageResult[TransactionResponse]], description="获取交易记录列表", dependencies=[Depends(verify_signature), Depends(RateLimiter(times=5, seconds=60))])
def get_transactions(
    form: TransactionListQuery = Depends(), 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    userid = form.userid or current_user.userid
    
    # 查询交易记录
    query = db.query(Transaction).filter(Transaction.create_userid == userid).order_by(Transaction.created_at.desc())
    
    if form.date_from:
        query = query.filter(Transaction.created_at >= form.date_from)
    if form.date_to:
        query = query.filter(Transaction.created_at <= form.date_to)
    if form.type:
        query = query.filter(Transaction.type == form.type)
    if form.min_amount is not None:
        query = query.filter(Transaction.amount >= form.min_amount)
    if form.max_amount is not None:
        query = query.filter(Transaction.amount <= form.max_amount)
    if form.keyword:
        query = query.filter(Transaction.remark.ilike(f"%{form.keyword}%") | Transaction.type.ilike(f"%{form.keyword}%"))
    
    total = query.count()

    rows = query.offset((form.page - 1) * form.page_size).limit(form.page_size).all()
    
    items = [TransactionResponse.model_validate(t) for t in rows]
    
    page = PageResult[TransactionResponse](page=form.page, page_size=form.page_size, items=items, total=total)

    return R.ok(data=page)


@router.get("/getRecordDetail", response_model=R[TransactionResponse], description="获取交易记录详情")
async def get_transaction_detail(
    transaction_id: str, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    cache_key = f"transaction:{transaction_id}"
    
    # 从Redis缓存中获取交易记录
    cached_transaction = await redis_client.get(cache_key)
    if cached_transaction:
        try:
            transaction_data = json.loads(cached_transaction)
            print('从缓存中获取交易记录:', transaction_data)
            return R.ok(data=TransactionResponse.model_validate(transaction_data))
        except (json.JSONDecodeError, ValueError) as e:
            pass

    transaction = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if transaction is None:
        raise BizException(message="交易记录不存在")

    # 获取关联的文件资产
    fileassets = db.query(Fileassets).filter(Fileassets.business_id == transaction.transaction_id, Fileassets.status == FileStatus.ACTIVE).all()
    transaction.filelist = [{"filepath": fa.filepath, "fileid": fa.fileid, "photo_id": fa.category} for fa in fileassets]

    create_username = db.query(User.username).filter(User.userid == transaction.create_userid).first()
    transaction.create_username = create_username[0] if create_username else ""

    # 将SQLAlchemy模型转换为Pydantic模型
    transaction_response = TransactionResponse.model_validate(transaction)
    
    try:
        await redis_client.setex(cache_key, 1440, transaction_response.model_dump_json())
    except Exception as e:
        pass
    
    return R.ok(data=transaction_response)


@router.post("/deleteRecord", response_model=R, description="删除交易记录")
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    cache_key = f"transaction:{transaction_id}"
    # 从Redis缓存中删除交易记录
    await redis_client.delete(cache_key)
    
    transaction = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if transaction is None:
        raise BizException(message="交易记录不存在")

    if transaction.create_userid != current_user.userid:
        raise BizException(message="您没有权限删除此交易记录")

    # 获取关联的文件资产路径
    fileassets = db.query(Fileassets).filter(Fileassets.business_id == transaction.transaction_id).all()
    
    try:
        db.query(Fileassets).filter(Fileassets.business_id == transaction.transaction_id).delete()
        db.delete(transaction)
        db.commit()
    except Exception as e:
        db.rollback()
        raise BizException(message=f"删除失败: {str(e)}")
    
    # 尝试删除实际文件（在事务提交后执行，避免事务失败）
    for fileasset in fileassets:
        try:
            # 构建完整的文件路径
            # 从URL路径中提取相对路径（去掉'/static/'前缀）
            if fileasset.filepath.startswith('/static/'):
                relative_path = fileasset.filepath[len('/static/'):]
            else:
                relative_path = fileasset.filepath
            
            # 结合项目根目录和静态文件目录构建完整文件系统路径
            full_path = os.path.join(settings.BASE_DIR, "app", "static", relative_path)
            print(f"尝试删除文件: {full_path}")
            
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"成功删除文件: {full_path}")
            else:
                print(f"文件不存在: {full_path}")
        except Exception as e:
            # 记录错误但不影响主要功能
            print(f"删除文件失败: {full_path}, 错误: {str(e)}")
    

    return R.ok(message="交易记录已成功删除")