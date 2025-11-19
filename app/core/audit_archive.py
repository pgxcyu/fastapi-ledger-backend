# app/core/audit_archive.py
from datetime import datetime, timedelta
import gzip
import json
import os
import shutil
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.audit_service import audit_service
from app.core.config import settings
from app.core.deps import get_db
from app.db.models import AuditLog

# settings 已经从 app.core.config 导入

class AuditArchiver:
    """审计数据归档和清理管理器"""
    
    def __init__(self):
        self.archive_dir = getattr(settings, 'AUDIT_ARCHIVE_DIR', 'archives/audit')
        self.retention_days = getattr(settings, 'AUDIT_RETENTION_DAYS', 365)  # 保留天数
        self.archive_after_days = getattr(settings, 'AUDIT_ARCHIVE_AFTER_DAYS', 90)  # 归档天数
        self.compression_enabled = getattr(settings, 'AUDIT_COMPRESSION_ENABLED', True)
        
        # 确保归档目录存在
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def archive_old_logs(self, db: Session, days: Optional[int] = None) -> dict:
        """归档旧的审计日志"""
        if days is None:
            days = self.archive_after_days
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 查询需要归档的日志
        logs_to_archive = db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).all()
        
        if not logs_to_archive:
            return {
                "archived_count": 0,
                "message": f"没有需要归档的日志（{days}天前）"
            }
        
        # 按月份分组归档
        archived_groups = {}
        for log in logs_to_archive:
            month_key = log.created_at.strftime("%Y-%m")
            if month_key not in archived_groups:
                archived_groups[month_key] = []
            archived_groups[month_key].append(log)
        
        total_archived = 0
        archive_files = []
        
        # 为每个月份创建归档文件
        for month, logs in archived_groups.items():
            archive_filename = f"audit_logs_{month}.json"
            if self.compression_enabled:
                archive_filename += ".gz"
            
            archive_path = os.path.join(self.archive_dir, archive_filename)
            
            # 转换日志为字典格式
            log_data = []
            for log in logs:
                log_dict = {
                    "audit_id": log.audit_id,
                    "user_id": log.user_id,
                    "user_name": log.user_name,
                    "session_id": log.session_id,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "request_method": log.request_method,
                    "request_path": log.request_path,
                    "operation_type": log.operation_type,
                    "operation_module": log.operation_module,
                    "operation_description": log.operation_description,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "resource_name": log.resource_name,
                    "audit_level": log.audit_level,
                    "risk_level": log.risk_level,
                    "sensitive_flag": log.sensitive_flag,
                    "operation_result": log.operation_result,
                    "error_message": log.error_message,
                    "before_data": log.before_data,
                    "after_data": log.after_data,
                    "business_context": log.business_context,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "updated_at": log.updated_at.isoformat() if log.updated_at else None
                }
                log_data.append(log_dict)
            
            # 写入归档文件
            if self.compression_enabled:
                with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
                    json.dump(log_data, f, ensure_ascii=False, indent=2)
            else:
                with open(archive_path, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            archive_files.append(archive_filename)
            total_archived += len(logs)
            
            # 从数据库中删除已归档的日志
            log_ids = [log.audit_id for log in logs]
            db.query(AuditLog).filter(AuditLog.audit_id.in_(log_ids)).delete()
        
        db.commit()
        
        return {
            "archived_count": total_archived,
            "archive_files": archive_files,
            "message": f"成功归档 {total_archived} 条审计日志"
        }
    
    def cleanup_old_archives(self, days: Optional[int] = None) -> dict:
        """清理旧的归档文件"""
        if days is None:
            days = self.retention_days
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_files = []
        
        # 遍历归档目录
        for filename in os.listdir(self.archive_dir):
            file_path = os.path.join(self.archive_dir, filename)
            
            if os.path.isfile(file_path):
                # 获取文件修改时间
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_mtime < cutoff_date:
                    try:
                        os.remove(file_path)
                        deleted_files.append(filename)
                    except Exception as e:
                        print(f"删除归档文件失败 {filename}: {e}")
        
        return {
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "message": f"清理了 {len(deleted_files)} 个过期归档文件"
        }
    
    def get_archive_info(self) -> dict:
        """获取归档信息"""
        archive_files = []
        total_size = 0
        
        for filename in os.listdir(self.archive_dir):
            file_path = os.path.join(self.archive_dir, filename)
            
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                archive_files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
                total_size += stat.st_size
        
        return {
            "archive_directory": self.archive_dir,
            "total_files": len(archive_files),
            "total_size": total_size,
            "files": sorted(archive_files, key=lambda x: x['filename'], reverse=True),
            "retention_days": self.retention_days,
            "archive_after_days": self.archive_after_days
        }
    
    def restore_from_archive(self, archive_filename: str, db: Session) -> dict:
        """从归档文件恢复审计日志"""
        archive_path = os.path.join(self.archive_dir, archive_filename)
        
        if not os.path.exists(archive_path):
            return {
                "restored_count": 0,
                "error": f"归档文件不存在: {archive_filename}"
            }
        
        try:
            # 读取归档文件
            if archive_filename.endswith('.gz'):
                with gzip.open(archive_path, 'rt', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                with open(archive_path, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            
            restored_count = 0
            for log_dict in log_data:
                # 检查是否已存在
                existing = db.query(AuditLog).filter(
                    AuditLog.audit_id == log_dict['audit_id']
                ).first()
                
                if not existing:
                    # 使用audit_service创建AuditLog对象
                    audit_log = audit_service.create_audit_log_from_data(log_dict)
                    db.add(audit_log)
                    restored_count += 1
            
            db.commit()
            
            return {
                "restored_count": restored_count,
                "message": f"成功从 {archive_filename} 恢复 {restored_count} 条审计日志"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "restored_count": 0,
                "error": f"恢复归档文件失败: {str(e)}"
            }

def archive_audit_log(db: Session, days: int = 90) -> dict:
    """归档审计日志的便捷函数"""
    return audit_archiver.archive_old_logs(db, days)

def cleanup_audit_archives(days: int = None) -> dict:
    """清理审计归档文件的便捷函数"""
    return audit_archiver.cleanup_old_archives(days)

def get_audit_archive_info() -> dict:
    """获取审计归档信息的便捷函数"""
    return audit_archiver.get_archive_info()

def restore_audit_archive(archive_filename: str, db: Session) -> dict:
    """从归档恢复审计日志的便捷函数"""
    return audit_archiver.restore_from_archive(archive_filename, db)

# 全局归档器实例
audit_archiver = AuditArchiver()

def schedule_archive_cleanup():
    """定时任务：归档和清理审计数据"""
    from app.core.deps import get_db
    
    db = next(get_db())
    try:
        # 归档旧日志
        archive_result = audit_archiver.archive_old_logs(db)
        print(f"审计归档结果: {archive_result}")
        
        # 清理过期归档文件
        cleanup_result = audit_archiver.cleanup_old_archives()
        print(f"归档清理结果: {cleanup_result}")
        
    finally:
        db.close()