import os
import sys
import subprocess
import time
import signal
from dotenv import load_dotenv

# === 加载 .env 环境变量 ===
load_dotenv()

# 读取必要配置
project_path = os.getenv("PROJECT_PATH")
event_handler_file = os.getenv("EVENT_HANDLER_FILE")
dashboard_script_file = os.getenv("DASHBOARD_SCRIPT_FILE")

# 校验配置完整性
if not all([project_path, event_handler_file, dashboard_script_file]):
    print("[ERROR] 请检查 .env 配置是否完整：PROJECT_PATH / EVENT_HANDLER_FILE / DASHBOARD_SCRIPT_FILE")
    sys.exit(1)

# 构建完整路径
event_handler_path = os.path.join(project_path, event_handler_file)
dashboard_script_path = os.path.join(project_path, dashboard_script_file)
dashboard_script_name = os.path.basename(dashboard_script_file)  # 只取 dashboard.py，用于匹配进程

# === 调用 B 的事件处理函数 ===
def call_b_event(action: str, block_number: int, bgt_amount: float, account: str = None):
    cmd = [
        "python3",
        event_handler_path,
        action,
        str(block_number),
        str(bgt_amount),
    ]
    if action == "drop" and account:
        cmd.append(account)

    print(f"[INFO] 调用事件处理脚本：{' '.join(cmd)}")
    subprocess.run(cmd)

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
    subprocess.Popen(["python3", dashboard_script_path], cwd=project_path)

# === 主函数：事件处理 + 重启 dashboard ===
def handle_event(action: str, block_number: int, bgt_amount: float, account: str = None):
    call_b_event(action, block_number, bgt_amount, account)
    restart_dashboard()


# ✅ 示例调用
# if __name__ == "__main__":
#     # 示例：处理 active 类型事件
#     handle_event("active", 123456, 1000.0)

    # 示例：处理 drop 类型事件（取消注释使用）
    # handle_event("drop", 123456, 1000.0, account="0xabc123...")
