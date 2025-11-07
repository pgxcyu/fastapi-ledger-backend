from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import shutil
from typing import Dict, Iterable, Set, Tuple

from sqlalchemy import and_, exists, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import cleanup_logger as logger
from app.db import models as M
from app.db.db_session import get_db
from app.domains.enums import FileStatus

def _list_all_files(root: Path) -> Set[Path]:
    if not root.exists(): return set()
    return {p for p in root.rglob("*") if p.is_file()}

def _normalize_path(p: str) -> str:
    # 数据库存的是相对路径、URL、或含 /static 前缀的，都规范到相对上传目录
    # 例如 "/static/upload_files/2025/10/a.jpg" → "2025/10/a.jpg"
    p = p.strip()
    p = p.split("?")[0]
    p = p.replace("\\", "/")
    cuts = [
        "/static/upload_files/",
        "static/upload_files/",
        settings.UPLOAD_DIR.strip("/")+ "/",
    ]
    for c in cuts:
        if c in p:
            p = p.split(c, 1)[1]
            break
    return p.lstrip("/")

def _older_than(path: Path, days: int) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return mtime < datetime.now() - timedelta(days=days)
    except FileNotFoundError:
        return False

def _move_to_quarantine(files: Iterable[Path]) -> Tuple[int, int, Dict[Path, str]]:
    """
    将文件移动到隔离区，并返回移动的文件信息
    
    Args:
        files: 要移动的文件路径集合
    
    Returns:
        Tuple[int, int, Dict[Path, str]]: (移动成功数, 跳过数, 原路径到新路径的映射)
    """
    qdir = Path(settings.QUARANTINE_DIR)
    qdir.mkdir(parents=True, exist_ok=True)
    moved, skipped = 0, 0
    path_mapping = {}  # 记录原路径到隔离区路径的映射
    
    for f in files:
        try:
            # 保留完整的相对路径结构，包括年月日文件夹
            if str(f).startswith(str(settings.UPLOAD_DIR)):
                # 获取相对于上传目录的完整路径
                rel = f.relative_to(settings.UPLOAD_DIR)
            else:
                rel = Path(os.path.basename(str(f)))
            
            # 目标路径 = 隔离区目录 + 相对路径
            dst = qdir / rel
            
            # 确保目标目录存在（包括年月日子目录）
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(str(f), str(dst))
            moved += 1
            
            # 记录映射关系，用于后续更新数据库
            # 存储相对于隔离区的路径字符串
            path_mapping[f] = str(rel)
            
        except Exception as e:
            logger.warning("quarantine_move_failed", extra={"path": str(f), "err": str(e)})
            skipped += 1
    
    return moved, skipped, path_mapping

def _purge_quarantine() -> int:
    """清理隔离区内超过 QUARANTINE_LIFETIME_DAYS 的文件"""
    qdir = Path(settings.QUARANTINE_DIR)
    if not qdir.exists(): return 0
    count = 0
    for p in qdir.rglob("*"):
        if p.is_file() and _older_than(p, settings.QUARANTINE_LIFETIME_DAYS):
            try:
                p.unlink()
                count += 1
            except Exception as e:
                logger.warning("quarantine_delete_failed", extra={"path": str(p), "err": str(e)})
    return count

def _collect_file_records(db: Session) -> Dict[str, M.Fileassets]:
    """返回 {相对路径: FileassetsRow} 映射，用于快速比对"""
    mapping: Dict[str, M.Fileassets] = {}
    if not hasattr(M, "Fileassets"): return mapping
    rows = db.execute(select(M.Fileassets)).scalars().all()
    for row in rows:
        rel = _normalize_path(row.filepath)
        if rel: mapping[rel] = row
    logger.info("collect_file_records", extra={"mapping": mapping})
    return mapping

def _find_untracked_fs_files(db: Session) -> Set[Path]:
    """情况①：磁盘有文件，但数据库文件表中无记录"""
    root = Path(settings.UPLOAD_DIR)
    all_fs = _list_all_files(root)
    db_map = _collect_file_records(db)
    untracked = set()
    for f in all_fs:
        # 使用_normalize_path确保路径格式与数据库中的一致
        full_path = str(f)
        rel = _normalize_path(full_path)
        # 如果_normalize_path失败，回退到相对路径
        if not rel:
            rel = str(f.relative_to(root))
        if rel not in db_map and _older_than(f, settings.UNTRACKED_FS_RETENTION_DAYS):
            untracked.add(f)
    return untracked

def _is_link_valid(db: Session, file_row: M.Fileassets) -> bool:
    """业务关联是否有效：
       - business_id 为空/空串 → 无效
       - 若你后续有多表验证，在这里扩展（例如按 row.type 决定去哪个表 exists()）
    """
    bid = (file_row.business_id or "").strip()
    return bool(bid)


