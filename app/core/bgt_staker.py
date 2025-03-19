import logging
from app.blockchain.contracts import bgt_staker_contract
from app.config import config

class BGTStakerManager:
    """BGT Staker 奖励管理"""
    
    def __init__(self):
        """初始化奖励管理器"""
        self.bgt_staker_contract = bgt_staker_contract
    
    def get_earned(self, account=None):
        """
        获取账户已赚取但未领取的奖励
        
        Args:
            account: 要查询的账户地址，默认为配置的地址
            
        Returns:
            float: 已赚取的奖励金额
        """
        if account is None:
            account = config.ADDRESS
        
        try:
            # 获取已赚取的金额（wei单位）
            earned_wei = self.bgt_staker_contract.earned(account)
            decimals = 18  # 假设奖励代币有18位小数
            earned_amount = earned_wei / (10 ** decimals)
            return round(earned_amount, 4)
        except Exception as e:
            logging.error(f"Failed to query earned rewards: {e}")
            print(f"Failed to query earned rewards: {e}", flush=True)
            return 0
    
    def claim_reward(self):
        """
        领取奖励

        Returns:
            tx_hash: 成功时返回交易哈希，否则返回None
        """
        return self.bgt_staker_contract.get_reward()

# 创建单例实例
bgt_staker_manager = BGTStakerManager() 