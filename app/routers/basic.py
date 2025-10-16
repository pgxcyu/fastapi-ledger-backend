from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends, Query
from typing import List, Dict, Any
import os
import uuid
import shutil
import hashlib
from datetime import datetime
from app.db.models import User
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.schemas.response import R
from fastapi_limiter.depends import RateLimiter

from app.tasks.cleanup import cleanup_files

# 创建路由实例
router = APIRouter()

# 配置项
STATIC_ROOT = os.path.join("app", "static")              # 统一静态根
UPLOAD_PATH = "upload_files"
UPLOAD_DIR = os.path.join(STATIC_ROOT, UPLOAD_PATH)
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp"
}
ALLOWED_FILE_TYPES = {
    *ALLOWED_IMAGE_TYPES,
    "application/pdf", "application/msword", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "application/json"
}

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _safe_join(root: str, *paths: str) -> str:
    full = os.path.normpath(os.path.join(root, *paths))
    root_norm = os.path.normpath(os.path.abspath(root))
    full_abs = os.path.normpath(os.path.abspath(full))
    if not (full_abs == root_norm or full_abs.startswith(root_norm + os.sep)):
        raise ValueError("illegal path")
    return full_abs

def _today_subdir() -> str:
    d = datetime.now()
    # 例如：YYYY/MM/DD
    return os.path.join(f"{d:%Y}", f"{d:%m}", f"{d:%d}")

def _sha256_of_fileobj(fobj, *, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    pos = fobj.tell()
    while True:
        buf = fobj.read(chunk)
        if not buf:
            break
        h.update(buf)
    fobj.seek(pos)
    return h.hexdigest()

@router.post("/upload_file", response_model=R, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def upload_file(
    files: List[UploadFile] = File(...),
    allow_only_images: bool = False,  # 可选参数，是否只允许上传图片
    current_user: User = Depends(get_current_user),
):
    _ensure_dir(UPLOAD_DIR)
    rel_base_dir = _today_subdir()
    abs_base_dir = _safe_join(UPLOAD_DIR, rel_base_dir)
    _ensure_dir(abs_base_dir)
    
    # 初始化结果
    result = {
        "success": [],
        "failed": []
    }
    
    # 选择允许的文件类型
    allowed_types = ALLOWED_IMAGE_TYPES if allow_only_images else ALLOWED_FILE_TYPES
    
    for file in files:
        try:
            # 处理空文件
            if not file or not file.filename:
                result["failed"].append({
                    "filename": "",
                    "reason": "No file sent or empty filename"
                })
                continue
            
            # 获取文件类型
            content_type = file.content_type
            
            # 文件类型验证
            if not content_type or content_type not in allowed_types:
                result["failed"].append({
                    "filename": file.filename,
                    "reason": f"File type {content_type} not allowed"
                })
                continue
            
            # 文件大小验证
            file.file.seek(0, 2)  # 移动到文件末尾
            file_size = file.file.tell()
            file.file.seek(0)  # 重置文件指针到开头
            
            if file_size > MAX_FILE_SIZE_BYTES:
                result["failed"].append({
                    "filename": file.filename,
                    "reason": f"File size exceeds {MAX_FILE_SIZE_MB}MB limit"
                })
                continue
            

            # sha256_hash = _sha256_of_fileobj(file.file)
            
            # 生成唯一文件名（保留后缀）
            orig_ext = os.path.splitext(file.filename)[1]
            unique_name = f"{uuid.uuid4().hex}{orig_ext.lower()}"
            rel_path = os.path.join(rel_base_dir, unique_name)
            abs_path = _safe_join(UPLOAD_DIR, rel_path)

            # 原子写入（写到 .part 再替换）
            tmp_path = abs_path + ".part"
            with open(tmp_path, "wb") as out:
                shutil.copyfileobj(file.file, out)
            os.replace(tmp_path, abs_path)
            
            # 构建URL
            file_url = f"/static/upload_files/{rel_path.replace(os.sep, '/')}"
            
            # 生成唯一文件名，避免覆盖 
            # file_extension = os.path.splitext(file.filename)[1]
            # unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            # file_path = os.path.join(UPLOAD_DIR, unique_filename) 
            
            # # 保存文件 
            # with open(file_path, "wb") as buffer:
            #     shutil.copyfileobj(file.file, buffer) 
                
            # # 构建访问URL
            # file_url = f"/static/upload_files/{unique_filename}"
            
            # 记录成功上传的文件信息
            result["success"].append({
                "filename": unique_name,
                "url": file_url,
                "content_type": content_type,
                "size": file_size
            })
            
        except Exception as e:
            # 记录失败的文件信息
            result["failed"].append({
                "filename": file.filename if file and file.filename else "",
                "reason": str(e)
            })
        finally:
            # 确保文件被关闭
            try:
                file.file.close()
            except:
                pass
    
    # 如果所有文件都失败了，可以考虑抛出异常
    if not result["success"] and result["failed"]:
        return R.fail(message="All files failed to upload", data=result)
    
    return R.ok(message="Files uploaded successfully", data=result)


@router.post("/ops/cleanup-orphans", response_model=R[dict])
def cleanup_orphans_api(
    dry_run: bool = Query(True, description="是否仅模拟运行，设置为False才会实际移动文件到隔离区") ,
    db: Session = Depends(get_db),
    # current_user=Depends(get_current_user)  # + 权限校验
): 
    report = cleanup_files(db, dry_run=dry_run)
    return R.ok(data=report, message="已完成文件清理" if not dry_run else "模拟运行完成，未实际删除文件")