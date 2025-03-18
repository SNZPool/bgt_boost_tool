import logging
from app.blockchain.contracts import bgt_contract
from app.core.boost import boost_manager
from app.db.database import db
from app.db.models import TaskType, TaskStatus
from app.config import config

class RedeemManager:
    """BGT Redeem管理"""
    
    def __init__(self):
        """初始化Redeem管理器"""
        self.bgt_contract = bgt_contract
    
    def redeem(self, amount, receiver):
        """
        将BGT按1:1的比例兑换为BERA
        
        Args:
            amount: 要兑换的BGT数量，以标准单位(ETH)计算
            receiver: 接收BERA的地址
            
        Returns:
            tx_hash: 成功时返回交易哈希，失败时返回None
        """
        # 将标准单位转换为wei单位
        amount_wei = int(amount * (10 ** 18))
        
        # 执行赎回交易
        return self.bgt_contract.redeem(receiver, amount_wei)
    
    def process_active_tasks(self):
        """处理活跃的unboost任务，准备赎回"""
        # 获取ACTIVE状态的unboost任务
        active_tasks = db.get_pending_tasks(task_type=TaskType.UNBOOST, status=TaskStatus.ACTIVE)
        
        if active_tasks:
            # 一次性获取当前BGT信息
            bgt_info = boost_manager.get_bgt_info()
            free_balance = bgt_info["free_balance"]
            
            for task in active_tasks:
                task_id = task["task_id"]
                amount = task["amount"]
                receiver = task["receiver"]
                
                # 验证BGT现在可用（空闲）
                if free_balance < amount:
                    db.log_event(task_id, "REDEEM_WAITING", {
                        "message": f"Waiting for enough free BGT. Available: {free_balance}, Required: {amount}"
                    })
                    continue
                
                logging.info(f"Redeeming BGT for task: {task_id}")
                print(f"Redeeming BGT for task: {task_id}", flush=True)
                
                # 赎回BGT为BERA
                tx_hash = self.redeem(amount, receiver)
                if not tx_hash:
                    db.log_event(task_id, "REDEEM_FAILED", {
                        "error": "Failed to redeem BGT for BERA"
                    })
                    continue
                
                # 用赎回交易哈希更新任务
                db.update_task(
                    task_id,
                    redeem_tx_hash=tx_hash.hex()
                )
                
                db.log_event(task_id, "REDEEM_SUCCESS", {
                    "tx_hash": tx_hash.hex(),
                    "amount": amount,
                    "receiver": receiver
                })
                
                # 将任务标记为已完成
                db.complete_task(task_id)
                
                logging.info(f"✅ Redeemed {amount} BGT for BERA to {receiver}: {tx_hash.hex()}")
                print(f"✅ redeem: {tx_hash.hex()} for task: {task_id}", flush=True)
                logging.info(f"✅ Task completed: {task_id}")
                print(f"✅ Task completed: {task_id}", flush=True)
                
                # 为后续任务减少可用余额
                free_balance -= amount

# 创建单例实例
redeem_manager = RedeemManager() 