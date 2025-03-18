import logging
from web3 import Web3
from app.config import config

class Web3Client:
    """Web3客户端，用于与区块链交互"""
    
    def __init__(self):
        """初始化Web3客户端"""
        self.w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
        # 检查连接
        if not self.w3.is_connected():
            logging.error("Cannot connect to Ethereum node")
            print("Cannot connect to Ethereum node", flush=True)
    
    def get_transaction_count(self, address):
        """获取账户交易计数（nonce）"""
        return self.w3.eth.get_transaction_count(address)
    
    def get_gas_price(self):
        """获取当前gas价格"""
        return self.w3.eth.gas_price
    
    def get_block_number(self):
        """获取当前区块高度"""
        return self.w3.eth.block_number
    
    def sign_and_send_transaction(self, transaction, private_key=None):
        """
        签名并发送交易
        
        Args:
            transaction: 要发送的交易
            private_key: 私钥（默认使用配置中的私钥）
            
        Returns:
            tx_hash: 成功时返回交易哈希，失败时返回None
        """
        # 观察模式下不执行交易
        if config.OBSERVATION_MODE:
            logging.warning("Transaction not sent - running in observation mode")
            print("⚠️ Transaction not sent - running in observation mode", flush=True)
            return None
            
        try:
            private_key = private_key or config.PRIVATE_KEY
            signed_tx = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx["raw_transaction"])
            return tx_hash
        except Exception as e:
            logging.error(f"Failed to sign and send transaction: {e}")
            print(f"Failed to sign and send transaction: {e}", flush=True)
            return None

# 创建单例实例
web3_client = Web3Client() 