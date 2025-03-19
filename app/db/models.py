from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum as DbEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued" 
    WAITING_FOR_ACTIVATION = "waiting_for_activation"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class TaskType(Enum):
    """任务类型枚举"""
    BOOST = "boost"
    UNBOOST = "unboost"
    REDEEM = "redeem"