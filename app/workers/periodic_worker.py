import time
import logging
import threading
from app.core.boost import boost_manager
from app.core.bgt_staker import bgt_staker_manager
from app.config import config
from app.blockchain.contracts import web3_client
from app.workers.task_processor import task_processor
from app.utils.control_dashboard import handle_event
from app.core.hub_api import hub_api
from decimal import Decimal

class PeriodicWorker:
    """周期性自动化工作器"""
    
    def __init__(self, interval=None):
        """
        初始化周期性工作器
        
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
        logging.info(f"周期性工作器 {'enabled' if self.enabled else 'disabled'}")
        return self.enabled
    
    def start(self):
        """启动工作器线程"""
        if self._thread is not None and self._thread.is_alive():
            logging.warning("周期性工作器已在运行中")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        mode_msg = "OBSERVATION MODE" if config.OBSERVATION_MODE else "EXECUTION MODE"
        logging.info(f"周期性工作器已启动 ({mode_msg})")
        print(f"周期性工作器已启动 ({mode_msg})", flush=True)
    
    def stop(self):
        """停止工作器线程"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        logging.info("周期性工作器已停止")
    
    def _run(self):
        """运行循环"""
        while not self._stop_event.is_set():
            if self.enabled:
                try:
                    self._process_boost()
                except Exception as e:
                    logging.error(f"周期性工作器运行错误: {e}")
                    print(f"❌ 周期性工作器运行错误: {e}", flush=True)
            
            # 使用事件等待，允许提前停止
            self._stop_event.wait(timeout=self.interval)
    
    def _process_boost(self):
        """处理Boost任务"""
        # 检查是否有未完成的任务
        if task_processor.has_active_tasks():
            logging.info("有未完成的任务正在进行中，暂停Boost流程")
            print("有未完成的任务正在进行中，暂停Boost流程", flush=True)
            return
            
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

                                # 转换为人类可读的金额
                                human_amount = Decimal(amount) / Decimal(10 ** 18)
                                logging.info(f"💰 转换后金额: {human_amount}")
                                print(f"💰 转换后金额: {human_amount}", flush=True)

                                # 调用事件处理函数
                                if config.ENABLE_EVENT_HANDLER:
                                    handle_event("active", block_number, float(human_amount))

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

        # 3. 调用 handle_event("distribute_honey")
        # 被调用端允许周期调用，当不满足条件时直接跳过
        handle_event("distribute_honey")

        # 4. 调用 handle_event("claim_incentive")
        # 检查是否需要检查激励
        # 使用内存中的变量记录上次检查时间，避免使用数据库
        current_time = time.time()
        
        # 如果是第一次运行或者_last_incentive_check_time未定义
        if not hasattr(self, '_last_incentive_check_time'):
            self._last_incentive_check_time = 0
            
        # 计算距离上次检查的时间（秒）
        time_since_last_check = current_time - self._last_incentive_check_time
        
        # 检查是否已经过了24小时（86400秒）
        if time_since_last_check >= 86400:  # 每24小时检查一次
            logging.info("开始每日激励检查")
            print("开始每日激励检查", flush=True)
            
            # while hub_api.has_incentives(config.ADDRESS):
            #     handle_event("claim_incentive")
            #     # 等待 berachain hub api 更新数据
            #     time.sleep(300)
            handle_event("claim_incentive")

            # 更新上次检查时间
            self._last_incentive_check_time = current_time
        else:
            # 如果未到检查时间，则跳过此部分
            logging.debug(f"距离下次激励检查还有 {86400 - time_since_last_check} 秒")

        # 5. 调用 handle_event("distribute_incentive")
        # 被调用端允许周期调用，当不满足条件时直接跳过
        handle_event("distribute_incentive")

        # 6. 调用 emission_rebalance
        if config.ENABLE_REBALANCE_HANDLER == True:
            # 检查是否需要执行 emission_rebalance
            if not hasattr(self, '_last_rebalance_time'):
                self._last_rebalance_time = 0

            # 计算距离上次执行的时间（秒）
            time_since_last_rebalance = current_time - self._last_rebalance_time

            # 检查是否已经过了4小时（14400秒）
            if time_since_last_rebalance >= 14400:  # 每4小时执行一次
                logging.info("开始执行 emission_rebalance")
                print("开始执行 emission_rebalance", flush=True)
                
                handle_event("emission_rebalance")
                
                # 更新上次执行时间
                self._last_rebalance_time = current_time
            else:
                logging.info(f"距离下次 emission_rebalance 还有 {14400 - time_since_last_rebalance} 秒")

# 创建单例实例
periodic_worker = PeriodicWorker()
