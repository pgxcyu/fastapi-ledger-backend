import threading
import subprocess
import time
import sys

def run_command(command, description):
    """运行命令并保持运行"""
    print(f"Starting {description}...")
    subprocess.run(command, shell=True)
    print(f"{description} stopped.")

def main():
    try:
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