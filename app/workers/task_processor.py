import time
import logging
import threading
from app.core.unboost import unboost_manager
from app.core.redeem import redeem_manager
from app.config import config
from app.db.database import db
from app.db.models import TaskType, TaskStatus

class TaskProcessor:
    """任务处理器"""
    
    def __init__(self, interval=None):
        """
        初始化任务处理器
        
        Args:
            interval: 检查间隔（秒）
        """
        self.unboost_manager = unboost_manager
        self.redeem_manager = redeem_manager
        self.interval = interval or config.INTERVAL
        self.enabled = True
        self._thread = None
        self._stop_event = threading.Event()
    
    def toggle(self):
        """
        切换处理器状态
        
        Returns:
            bool: 新的状态
        """
        self.enabled = not self.enabled
        logging.info(f"Task processor {'enabled' if self.enabled else 'disabled'}")
        return self.enabled
    
    def start(self):
        """启动处理器线程"""
        if self._thread is not None and self._thread.is_alive():
            logging.warning("Task processor already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        mode_msg = "OBSERVATION MODE" if config.OBSERVATION_MODE else "EXECUTION MODE"
        logging.info(f"Task processor started ({mode_msg})")
        print(f"Task processor started ({mode_msg})", flush=True)
    
    def stop(self):
        """停止处理器线程"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        logging.info("Task processor stopped")
    
    def _run(self):
        """运行循环"""
        while not self._stop_event.is_set():
            if self.enabled:
                try:
                    self._process_tasks()
                except Exception as e:
                    logging.error(f"Error in task processor: {e}")
                    print(f"❌ Error in task processor: {e}", flush=True)
            
            # 使用事件等待，允许提前停止
            self._stop_event.wait(timeout=self.interval)
    
    def _process_tasks(self):
        """处理各种类型的任务"""
        # 观察模式下只显示任务状态，不执行操作
        if config.OBSERVATION_MODE:
            self._observe_tasks()
            return
            
        # 处理每种类型的任务
        self.unboost_manager.process_pending_tasks()  # 处理待处理的unboost任务
        self.unboost_manager.process_queued_tasks()   # 处理已排队的unboost任务
        self.redeem_manager.process_active_tasks()    # 处理活跃的unboost任务，准备赎回
    
    def _observe_tasks(self):
        """观察模式下，只显示任务状态但不执行操作"""
        # 获取不同状态的任务
        pending_tasks = db.get_pending_tasks(task_type=TaskType.UNBOOST, status=TaskStatus.PENDING)
        queued_tasks = db.get_pending_tasks(task_type=TaskType.UNBOOST, status=TaskStatus.QUEUED)
        active_tasks = db.get_pending_tasks(task_type=TaskType.UNBOOST, status=TaskStatus.ACTIVE)
        
        # 报告但不执行
        if pending_tasks:
            task_ids = [task["task_id"] for task in pending_tasks]
            logging.info(f"[OBSERVATION] Found {len(pending_tasks)} pending unboost tasks: {task_ids}")
            print(f"[OBSERVATION] Found {len(pending_tasks)} pending unboost tasks: {task_ids}", flush=True)
        
        if queued_tasks:
            task_ids = [task["task_id"] for task in queued_tasks]
            drop_boost_ready = self.unboost_manager.can_drop_boost()
            status = "ready to execute" if drop_boost_ready else "conditions not met"
            logging.info(f"[OBSERVATION] Found {len(queued_tasks)} queued unboost tasks: {task_ids}, status: {status}")
            print(f"[OBSERVATION] Found {len(queued_tasks)} queued unboost tasks: {task_ids}, status: {status}", flush=True)
        
        if active_tasks:
            task_ids = [task["task_id"] for task in active_tasks]
            logging.info(f"[OBSERVATION] Found {len(active_tasks)} active unboost tasks ready for redeem: {task_ids}")
            print(f"[OBSERVATION] Found {len(active_tasks)} active unboost tasks ready for redeem: {task_ids}", flush=True)

# 创建单例实例
task_processor = TaskProcessor() 