import requests
import logging

class HubAPI:
    """Berachain Hub API 客户端"""
    
    def __init__(self):
        self.base_url = "https://hub.berachain.com/api"
    
    def has_incentives(self, account_address):
        """
        检查指定账户是否有激励
        
        Args:
            account_address: 账户地址
            
        Returns:
            bool: 如果有激励返回True，否则返回False
        """
        try:
            url = f"{self.base_url}/portfolio/incentives/?account={account_address}"
            response = requests.get(url, timeout=30)
            
            # 检查请求是否成功
            if response.status_code != 200:
                logging.error(f"获取激励信息失败，状态码: {response.status_code}")
                return False
            
            # 解析响应数据
            data = response.json()
            
            # 如果返回为null或空列表，返回False
            if data is None or data == []:
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"检查激励时出错: {e}")
            return False

    def get_incentives_details(self, account_address):
        """
        获取指定账户的激励详细信息
        
        Args:
            account_address: 账户地址
            
        Returns:
            list: 包含验证者和奖励信息的列表，如果获取失败则返回空列表
        """
        try:
            url = f"{self.base_url}/portfolio/incentives/?account={account_address}"
            response = requests.get(url, timeout=30)
            
            # 检查请求是否成功
            if response.status_code != 200:
                logging.error(f"获取激励详情失败，状态码: {response.status_code}")
                return []
            
            # 解析响应数据
            data = response.json()
            
            # 如果返回为null，返回空列表
            if data is None:
                return []
                
            # 返回完整的激励详情列表
            return data
                
        except Exception as e:
            logging.error(f"获取激励详情时出错: {e}")
            return []

# 创建单例实例
hub_api = HubAPI()
