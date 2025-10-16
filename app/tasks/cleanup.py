import os, shutil, logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Set, Tuple, Dict

from sqlalchemy.orm import Session
from sqlalchemy import select, exists, and_
from app.core.config import settings
from app.db.session import get_db
from app.db import models as M
from app.domains.enums import FileStatus

logger = logging.getLogger("cleanup")

def _list_all_files(root: Path) -> Set[Path]:
    if not root.exists(): return set()
    return {p for p in root.rglob("*") if p.is_file()}

def _normalize_path(p: str) -> str:
    # 数据库存的是相对路径、URL、或含 /static 前缀的，都规范到相对上传目录
    # 例如 "app/static/upload_files/2025/10/a.jpg" → "2025/10/a.jpg"
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

def _move_to_quarantine(files: Iterable[Path]) -> Tuple[int, int]:
    qdir = Path(settings.QUARANTINE_DIR)
    qdir.mkdir(parents=True, exist_ok=True)
    moved, skipped = 0, 0
    for f in files:
        try:
            rel = f.relative_to(settings.UPLOAD_DIR) if str(f).startswith(settings.UPLOAD_DIR) else f.name
        except Exception:
            rel = f.name
        dst = qdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dst))
        moved += 1
    return moved, skipped

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
    return mapping

def _find_untracked_fs_files(db: Session) -> Set[Path]:
    """情况①：磁盘有，但 DB 无记录"""
    root = Path(settings.UPLOAD_DIR)
    all_fs = _list_all_files(root)
    db_map = _collect_file_records(db)
    untracked = set()
    for f in all_fs:
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

def _find_unlinked_db_files(db: Session) -> Tuple[Set[M.Fileassets], Set[M.Fileassets]]:
    """情况②：DB 有记录但无关联；细分：磁盘存在/磁盘已丢失"""
    root = Path(settings.UPLOAD_DIR)
    unlinked_exist, unlinked_missing = set(), set()
    if not hasattr(M, "Fileassets"): return unlinked_exist, unlinked_missing

    rows = db.execute(select(M.Fileassets)).scalars().all()
    for row in rows:
        # 仅清理“老的”未关联
        if _is_link_valid(db, row): 
            continue
        # 保留期内的临时文件不清
        created_at = getattr(row, "created_at", None)
        if created_at and isinstance(created_at, datetime):
            if created_at > datetime.now() - timedelta(days=settings.UNLINKED_DB_RETENTION_DAYS):
                continue

        rel = _normalize_path(row.filepath)
        fpath = root / rel if rel else None
        if fpath and fpath.exists():
            unlinked_exist.add(row)
        else:
            unlinked_missing.add(row)

    return unlinked_exist, unlinked_missing

def cleanup_files(db: Session, dry_run: bool = True) -> dict:
    # 情况①：磁盘未入库
    untracked_fs = _find_untracked_fs_files(db)
    moved_untracked = 0
    if not dry_run and untracked_fs:
        moved_untracked = _move_to_quarantine(untracked_fs)

    # 情况②：DB 未关联
    unlinked_exist, unlinked_missing = _find_unlinked_db_files(db)
    moved_unlinked, db_deleted = 0, 0
    if not dry_run:
        # 2a) DB 有记录 + 磁盘存在 → 移隔离区 + 删除/标记 DB 记录
        to_move = []
        for row in unlinked_exist:
            rel = _normalize_path(row.filepath)
            if rel:
                to_move.append(Path(settings.UPLOAD_DIR) / rel)
            # 软删或硬删（按你的需求）
            try:
                if hasattr(row, "status"):
                    row.status = FileStatus.QUARANTINE
                else:
                    db.delete(row)
                db_deleted += 1
            except Exception as e:
                logger.warning("db_mark_quarantine_failed", extra={"file_id": getattr(row, "file_id", None), "err": str(e)})
        if to_move:
            moved_unlinked = _move_to_quarantine(to_move)

        # 2b) DB 有记录 + 磁盘缺失 → 只删 DB
        for row in unlinked_missing:
            try:
                if hasattr(row, "status"):
                    row.status = FileStatus.DELETED
                else:
                    db.delete(row)
                db_deleted += 1
            except Exception as e:
                logger.warning("db_delete_missing_failed", extra={"file_id": getattr(row, "file_id", None), "err": str(e)})
        db.commit()

    purged = 0 if dry_run else _purge_quarantine()
    report = {
        "upload_dir": settings.UPLOAD_DIR,
        "untracked_fs": len(untracked_fs),
        "unlinked_db_exist": len(unlinked_exist),
        "unlinked_db_missing": len(unlinked_missing),
        "moved_untracked_fs": moved_untracked if not dry_run else 0,
        "moved_unlinked_db": moved_unlinked if not dry_run else 0,
        "db_deleted": db_deleted if not dry_run else 0,
        "quarantine_purged": purged if not dry_run else 0,
        "dry_run": dry_run,
    }
    logger.info("file_cleanup_report", extra=report)
    return report