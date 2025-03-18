from enum import Enum

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    WAITING_FOR_ACTIVATION = "waiting_for_activation"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(Enum):
    """任务类型枚举"""
    BOOST = "boost"
    UNBOOST = "unboost"
    REDEEM = "redeem" 