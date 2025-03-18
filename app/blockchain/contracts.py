import json
import logging
from app.blockchain.web3_client import web3_client
from app.config import config

class ContractClient:
    """合约客户端基类"""
    
    def __init__(self, address, abi_path):
        """
        初始化合约客户端
        
        Args:
            address: 合约地址
            abi_path: ABI文件路径
        """
        self.address = address
        self.abi = self._load_abi(abi_path)
        self.contract = web3_client.w3.eth.contract(address=address, abi=self.abi)
        self.web3_client = web3_client  # 添加web3_client作为实例属性
    
    def _load_abi(self, abi_path):
        """加载合约ABI"""
        with open(abi_path, "r") as f:
            return json.load(f)
    
    def build_transaction(self, function, gas=200000):
        """构建交易对象"""
        return function.build_transaction({
            'from': config.ADDRESS,
            'nonce': web3_client.get_transaction_count(config.ADDRESS),
            'gas': gas,
            'gasPrice': web3_client.get_gas_price()
        })
    
    def execute(self, function, gas=200000):
        """执行合约方法"""
        tx = self.build_transaction(function, gas)
        return web3_client.sign_and_send_transaction(tx)

class BGTContract(ContractClient):
    """BGT合约客户端"""
    
    def __init__(self):
        super().__init__(config.BGT_CONTRACT_ADDRESS, "app/abi/bgt_abi.json")
    
    def get_balance(self, address):
        """获取BGT余额"""
        return self.contract.functions.balanceOf(address).call()
    
    def get_boosts(self, address):
        """获取已提升的BGT数量"""
        return self.contract.functions.boosts(address).call()
    
    def get_queued_boost(self, address):
        """获取已排队的BGT数量"""
        return self.contract.functions.queuedBoost(address).call()
    
    def get_boosted_queue(self, account, pubkey):
        """获取排队提升的详情"""
        return self.contract.functions.boostedQueue(account, pubkey).call()
    
    def get_dropped_queue(self, account, pubkey):
        """获取排队取消提升的详情"""
        return self.contract.functions.dropBoostQueue(account, pubkey).call()
    
    def get_activate_boost_delay(self):
        """获取激活提升的延迟区块数"""
        return self.contract.functions.activateBoostDelay().call()
    
    def get_drop_boost_delay(self):
        """获取移除提升的延迟区块数"""
        return self.contract.functions.dropBoostDelay().call()
    
    def queue_boost(self, pubkey, amount):
        """排队提升BGT"""
        function = self.contract.functions.queueBoost(pubkey, amount)
        return self.execute(function)
    
    def activate_boost(self, account, pubkey):
        """激活提升BGT"""
        function = self.contract.functions.activateBoost(account, pubkey)
        return self.execute(function)
    
    def cancel_boost(self, pubkey, amount):
        """取消排队的提升"""
        function = self.contract.functions.cancelBoost(pubkey, amount)
        return self.execute(function)
    
    def queue_drop_boost(self, pubkey, amount):
        """排队移除BGT提升"""
        function = self.contract.functions.queueDropBoost(pubkey, amount)
        return self.execute(function)
    
    def cancel_drop_boost(self, pubkey, amount):
        """取消排队的提升移除"""
        function = self.contract.functions.cancelDropBoost(pubkey, amount)
        return self.execute(function)
    
    def drop_boost(self, account, pubkey):
        """移除BGT提升"""
        function = self.contract.functions.dropBoost(account, pubkey)
        return self.execute(function)
    
    def redeem(self, receiver, amount):
        """赎回BGT为BERA"""
        function = self.contract.functions.redeem(receiver, amount)
        return self.execute(function)

class RewardContract(ContractClient):
    """奖励合约客户端"""
    
    def __init__(self):
        super().__init__(config.REWARD_CONTRACT_ADDRESS, "app/abi/reward_abi.json")
    
    def earned(self, account):
        """获取已赚取但未领取的奖励数量"""
        return self.contract.functions.earned(account).call()
    
    def get_reward(self, account, recipient, gas=300000):
        """领取奖励"""
        function = self.contract.functions.getReward(account, recipient)
        return self.execute(function, gas)

# 创建合约实例
bgt_contract = BGTContract()
reward_contract = RewardContract() 