def _to_utc(dt: datetime) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _find_unlinked_db_files(db: Session) -> Tuple[Set[M.Fileassets], Set[M.Fileassets]]:
    """情况②：数据库文件表有记录但未关联业务id或文件丢失；"""
    root = Path(settings.UPLOAD_DIR)
    unlinked_exist, unlinked_missing = set(), set()
    if not hasattr(M, "Fileassets"): return unlinked_exist, unlinked_missing

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.UNLINKED_DB_RETENTION_DAYS)

    rows = db.execute(select(M.Fileassets)).scalars().all()
    for row in rows:
        rel = _normalize_path(row.filepath)
        fpath = root / rel if rel else None
        
        # 对于文件丢失的情况，无论是否关联业务id都添加到unlinked_missing
        if not fpath or not fpath.exists():
            unlinked_missing.add(row)
        # 对于文件存在但未关联业务id的情况，添加到unlinked_exist
        elif not _is_link_valid(db, row):
            # 保留期内的临时文件不清
            created_at = _to_utc(getattr(row, "created_at", None))
            if created_at and isinstance(created_at, datetime) and created_at > cutoff:
                continue
            unlinked_exist.add(row)

    return unlinked_exist, unlinked_missing

def cleanup_files(db: Session, dry_run: bool = True) -> dict:
    # 情况①：磁盘有文件，但数据库文件表中无记录
    untracked_fs = _find_untracked_fs_files(db)
    moved_untracked = 0
    if not dry_run and untracked_fs:
        try:
            moved_count, _, _ = _move_to_quarantine(untracked_fs)
            moved_untracked = moved_count
        except Exception as e:
            logger.error("move_untracked_failed", extra={"err": str(e)})
            moved_untracked = 0

    # 情况②：数据库文件表有记录但未关联业务id或文件丢失
    unlinked_exist, unlinked_missing = _find_unlinked_db_files(db)
    moved_unlinked, db_deleted = 0, 0
    if not dry_run:
        # 2a) DB 有记录 + 磁盘存在但未关联业务id → 移隔离区 + 更新 DB 记录
        file_path_map = {}
        to_move = []
        
        # 收集需要移动的文件，并建立行对象与文件路径的映射
        for row in unlinked_exist:
            rel = _normalize_path(row.filepath)
            if rel:
                file_path = Path(settings.UPLOAD_DIR) / rel
                to_move.append(file_path)
                file_path_map[file_path] = row
        
        # 移动文件到隔离区
        if to_move:
            try:
                moved_count, _, path_mapping = _move_to_quarantine(to_move)
                moved_unlinked = moved_count
                
                # 更新数据库记录
                for file_path, row in file_path_map.items():
                    try:
                        if file_path in path_mapping:
                            # 更新文件路径为隔离区路径
                            quarantine_rel_path = path_mapping[file_path]
                            new_filepath = f"static/quarantine/{quarantine_rel_path}"
                            row.filepath = new_filepath
                            
                        # 更新状态为隔离
                        if hasattr(row, "status"):
                            row.status = FileStatus.QUARANTINE
                        
                        db_deleted += 1
                    except Exception as e:
                        logger.warning("db_mark_quarantine_failed", extra={"file_id": getattr(row, "file_id", None), "err": str(e)})
            except Exception as e:
                logger.error("move_unlinked_failed", extra={"err": str(e)})
                moved_unlinked = 0

        # 2b) DB 有记录 + 磁盘缺失 → 文件表记录设为缺失状态
        for row in unlinked_missing:
            try:
                if hasattr(row, "status"):
                    row.status = FileStatus.MISSING
                else:
                    db.delete(row)
                db_deleted += 1
            except Exception as e:
                logger.warning("db_delete_missing_failed", extra={"file_id": getattr(row, "file_id", None), "err": str(e)})
        db.commit()

    purged = 0 if dry_run else _purge_quarantine()
    report = {
        "upload_dir": settings.UPLOAD_DIR,
        "untracked_fs": len(untracked_fs), # 情况①：磁盘有文件，但数据库文件表中无记录
        "unlinked_db_exist": len(unlinked_exist), # 情况②：数据库文件表有记录但未关联业务id
        "unlinked_db_missing": len(unlinked_missing), # 情况②：数据库文件表有记录但文件丢失
        "moved_untracked_fs": moved_untracked if not dry_run else 0,
        "moved_unlinked_db": moved_unlinked if not dry_run else 0,
        "db_deleted": db_deleted if not dry_run else 0,
        "quarantine_purged": purged if not dry_run else 0,
        "dry_run": dry_run,
    }
    logger.info("file_cleanup_report", extra=report)
    return report