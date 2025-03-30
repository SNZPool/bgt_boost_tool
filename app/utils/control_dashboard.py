import os
import sys
import subprocess
import time
import signal
from app.config import config

# 读取必要配置
project_path = config.PROJECT_PATH
event_handler_file = config.EVENT_HANDLER_FILE
dashboard_script_file = config.DASHBOARD_SCRIPT_FILE

# 校验配置完整性
if not all([project_path, event_handler_file, dashboard_script_file]):
    print("[ERROR] 请检查 .env 配置是否完整：PROJECT_PATH / EVENT_HANDLER_FILE / DASHBOARD_SCRIPT_FILE")
    sys.exit(1)

# 构建完整路径
event_handler_path = os.path.join(project_path, event_handler_file)
dashboard_script_path = os.path.join(project_path, dashboard_script_file)
dashboard_script_name = os.path.basename(dashboard_script_file)  # 只取 dashboard.py，用于匹配进程

# === 调用 B 的事件处理函数 ===
def call_b_event(action: str, block_number: int = None, bgt_amount: float = None, account: str = None):
    cmd = ["python3", event_handler_path, action]
    
    # 定义事件参数映射
    event_params = {
        "claim_incentive": [],  # 不需要额外参数
        "active": ["block_number", "bgt_amount"],  # 需要block_number和bgt_amount
        "drop": ["block_number", "bgt_amount", "account"]  # 需要block_number、bgt_amount和account
    }
    
    # 获取当前事件需要的参数列表
    required_params = event_params.get(action, [])
    
    # 参数映射表
    param_values = {
        "block_number": block_number,
        "bgt_amount": bgt_amount,
        "account": account
    }
    
    # 验证并添加参数
    for param in required_params:
        value = param_values.get(param)
        if value is None:
            raise ValueError(f"事件 {action} 需要 {param} 参数")
        cmd.append(str(value))
    
    env = os.environ.copy()
    # 所有事件都需要PRIVATE_KEY
    if config.PRIVATE_KEY:
        env["PRIVATE_KEY"] = config.PRIVATE_KEY

    print(f"[INFO] 调用事件处理脚本：{' '.join(cmd)} (cwd={project_path})")
    try:
        # 使用subprocess.run等待脚本执行完成
        result = subprocess.run(
            cmd,
            cwd=project_path,
            env=env,
            check=True,  # 如果脚本返回非零状态码，抛出异常
            capture_output=True,  # 捕获输出
            text=True  # 将输出转换为文本
        )
        print(f"[INFO] 事件处理脚本执行完成")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 事件处理脚本执行失败: {e.stderr}")
        raise

# === 获取 dashboard 进程（根据 cwd 和脚本名）===
def get_dashboard_pids():
    result = subprocess.run(["pgrep", "-f", dashboard_script_name], stdout=subprocess.PIPE)
    pids = result.stdout.decode().strip().split('\n')

    matched_pids = []
    for pid in pids:
        if not pid.strip():
            continue
        try:
            real_cwd = os.readlink(f"/proc/{pid}/cwd")
            if os.path.abspath(real_cwd) == os.path.abspath(project_path):
                matched_pids.append(int(pid))
        except Exception as e:
            print(f"[WARN] 无法获取 pid {pid} 的工作目录：{e}")
    return matched_pids

# === 重启 dashboard 程序 ===
def restart_dashboard():
    print("[INFO] 重启 dashboard 中...")

    pids = get_dashboard_pids()
    for pid in pids:
        try:
            print(f"[INFO] 终止 dashboard 进程 PID {pid}")
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"[ERROR] 无法终止 PID {pid}：{e}")

    time.sleep(5)

    print("[INFO] 启动 dashboard...")
    # 使用nohup启动dashboard进程，确保进程在后台持续运行
    subprocess.Popen(
        ["python3", dashboard_script_path],
        cwd=project_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

# === 主函数：事件处理 + 重启 dashboard ===
def handle_event(action: str, block_number: int = None, bgt_amount: float = None, account: str = None):
    """
    处理事件并重启dashboard
    
    Args:
        action: 事件类型（active/drop/claim_incentive）
        block_number: 区块号（可选，active和drop事件需要）
        bgt_amount: BGT数量（可选，active和drop事件需要）
        account: 账户地址（可选，仅drop事件需要）
    """
    call_b_event(action, block_number, bgt_amount, account)
    restart_dashboard()


# ✅ 示例调用
# if __name__ == "__main__":
#     # 示例：处理 active 类型事件
#     handle_event("active", 123456, 1000.0)

    # 示例：处理 drop 类型事件（取消注释使用）
    # handle_event("drop", 123456, 1000.0, account="0xabc123...")
