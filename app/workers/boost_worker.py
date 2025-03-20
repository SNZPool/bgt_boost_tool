import time
import logging
import threading
from app.core.boost import boost_manager
from app.core.bgt_staker import bgt_staker_manager
from app.config import config

class BoostWorker:
    """Boost自动化工作器"""
    
    def __init__(self, interval=None):
        """
        初始化Boost工作器
        
        Args:
            interval: 检查间隔（秒）
        """
        self.boost_manager = boost_manager
        self.interval = interval or config.INTERVAL
        self.enabled = True
        self._thread = None
        self._stop_event = threading.Event()
    
    def toggle(self):
        """
        切换工作器状态
        
        Returns:
            bool: 新的状态
        """
        self.enabled = not self.enabled
        logging.info(f"Boost worker {'enabled' if self.enabled else 'disabled'}")
        return self.enabled
    
    def start(self):
        """启动工作器线程"""
        if self._thread is not None and self._thread.is_alive():
            logging.warning("Boost worker already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        mode_msg = "OBSERVATION MODE" if config.OBSERVATION_MODE else "EXECUTION MODE"
        logging.info(f"Boost worker started ({mode_msg})")
        print(f"Boost worker started ({mode_msg})", flush=True)
    
    def stop(self):
        """停止工作器线程"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        logging.info("Boost worker stopped")
    
    def _run(self):
        """运行循环"""
        while not self._stop_event.is_set():
            if self.enabled:
                try:
                    self._process_boost()
                except Exception as e:
                    logging.error(f"Error in boost worker: {e}")
                    print(f"❌ Error in boost worker: {e}", flush=True)
            
            # 使用事件等待，允许提前停止
            self._stop_event.wait(timeout=self.interval)
    
    def _process_boost(self):
        """处理Boost任务"""
        bgt_info = self.boost_manager.get_bgt_info()
        queued_balance = bgt_info["queued_balance"]
        free_balance = bgt_info["free_balance"]

        # 观察模式下只记录不执行
        if config.OBSERVATION_MODE:
            if queued_balance == 0 and free_balance > 0:
                logging.info(f"[OBSERVATION] Available BGT: {free_balance}, queue boost possible")
                print(f"[OBSERVATION] Available BGT: {free_balance}, queue boost possible", flush=True)
            
            if self.boost_manager.can_activate_boost():
                logging.info("[OBSERVATION] Conditions met for activate boost")
                print("[OBSERVATION] Conditions met for activate boost", flush=True)
            
            return

        # 1. 执行Queue Boost（仅当队列为空时）
        if queued_balance == 0 and free_balance > 0:
            tx_hash = self.boost_manager.queue_boost()
            if tx_hash:
                logging.info(f"✅ Queued Boost: {tx_hash.hex()}")
                print(f"✅ queue_boost: {tx_hash.hex()}", flush=True)

        # 2. 当条件满足时执行Activate Boost
        if self.boost_manager.can_activate_boost():
            tx_hash = self.boost_manager.activate_boost()
            if tx_hash:
                logging.info(f"✅ Activated Boost: {tx_hash.hex()}")
                print(f"✅ activate_boost: {tx_hash.hex()}", flush=True)
                
                # 执行奖励获取
                try:
                    reward_tx_hash = bgt_staker_manager.claim_reward()
                    if reward_tx_hash:
                        logging.info(f"✅ Claimed Reward: {reward_tx_hash.hex()}")
                        print(f"✅ claim_reward: {reward_tx_hash.hex()}", flush=True)
                except Exception as e:
                    logging.error(f"❌ Failed to claim reward: {e}")
                    print(f"❌ Failed to claim reward: {e}", flush=True)

# 创建单例实例
boost_worker = BoostWorker()
