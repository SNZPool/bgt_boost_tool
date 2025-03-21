import logging
from app.blockchain.contracts import bgt_contract, web3_client
from app.config import config

class BoostManager:
    """BGT Boost管理"""
    
    def __init__(self):
        """初始化Boost管理器"""
        self.bgt_contract = bgt_contract
    
    def get_bgt_info(self):
        """
        获取BGT信息
        
        Returns:
            dict: 包含BGT信息的字典
        """
        try:
            address = config.ADDRESS
            pubkey = config.PUBKEY
            
            # 获取BGT余额
            total_balance = self.bgt_contract.get_balance(address) / (10 ** 18)
            
            # 获取已提升的数量
            boost_balance = self.bgt_contract.get_boosts(address) / (10 ** 18)
            
            # 获取已排队的数量
            queued_balance = self.bgt_contract.get_queued_boost(address) / (10 ** 18)
            
            # 计算空闲余额
            free_balance = total_balance - boost_balance - queued_balance
            
            # 获取队列详情
            queued_boost_info = self.bgt_contract.get_boosted_queue(address, pubkey)
            queue_block = queued_boost_info[0]  # 排队的区块
            
            # 获取当前区块 - 修正获取方式
            current_block = web3_client.get_block_number()
            
            # 获取激活延迟
            activate_boost_delay = self.bgt_contract.get_activate_boost_delay()
            
            # 计算已经过的区块和剩余区块
            blocks_elapsed = current_block - queue_block if queue_block > 0 else 0
            blocks_remaining = max(0, activate_boost_delay - blocks_elapsed) if queue_block > 0 else 0
            
            # 判断是否可以激活
            can_activate = queue_block > 0 and blocks_elapsed >= activate_boost_delay
            
            return {
                "total_balance": round(total_balance, 4),
                "boost_balance": round(boost_balance, 4),
                "queued_balance": round(queued_balance, 4),
                "free_balance": round(free_balance, 4),
                "boost_queue_block": int(queue_block),
                "boost_delay_blocks": int(activate_boost_delay),
                "boost_blocks_elapsed": int(blocks_elapsed),
                "boost_blocks_remaining": int(blocks_remaining),
                "can_activate": can_activate
            }
        except Exception as e:
            logging.error(f"Failed to get BGT info: {e}")
            print(f"Failed to get BGT info: {e}", flush=True)
            return {
                "total_balance": 0,
                "boost_balance": 0,
                "queued_balance": 0,
                "free_balance": 0,
                "boost_queue_block": 0,
                "boost_delay_blocks": 0,
                "boost_blocks_elapsed": 0,
                "boost_blocks_remaining": 0,
                "can_activate": False
            }
    
    def can_activate_boost(self):
        """
        检查是否满足激活Boost的条件
        
        Returns:
            bool: 如果满足条件返回True，否则返回False
        """
        address = config.ADDRESS
        pubkey = config.PUBKEY
        
        # 获取queueBoost输入时的区块号
        queued_boost = self.bgt_contract.get_boosted_queue(address, pubkey)
        block_number_last = queued_boost[0]  # 获取blockNumberLast
        amount = queued_boost[1]  # 获取queuedBoost BGT金额
        logging.info(f"💰 Queued boost info: {queued_boost}")
        logging.info(f"💰 Amount: {amount}")
        
        # 如果没有队列Boost余额，返回False
        if amount == 0:
            return False
        
        # 检查当前区块号
        current_block = web3_client.get_block_number()
        activate_boost_delay = self.bgt_contract.get_activate_boost_delay()
        
        # 检查等待时间要求是否满足
        blocks_remaining = activate_boost_delay - (current_block - block_number_last)
        if blocks_remaining > 0:
            logging.info(f"Waiting {blocks_remaining} blocks to activate queued BGT")
            print(f"Waiting {blocks_remaining} blocks to activate queued BGT", flush=True)
        
        return current_block - block_number_last > activate_boost_delay
    
    def queue_boost(self):
        """
        执行Queue Boost操作
        
        Returns:
            tx_hash: 成功时返回交易哈希，否则返回None
        """
        # 检查是否已有排队的提升
        bgt_info = self.get_bgt_info()
        if bgt_info["queued_balance"] > 0:
            logging.info("Queue boost skipped: already have queued balance")
            return None
        
        # 获取可用余额并转换为wei单位
        free_balance = int(bgt_info["free_balance"] * (10 ** 18))
        if free_balance <= 0:
            logging.info("Queue boost skipped: no free balance")
            return None
            
        # 执行交易
        return self.bgt_contract.queue_boost(config.PUBKEY, free_balance)
    
    def activate_boost(self):
        """
        如果满足条件，执行Activate Boost操作
        
        Returns:
            tx_hash: 成功时返回交易哈希，否则返回None
        """
        if not self.can_activate_boost():
            logging.warning("⚠️  Activation conditions not met, skipping Activate Boost")
            print("⚠️  Activation conditions not met, skipping Activate Boost", flush=True)
            return None
        
        return self.bgt_contract.activate_boost(config.ADDRESS, config.PUBKEY)

# 创建单例实例
boost_manager = BoostManager() 