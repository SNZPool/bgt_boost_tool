import logging
import uuid
from datetime import datetime
from flask import request
from app.blockchain.contracts import bgt_contract, web3_client
from app.db.database import db
from app.db.models import TaskType, TaskStatus
from app.config import config

class UnboostManager:
    """BGT Unboost管理"""
    
    def __init__(self):
        """初始化Unboost管理器"""
        self.bgt_contract = bgt_contract
    
    def create_task(self, amount, receiver):
        """
        创建Unboost任务
        
        Args:
            amount: 要unboost和redeem的BGT数量，以标准单位(ETH)计算
            receiver: 接收BERA的地址
            
        Returns:
            task_id: 创建的任务ID
        """
        # 创建数据库任务记录
        metadata = {
            "description": f"Unboosting and redeeming {amount} BGT to {receiver}",
            "source_ip": request.remote_addr if request else "API"
        }
        
        task_id = db.create_task(
            task_type=TaskType.UNBOOST,
            amount=amount,
            receiver=receiver,
            metadata=metadata
        )
        
        logging.info(f"✅ Created unboost task: {task_id} for {amount} BGT to {receiver}")
        print(f"✅ Created unboost task: {task_id} for {amount} BGT to {receiver}", flush=True)
        
        return task_id
    
    def can_drop_boost(self):
        """
        检查是否满足Drop Boost的条件
        直接从区块链读取信息，不依赖数据库中的任务状态
        
        Returns:
            bool: 如果满足条件返回True，否则返回False
        """
        try:
            address = config.ADDRESS
            pubkey = config.PUBKEY
            
            # 从区块链获取排队取消的提升信息
            dropped_queue = self.bgt_contract.get_dropped_queue(address, pubkey)
            queue_block = dropped_queue[0]  # 排队的区块号
            amount = dropped_queue[1]  # 排队取消的BGT金额
            
            # 如果没有排队取消的提升，返回False
            if amount == 0 or queue_block == 0:
                return False
            
            # 获取当前区块和延迟要求
            current_block = web3_client.get_block_number()
            drop_boost_delay = self.bgt_contract.get_drop_boost_delay()
            
            # 计算已经过的区块数和剩余区块数
            blocks_elapsed = current_block - queue_block
            blocks_remaining = drop_boost_delay - blocks_elapsed
            
            # 记录等待状态
            if blocks_remaining > 0:
                logging.info(f"Waiting {blocks_remaining} blocks to drop boost")
                print(f"Waiting {blocks_remaining} blocks to drop boost", flush=True)
                return False
            
            # 延迟已经结束，可以执行drop boost
            return blocks_elapsed >= drop_boost_delay
            
        except Exception as e:
            logging.error(f"Failed to check drop boost conditions: {e}")
            print(f"Failed to check drop boost conditions: {e}", flush=True)
            return False
    
    def get_queued_drop_info(self):
        """
        获取当前已排队等待取消的BGT信息。
        直接从区块链读取信息，不依赖数据库中的任务状态。
        
        Returns:
            dict: 包含已排队取消的BGT信息的字典
        """
        try:
            address = config.ADDRESS
            pubkey = config.PUBKEY
            
            # 获取当前区块
            current_block = web3_client.get_block_number()
            
            # 获取drop boost延迟区块数
            drop_boost_delay = self.bgt_contract.get_drop_boost_delay()
            
            # 从区块链获取排队取消的提升信息
            dropped_queue = self.bgt_contract.get_dropped_queue(address, pubkey)
            queue_block = dropped_queue[0]  # 排队的区块
            amount = dropped_queue[1] / (10 ** 18)  # 排队取消的BGT金额，转换为ETH单位
            
            # 计算还需要等待的区块数
            blocks_elapsed = current_block - queue_block if queue_block > 0 else 0
            blocks_remaining = max(0, drop_boost_delay - blocks_elapsed) if queue_block > 0 else 0
            
            # 判断是否可以执行drop boost
            can_drop = queue_block > 0 and blocks_elapsed >= drop_boost_delay
            
            return {
                "queued_drop_amount": round(amount, 4),
                "queued_drop_block": int(queue_block),
                "drop_delay_blocks": int(drop_boost_delay),
                "drop_blocks_elapsed": int(blocks_elapsed),
                "drop_blocks_remaining": int(blocks_remaining),
                "can_drop": can_drop
            }
        except Exception as e:
            logging.error(f"Failed to get queued drop info: {e}")
            print(f"Failed to get queued drop info: {e}", flush=True)
            return {
                "queued_drop_amount": 0,
                "queued_drop_block": 0,
                "drop_delay_blocks": int(drop_boost_delay) if 'drop_boost_delay' in locals() else 0,
                "drop_blocks_elapsed": 0,
                "drop_blocks_remaining": 0,
                "can_drop": False
            }
    
    def process_pending_tasks(self):
        """处理待处理的unboost任务"""
        # 获取PENDING状态的unboost任务
        pending_tasks = db.get_pending_tasks(task_type=TaskType.UNBOOST, status=TaskStatus.PENDING)
        
        for task in pending_tasks:
            task_id = task["task_id"]
            amount = task["amount"]
            
            logging.info(f"Processing unboost task: {task_id}")
            print(f"Processing unboost task: {task_id}", flush=True)
            
            # 第1步: 队列drop boost
            amount_wei = int(amount * (10 ** 18))
            tx_hash = self.bgt_contract.queue_drop_boost(config.PUBKEY, amount_wei)
            if not tx_hash:
                db.log_event(task_id, "QUEUE_DROP_BOOST_FAILED", {
                    "error": "Failed to queue drop boost"
                })
                continue
            
            # 更新任务状态和交易哈希
            db.update_task(
                task_id, 
                status=TaskStatus.QUEUED.value,
                queue_tx_hash=tx_hash.hex()
            )
            
            db.log_event(task_id, "QUEUE_DROP_BOOST_SUCCESS", {
                "tx_hash": tx_hash.hex(),
                "amount": amount
            })
            
            logging.info(f"✅ Queued Drop Boost: {tx_hash.hex()} for task: {task_id}")
            print(f"✅ queue_drop_boost: {tx_hash.hex()} for task: {task_id}", flush=True)
    
    def process_queued_tasks(self):
        """处理已排队的unboost任务"""
        # 获取QUEUED状态的unboost任务
        queued_tasks = db.get_pending_tasks(task_type=TaskType.UNBOOST, status=TaskStatus.QUEUED)
        
        for task in queued_tasks:
            task_id = task["task_id"]
            
            # 检查是否满足drop boost条件
            if self.can_drop_boost():
                logging.info(f"Activating drop boost for task: {task_id}")
                print(f"Activating drop boost for task: {task_id}", flush=True)
                
                # 更新任务状态
                db.update_task(
                    task_id, 
                    status=TaskStatus.WAITING_FOR_ACTIVATION.value
                )
                
                # 执行drop boost
                tx_hash = self.bgt_contract.drop_boost(config.ADDRESS, config.PUBKEY)
                if not tx_hash:
                    db.log_event(task_id, "DROP_BOOST_FAILED", {
                        "error": "Failed to execute drop boost"
                    })
                    continue
                
                # 更新任务状态和交易哈希
                db.update_task(
                    task_id, 
                    status=TaskStatus.ACTIVE.value,
                    activate_tx_hash=tx_hash.hex()
                )
                
                db.log_event(task_id, "DROP_BOOST_SUCCESS", {
                    "tx_hash": tx_hash.hex()
                })
                
                logging.info(f"✅ Executed Drop Boost: {tx_hash.hex()} for task: {task_id}")
                print(f"✅ drop_boost: {tx_hash.hex()} for task: {task_id}", flush=True)
            else:
                # 记录等待信息（仅在首次出现时记录）
                last_log = db.get_last_task_log(task_id, "DROP_BOOST_WAITING")
                if not last_log:
                    drop_info = self.get_queued_drop_info()
                    blocks_remaining = drop_info["drop_blocks_remaining"]
                    if blocks_remaining > 0:
                        db.log_event(task_id, "DROP_BOOST_WAITING", {
                            "message": f"Waiting {blocks_remaining} blocks for drop boost conditions to be met"
                        })
                    else:
                        db.log_event(task_id, "DROP_BOOST_WAITING", {
                            "message": "Waiting for drop boost conditions to be met"
                        })

# 创建单例实例
unboost_manager = UnboostManager()
