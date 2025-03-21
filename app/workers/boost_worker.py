import time
import logging
import threading
from app.core.boost import boost_manager
from app.core.bgt_staker import bgt_staker_manager
from app.config import config
from app.core.tx_lock import tx_lock
from app.blockchain.contracts import web3_client

class BoostWorker:
    """Boost自动化工作器"""
    
    def __init__(self, interval=None):
        """
        初始化Boost工作器
        
        Args:
            interval: 检查间隔（秒）
        """
        self.boost_manager = boost_manager
        self.interval = interval or config.INTERVAL
        self.enabled = True
        self._thread = None
        self._stop_event = threading.Event()
    
    def toggle(self):
        """
        切换工作器状态
        
        Returns:
            bool: 新的状态
        """
        self.enabled = not self.enabled
        logging.info(f"Boost worker {'enabled' if self.enabled else 'disabled'}")
        return self.enabled
    
    def start(self):
        """启动工作器线程"""
        if self._thread is not None and self._thread.is_alive():
            logging.warning("Boost worker already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        mode_msg = "OBSERVATION MODE" if config.OBSERVATION_MODE else "EXECUTION MODE"
        logging.info(f"Boost worker started ({mode_msg})")
        print(f"Boost worker started ({mode_msg})", flush=True)
    
    def stop(self):
        """停止工作器线程"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        logging.info("Boost worker stopped")
    
    def _run(self):
        """运行循环"""
        while not self._stop_event.is_set():
            if self.enabled:
                try:
                    self._process_boost()
                except Exception as e:
                    logging.error(f"Error in boost worker: {e}")
                    print(f"❌ Error in boost worker: {e}", flush=True)
            
            # 使用事件等待，允许提前停止
            self._stop_event.wait(timeout=self.interval)
    
    def _process_boost(self):
        """处理Boost任务"""
        bgt_info = self.boost_manager.get_bgt_info()
        queued_balance = bgt_info["queued_balance"]
        free_balance = bgt_info["free_balance"]

        # 观察模式下只记录不执行
        if config.OBSERVATION_MODE:
            if queued_balance == 0 and free_balance > 0:
                logging.info(f"[OBSERVATION] Available BGT: {free_balance}, queue boost possible")
                print(f"[OBSERVATION] Available BGT: {free_balance}, queue boost possible", flush=True)
            
            if self.boost_manager.can_activate_boost():
                logging.info("[OBSERVATION] Conditions met for activate boost")
                print("[OBSERVATION] Conditions met for activate boost", flush=True)
            
            return

        # 尝试获取交易锁
        lock_acquired = tx_lock.acquire(owner_name="BoostWorker", blocking=False)
        if not lock_acquired:
            logging.info("⏳ BoostWorker 无法获取交易锁，跳过本次处理")
            return
            
        try:
            # 1. 执行Queue Boost（仅当队列为空时）
            if queued_balance == 0 and free_balance > 0:
                tx_hash = self.boost_manager.queue_boost()
                if tx_hash:
                    logging.info(f"✅ Queued Boost: {tx_hash.hex()}")
                    print(f"✅ queue_boost: {tx_hash.hex()}", flush=True)

            # 2. 当条件满足时执行Activate Boost
            if self.boost_manager.can_activate_boost():
                tx_hash = self.boost_manager.activate_boost()
                if tx_hash:
                    logging.info(f"✅ Activated Boost: {tx_hash.hex()}")
                    print(f"✅ activate_boost: {tx_hash.hex()}", flush=True)
                    
                    # 等待第一个交易确认
                    try:
                        # 修正获取web3客户端的方式 - 直接导入web3_client
                        receipt = web3_client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                        
                        # 获取交易区块高度
                        block_number = receipt.blockNumber
                        logging.info(f"📦 交易区块高度: {block_number}")
                        print(f"📦 交易区块高度: {block_number}", flush=True)
                        
                        # 修正获取合约相关信息的方式
                        contract_address = self.boost_manager.bgt_contract.address
                        contract = web3_client.w3.eth.contract(
                            address=contract_address, 
                            abi=self.boost_manager.bgt_contract.abi
                        )
                        
                        # 遍历日志查找ActivateBoost事件
                        for log in receipt.logs:
                            try:
                                if log['address'].lower() == contract_address.lower():
                                    # 尝试解析事件
                                    parsed_log = contract.events.ActivateBoost().process_log(log)
                                    amount = parsed_log['args']['amount']
                                    logging.info(f"💰 ActivateBoost事件amount值: {amount}")
                                    print(f"💰 ActivateBoost事件amount值: {amount}", flush=True)
                                    break  # 找到事件后退出循环
                            except Exception as e:
                                continue  # 如果不是ActivateBoost事件，继续下一个日志
                        
                        # # 确认交易成功后再执行奖励获取
                        # if receipt.status == 1:  # 1表示交易成功
                        #     reward_tx_hash = bgt_staker_manager.claim_reward()
                        #     if reward_tx_hash:
                        #         logging.info(f"✅ Claimed Reward: {reward_tx_hash.hex()}")
                        #         print(f"✅ claim_reward: {reward_tx_hash.hex()}", flush=True)
                                
                        #         # 等待奖励交易确认并获取区块高度
                        #         try:
                        #             # 使用正确的web3_client
                        #             reward_receipt = web3_client.w3.eth.wait_for_transaction_receipt(reward_tx_hash, timeout=120)
                                    
                        #             # 获取奖励交易区块高度
                        #             reward_block_number = reward_receipt.blockNumber
                        #             logging.info(f"📦 奖励交易区块高度: {reward_block_number}")
                        #             print(f"📦 奖励交易区块高度: {reward_block_number}", flush=True)
                                    
                        #             # 修正获取staker合约相关信息的方式
                        #             staker_contract_address = bgt_staker_manager.contract.address
                        #             staker_contract = web3_client.w3.eth.contract(
                        #                 address=staker_contract_address, 
                        #                 abi=bgt_staker_manager.contract.abi
                        #             )
                                    
                        #             # 遍历日志查找RewardPaid事件
                        #             for log in reward_receipt.logs:
                        #                 try:
                        #                     if log['address'].lower() == staker_contract_address.lower():
                        #                         # 尝试解析RewardPaid事件
                        #                         parsed_log = staker_contract.events.RewardPaid().process_log(log)
                        #                         reward_amount = parsed_log['args']['reward']
                        #                         logging.info(f"💰 RewardPaid事件reward值: {reward_amount}")
                        #                         print(f"💰 RewardPaid事件reward值: {reward_amount}", flush=True)
                        #                         break  # 找到事件后退出循环
                        #                 except Exception as e:
                        #                     continue  # 如果不是RewardPaid事件，继续下一个日志
                                
                        #         except Exception as e:
                        #             logging.error(f"❌ 获取奖励交易信息失败: {e}")
                        #             print(f"❌ 获取奖励交易信息失败: {e}", flush=True)
                    except Exception as e:
                        logging.error(f"❌ Failed to claim reward: {e}")
                        print(f"❌ Failed to claim reward: {e}", flush=True)
        finally:
            # 无论成功或失败，都释放交易锁
            tx_lock.release(owner_name="BoostWorker")

# 创建单例实例
boost_worker = BoostWorker()
