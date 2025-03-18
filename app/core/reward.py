import logging
from app.blockchain.contracts import reward_contract
from app.config import config

class RewardManager:
    """BGT 奖励管理"""
    
    def __init__(self):
        """初始化奖励管理器"""
        self.reward_contract = reward_contract
    
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
            earned_wei = self.reward_contract.earned(account)
            decimals = 18  # 假设奖励代币有18位小数
            earned_amount = earned_wei / (10 ** decimals)
            return round(earned_amount, 4)
        except Exception as e:
            logging.error(f"Failed to query earned rewards: {e}")
            print(f"Failed to query earned rewards: {e}", flush=True)
            return 0
    
    def claim_reward(self, recipient=None):
        """
        领取奖励
        
        Args:
            recipient: 接收奖励的地址，默认为当前地址
            
        Returns:
            tx_hash: 成功时返回交易哈希，否则返回None
        """
        account = config.ADDRESS
        if recipient is None:
            recipient = account
        
        return self.reward_contract.get_reward(account, recipient)

# 创建单例实例
reward_manager = RewardManager() 