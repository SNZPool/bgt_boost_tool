import threading
import logging
import time

class TransactionLock:
    """交易锁管理器，确保系统范围内的交易不会并发执行"""
    
    def __init__(self, timeout=300):
        """
        初始化交易锁
        
        Args:
            timeout: 锁的最大持有时间（秒），防止死锁
        """
        self._lock = threading.Lock()
        self._owner = None
        self._acquire_time = None
        self._timeout = timeout
    
    def acquire(self, owner_name, blocking=True, timeout=None):
        """
        获取交易锁
        
        Args:
            owner_name: 请求锁的模块名称，用于日志
            blocking: 是否阻塞等待
            timeout: 等待锁的超时时间
            
        Returns:
            bool: 是否成功获取锁
        """
        # 检查锁是否超时
        self._check_timeout()
        
        # 尝试获取锁
        result = self._lock.acquire(blocking=blocking, timeout=timeout)
        if result:
            self._owner = owner_name
            self._acquire_time = time.time()
            logging.info(f"🔒 交易锁已被 {owner_name} 获取")
            print(f"🔒 交易锁已被 {owner_name} 获取", flush=True)
        else:
            current_owner = self._owner or "未知模块"
            logging.info(f"⏳ {owner_name} 等待交易锁释放 (当前持有者: {current_owner})")
            print(f"⏳ {owner_name} 等待交易锁释放 (当前持有者: {current_owner})", flush=True)
            
        return result
    
    def release(self, owner_name):
        """
        释放交易锁
        
        Args:
            owner_name: 释放锁的模块名称，用于验证
        """
        if not self._lock.locked():
            logging.warning(f"⚠️ {owner_name} 尝试释放未锁定的交易锁")
            return
            
        if self._owner != owner_name:
            logging.warning(f"⚠️ {owner_name} 尝试释放不属于它的交易锁 (属于 {self._owner})")
            return
            
        self._owner = None
        self._acquire_time = None
        self._lock.release()
        logging.info(f"🔓 交易锁已被 {owner_name} 释放")
        print(f"🔓 交易锁已被 {owner_name} 释放", flush=True)
    
    def _check_timeout(self):
        """检查并处理锁超时情况"""
        if (self._lock.locked() and self._acquire_time and 
                time.time() - self._acquire_time > self._timeout):
            logging.warning(f"⚠️ 交易锁已超时 (持有者: {self._owner})，强制释放")
            print(f"⚠️ 交易锁已超时 (持有者: {self._owner})，强制释放", flush=True)
            try:
                self._lock.release()
            except RuntimeError:
                pass
            self._owner = None
            self._acquire_time = None

# 创建全局单例实例
tx_lock = TransactionLock() 