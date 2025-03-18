import time
import logging
import threading
import json
from app.core.boost import boost_manager
from app.core.unboost import unboost_manager
from app.blockchain.web3_client import web3_client
from app.config import config

class StatusWorker:
    """BGT状态监控Worker"""
    
    def __init__(self, interval=None):
        """
        初始化状态监控Worker
        
        Args:
            interval: 检查间隔（秒）
        """
        self.interval = interval or config.STATUS_INTERVAL or 30
        self.enabled = True
        self._thread = None
        self._stop_event = threading.Event()
        self._status_cache = {}
        self._lock = threading.Lock()
    
    def toggle(self):
        """
        切换worker状态
        
        Returns:
            bool: 新的状态
        """
        self.enabled = not self.enabled
        logging.info(f"Status worker {'enabled' if self.enabled else 'disabled'}")
        return self.enabled
    
    def start(self):
        """启动worker线程"""
        if self._thread is not None and self._thread.is_alive():
            logging.warning("Status worker already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        mode_msg = "OBSERVATION MODE" if config.OBSERVATION_MODE else "EXECUTION MODE"
        logging.info(f"Status worker started ({mode_msg})")
        print(f"Status worker started ({mode_msg})", flush=True)
    
    def stop(self):
        """停止worker线程"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        logging.info("Status worker stopped")
    
    def _run(self):
        """运行循环"""
        while not self._stop_event.is_set():
            if self.enabled:
                try:
                    self._update_status()
                except Exception as e:
                    logging.error(f"Error in status worker: {e}")
                    print(f"❌ Error in status worker: {e}", flush=True)
            
            # 使用事件等待，允许提前停止
            self._stop_event.wait(timeout=self.interval)
    
    def _update_status(self):
        """获取并更新BGT状态信息"""
        # 从boost_manager获取基础BGT信息
        bgt_info = boost_manager.get_bgt_info()
        
        # 从unboost_manager获取queue drop信息
        queued_drop_info = unboost_manager.get_queued_drop_info()
        
        # 合并信息
        status = {
            **bgt_info,
            **queued_drop_info,
            "last_update": int(time.time()),
            "block_number": web3_client.get_block_number()
        }
        
        # 更新缓存
        with self._lock:
            self._status_cache = status
        
        logging.debug(f"Updated BGT status: {json.dumps(status)}")
    
    def get_status(self):
        """
        获取当前状态信息
        
        Returns:
            dict: 包含BGT状态信息的字典
        """
        with self._lock:
            status = self._status_cache.copy()
        
        # 如果缓存为空，立即获取一次
        if not status:
            try:
                self._update_status()
                with self._lock:
                    status = self._status_cache.copy()
            except Exception as e:
                logging.error(f"Failed to get initial status: {e}")
        
        return status

# 创建单例实例
status_worker = StatusWorker() 