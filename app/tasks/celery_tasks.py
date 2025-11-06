from app.core.celery_config import celery_app
from app.db.session import SessionLocal
from app.tasks.cleanup import cleanup_files as cleanup_files_func
from app.tasks.export_reporter import export_transactions_by_user_func

@celery_app.task(bind=True, name='app.tasks.celery_tasks.cleanup_files_task')
def cleanup_files_task(self, dry_run: bool = True):
    db = SessionLocal()
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0})
        result = cleanup_files_func(db, dry_run=dry_run)
        self.update_state(state='PROGRESS', meta={'progress': 100})
        return result
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
    finally:
        db.close()


@celery_app.task(bind=True,name='app.tasks.celery_tasks.export_transactions_by_user_task')
def export_transactions_by_user_task(self, user_id: str):
    db = SessionLocal()
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0})
        result = export_transactions_by_user_func(db, user_id=user_id)
        self.update_state(state='PROGRESS', meta={'progress': 100})
        return result
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
    finally:
        db.close()