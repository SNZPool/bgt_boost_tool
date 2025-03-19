import os
from dotenv import load_dotenv

# 允许强制刷新环境变量配置
def reload_env():
    """重新加载环境变量配置"""
    load_dotenv(override=True)

# 初始加载
reload_env()

class Config:
    """配置类，使用属性方法动态获取环境变量"""
    
    LOG_FILE = "boost.log"
    
    @classmethod
    def reload(cls):
        """重新加载环境变量"""
        reload_env()
    
    @property
    def RPC_URL(self):
        return os.getenv("RPC_URL")
    
    @property
    def DEPOSIT_CONTRACT_ADDRESS(self):
        return os.getenv("DEPOSIT_CONTRACT_ADDRESS")
    
    @property
    def REWARD_CONTRACT_ADDRESS(self):
        return os.getenv("REWARD_CONTRACT_ADDRESS")
    
    @property
    def BGT_CONTRACT_ADDRESS(self):
        return os.getenv("BGT_CONTRACT_ADDRESS")
    
    @property
    def PRIVATE_KEY(self):
        return os.getenv("PRIVATE_KEY")
    
    @property
    def ADDRESS(self):
        return os.getenv("ADDRESS")
    
    @property
    def PUBKEY(self):
        return os.getenv("PUBKEY")
    
    @property
    def PORT(self):
        return int(os.getenv("PORT", 5010))
    
    @property
    def INTERVAL(self):
        return int(os.getenv("INTERVAL", 30))
    
    @property
    def STATUS_INTERVAL(self):
        return int(os.getenv("STATUS_INTERVAL", 10))
    
    @property
    def MODE(self):
        return os.getenv("MODE", "")
    
    @property
    def BGT_STAKER_CONTRACT_ADDRESS(self):
        return os.getenv("BGT_STAKER_CONTRACT_ADDRESS")
    
    
    @property
    def OBSERVATION_MODE(self):
        """观察模式：明确设置为OBSERVATION或没有私钥"""
        return self.MODE.upper() == "OBSERVATION" or not self.PRIVATE_KEY
    
    

# 创建单例实例
config = Config()
