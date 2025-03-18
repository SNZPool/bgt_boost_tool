from flask import Blueprint, jsonify, request, render_template
from app.core.boost import boost_manager
from app.core.unboost import unboost_manager
from app.core.redeem import redeem_manager
from app.core.reward import reward_manager
from app.db.database import db
from app.workers.boost_worker import boost_worker
from app.workers.task_processor import task_processor
from app.workers.status_worker import status_worker
from app.config import config
import time

# 创建Blueprint
api = Blueprint('api', __name__)

@api.route("/")
def index():
    """渲染Web UI"""
    return render_template("index.html")

@api.route("/status", methods=["GET"])
def status():
    """获取BGT统计信息"""
    stats = status_worker.get_status()
    # 添加当前运行模式信息，使用英文
    stats["mode"] = "OBSERVATION" if config.OBSERVATION_MODE else "EXECUTION"
    stats["can_execute"] = not config.OBSERVATION_MODE
    return jsonify(stats)

@api.route("/toggle_boost", methods=["POST"])
def toggle_boost():
    """启用/禁用boost worker"""
    new_state = boost_worker.toggle()
    return jsonify({"boost_enabled": new_state})

@api.route("/toggle_task_processor", methods=["POST"])
def toggle_task_processor():
    """启用/禁用任务处理器"""
    new_state = task_processor.toggle()
    return jsonify({"task_processor_enabled": new_state})

@api.route("/unboost_redeem", methods=["POST"])
def handle_unboost_redeem():
    """处理取消提升和赎回请求"""
    # 在观察模式下禁用写操作
    if config.OBSERVATION_MODE:
        return jsonify({
            "status": "error", 
            "message": "Running in observation mode. No blockchain transactions will be executed."
        }), 403
        
    # 解析请求数据
    data = request.json
    amount = data.get("amount")
    receiver = data.get("receiver")
    
    # 验证输入
    if not amount or float(amount) <= 0:
        return jsonify({"status": "error", "message": "Invalid amount"}), 400
    
    if not receiver:
        return jsonify({"status": "error", "message": "Receiver address is required"}), 400
    
    # 创建任务
    task_id = unboost_manager.create_task(float(amount), receiver)
    
    return jsonify({
        "status": "success",
        "message": "Unboost and redeem task created",
        "task_id": task_id
    })

@api.route("/tasks", methods=["GET"])
def get_tasks():
    """获取待处理任务"""
    tasks = db.get_pending_tasks()
    return jsonify({"tasks": tasks})

@api.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """获取任务详情"""
    task = db.get_task(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404
    
    # 获取任务事件
    events = db.get_events(task_id)
    
    return jsonify({
        "task": task,
        "events": events
    })

@api.route("/history", methods=["GET"])
def get_history():
    """获取任务历史记录"""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    offset = (page - 1) * limit
    
    # 分页获取历史记录
    history = db.get_history(limit=limit, offset=offset)
    
    # 计算总数（可能需要单独查询）
    total = len(history)  # 这是简化处理，实际可能需要COUNT查询
    
    return jsonify({
        "history": history,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    })

@api.route("/statistics", methods=["GET"])
def get_statistics():
    """获取操作统计信息"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    stats = db.get_statistics(start_date=start_date, end_date=end_date)
    
    # 计算总计
    total_boosted = sum(item.get("total_boosted", 0) for item in stats)
    total_unboosted = sum(item.get("total_unboosted", 0) for item in stats)
    total_redeemed = sum(item.get("total_redeemed", 0) for item in stats)
    
    return jsonify({
        "statistics": stats,
        "summary": {
            "total_boosted": total_boosted,
            "total_unboosted": total_unboosted,
            "total_redeemed": total_redeemed
        }
    })

@api.route("/rewards/earned", methods=["GET"])
def get_earned_rewards():
    """获取已赚取的奖励"""
    account = request.args.get("account")
    earned = reward_manager.get_earned(account)
    return jsonify({"earned": earned})

@api.route("/rewards/claim", methods=["POST"])
def claim_rewards():
    """领取奖励"""
    # 在观察模式下禁用写操作
    if config.OBSERVATION_MODE:
        return jsonify({
            "status": "error", 
            "message": "Running in observation mode. No blockchain transactions will be executed."
        }), 403
        
    data = request.json
    recipient = data.get("recipient")
    
    tx_hash = reward_manager.claim_reward(recipient)
    if not tx_hash:
        return jsonify({"status": "error", "message": "Failed to claim rewards"}), 400
    
    return jsonify({
        "status": "success",
        "message": "Rewards claimed successfully",
        "tx_hash": tx_hash.hex()
    })

# 添加调试端点
@api.route('/debug', methods=['GET'])
def debug():
    """调试端点，显示当前配置信息"""
    return jsonify({
        'address': config.ADDRESS,
        'pubkey': config.PUBKEY,
        'mode': 'OBSERVATION' if config.OBSERVATION_MODE else 'EXECUTION',
        'current_time': int(time.time())
    }) 