import threading
import subprocess
import time
import sys
import os

def run_database_migrations():
    """运行数据库迁移"""
    print("Running database migrations...")
    try:
        result = subprocess.run("python -m alembic upgrade head", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Database migrations completed successfully")
        else:
            print(f"✗ Database migration failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error running migrations: {e}")
        return False
    return True

def run_command(command, description):
    """运行命令并保持运行"""
    print(f"Starting {description}...")
    subprocess.run(command, shell=True)
    print(f"{description} stopped.")

def main():
    try:
        # 首先运行数据库迁移
        if not run_database_migrations():
            print("Failed to run database migrations. Exiting...")
            sys.exit(1)
        
        # 等待一下确保数据库就绪
        time.sleep(2)
        
        # 定义命令
        commands = [
            ("uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload", "FastAPI server"),
            ("celery -A app.core.celery_config worker --loglevel=info -P eventlet", "Celery worker"),
            ("celery -A app.core.celery_config flower --port=5555", "Flower monitoring")
        ]
        
        # 创建并启动线程
        threads = []
        for cmd, desc in commands:
            thread = threading.Thread(target=run_command, args=(cmd, desc), daemon=True)
            threads.append(thread)
            thread.start()
        
        print("\nAll services started successfully!")
        print("FastAPI: http://localhost:9000")
        print("Celery Flower: http://localhost:5555")
        print("\nPress Ctrl+C to stop all services...")
        
        # 保持主线程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping all services...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()