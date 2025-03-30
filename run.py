"""
BGT Boost Tool - 主程序入口

这个工具用于管理BGT提升、取消提升和赎回操作。
"""

import time
import logging
import signal
import sys
from flask import Flask
from app.config import config
from app.api.routes import api
from app.workers.periodic_worker import periodic_worker
from app.workers.task_processor import task_processor
from app.workers.status_worker import status_worker

# 配置日志
logging.basicConfig(
    filename=config.LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 初始化Flask应用
app = Flask(__name__)
app.register_blueprint(api)

def signal_handler(sig, frame):
    """处理退出信号"""
    print("\nShutting down gracefully...", flush=True)
    logging.info("Shutting down gracefully")
    
    # 停止工作器
    periodic_worker.stop()
    task_processor.stop()
    status_worker.stop()
    
    # 退出程序
    sys.exit(0)

if __name__ == "__main__":
    # 重新加载环境变量
    config.reload()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 使用英文表示模式状态
    mode_msg = "[OBSERVATION MODE]" if config.OBSERVATION_MODE else "[EXECUTION MODE]"
    print(f"Starting BGT Boost Tool... {mode_msg}", flush=True)
    logging.info(f"Starting BGT Boost Tool - {mode_msg}")
    
    if config.OBSERVATION_MODE:
        print("⚠️ Running in observation mode, no transactions will be executed", flush=True)
        if not config.PRIVATE_KEY:
            print("📝 No PRIVATE_KEY set, automatically entering observation mode", flush=True)
        logging.warning("Running in observation mode - no transactions will be executed")
    
    # 启动工作器
    status_worker.start()
    periodic_worker.start()
    task_processor.start()

    
    # 启动Flask服务器
    app.run(
        host="0.0.0.0",
        port=config.PORT,
        debug=False,
        use_reloader=False
    )
