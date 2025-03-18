import os
import sqlite3
import json
import time
from datetime import datetime
from app.db.models import TaskStatus, TaskType

class Database:
    """SQLite数据库，用于BGT操作跟踪"""
    
    def __init__(self, db_path="data/bgt_operations.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
    
    def create_tables(self):
        """创建必要的表（如果不存在）"""
        cursor = self.conn.cursor()
        
        # 任务表：跟踪正在进行的操作
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE,
            task_type TEXT,
            amount REAL,
            receiver TEXT,
            status TEXT,
            created_at INTEGER,
            updated_at INTEGER,
            queue_tx_hash TEXT,
            activate_tx_hash TEXT,
            redeem_tx_hash TEXT,
            metadata TEXT
        )
        ''')
        
        # 历史表：已完成操作的记录
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE,
            task_type TEXT,
            amount REAL,
            receiver TEXT,
            status TEXT,
            created_at INTEGER,
            completed_at INTEGER,
            queue_tx_hash TEXT,
            activate_tx_hash TEXT, 
            redeem_tx_hash TEXT,
            metadata TEXT
        )
        ''')
        
        # 事件日志表：详细操作跟踪
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            event_type TEXT,
            timestamp INTEGER,
            details TEXT
        )
        ''')
        
        # 统计表：聚合数据
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_date TEXT,
            total_boosted REAL,
            total_unboosted REAL,
            total_redeemed REAL,
            updated_at INTEGER
        )
        ''')
        
        self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def create_task(self, task_type, amount, receiver, metadata=None):
        """
        创建新任务
        
        Args:
            task_type: 任务类型（boost, unboost, redeem）
            amount: BGT数量
            receiver: 接收者地址
            metadata: 附加元数据
            
        Returns:
            task_id: 创建的任务ID
        """
        cursor = self.conn.cursor()
        task_id = f"{task_type.value}_{int(time.time())}_{amount}"
        now = int(time.time())
        
        cursor.execute('''
        INSERT INTO tasks 
        (task_id, task_type, amount, receiver, status, created_at, updated_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, 
            task_type.value, 
            amount, 
            receiver, 
            TaskStatus.PENDING.value, 
            now, 
            now, 
            json.dumps(metadata or {})
        ))
        
        self.conn.commit()
        
        # 记录事件
        self.log_event(task_id, "TASK_CREATED", {"amount": amount, "receiver": receiver})
        
        return task_id
    
    def update_task(self, task_id, **kwargs):
        """
        更新任务
        
        Args:
            task_id: 要更新的任务ID
            **kwargs: 要更新的字段
        """
        if not kwargs:
            return
        
        cursor = self.conn.cursor()
        
        # 准备SET部分的查询
        set_clause = []
        values = []
        
        for key, value in kwargs.items():
            if key == 'metadata':
                # 处理元数据为JSON
                set_clause.append(f"{key} = ?")
                values.append(json.dumps(value))
            else:
                set_clause.append(f"{key} = ?")
                values.append(value)
        
        # 始终更新updated_at
        set_clause.append("updated_at = ?")
        values.append(int(time.time()))
        
        # 将task_id添加到values
        values.append(task_id)
        
        # 构造并执行查询
        query = f"UPDATE tasks SET {', '.join(set_clause)} WHERE task_id = ?"
        cursor.execute(query, values)
        self.conn.commit()
    
    def get_task(self, task_id):
        """
        通过ID获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            task: 任务数据的字典
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        task = dict(row)
        # 解析JSON元数据
        if task.get('metadata'):
            task['metadata'] = json.loads(task['metadata'])
        
        return task
    
    def get_pending_tasks(self, task_type=None, status=None):
        """
        获取待处理的任务
        
        Args:
            task_type: 按任务类型筛选
            status: 按状态筛选
            
        Returns:
            tasks: 任务数据字典的列表
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type.value if isinstance(task_type, TaskType) else task_type)
        
        if status:
            query += " AND status = ?"
            params.append(status.value if isinstance(status, TaskStatus) else status)
        
        query += " ORDER BY created_at ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            task = dict(row)
            # 解析JSON元数据
            if task.get('metadata'):
                task['metadata'] = json.loads(task['metadata'])
            tasks.append(task)
        
        return tasks
    
    def complete_task(self, task_id, status=TaskStatus.COMPLETED):
        """
        将任务标记为已完成并移至历史记录
        
        Args:
            task_id: 任务ID
            status: 最终状态
        """
        task = self.get_task(task_id)
        if not task:
            return
        
        cursor = self.conn.cursor()
        now = int(time.time())
        
        # 插入历史记录
        cursor.execute('''
        INSERT INTO history
        (task_id, task_type, amount, receiver, status, created_at, completed_at, 
        queue_tx_hash, activate_tx_hash, redeem_tx_hash, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task['task_id'],
            task['task_type'],
            task['amount'],
            task['receiver'],
            status.value,
            task['created_at'],
            now,
            task.get('queue_tx_hash'),
            task.get('activate_tx_hash'),
            task.get('redeem_tx_hash'),
            json.dumps(task.get('metadata', {}))
        ))
        
        # 从任务表中删除
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        
        # 更新统计数据
        self.update_statistics(task)
        
        self.conn.commit()
        
        # 记录事件
        self.log_event(task_id, "TASK_COMPLETED", {"status": status.value})
    
    def log_event(self, task_id, event_type, details=None):
        """
        记录任务事件
        
        Args:
            task_id: 任务ID
            event_type: 事件类型
            details: 事件详细信息
        """
        cursor = self.conn.cursor()
        now = int(time.time())
        
        cursor.execute('''
        INSERT INTO events
        (task_id, event_type, timestamp, details)
        VALUES (?, ?, ?, ?)
        ''', (
            task_id,
            event_type,
            now,
            json.dumps(details or {})
        ))
        
        self.conn.commit()
    
    def get_events(self, task_id):
        """
        获取任务的事件
        
        Args:
            task_id: 任务ID
            
        Returns:
            events: 事件列表
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE task_id = ? ORDER BY timestamp ASC", (task_id,))
        rows = cursor.fetchall()
        
        events = []
        for row in rows:
            event = dict(row)
            # 解析JSON详情
            if event.get('details'):
                event['details'] = json.loads(event['details'])
            events.append(event)
        
        return events
    
    def update_statistics(self, task):
        """
        基于已完成任务更新统计数据
        
        Args:
            task: 任务数据
        """
        cursor = self.conn.cursor()
        now = int(time.time())
        date = datetime.fromtimestamp(now).strftime('%Y-%m-%d')
        
        # 检查今天是否已有条目
        cursor.execute("SELECT * FROM statistics WHERE stat_date = ?", (date,))
        row = cursor.fetchone()
        
        if row:
            # 更新现有条目
            stats = dict(row)
            field_to_update = None
            
            if task['task_type'] == TaskType.BOOST.value:
                field_to_update = "total_boosted"
            elif task['task_type'] == TaskType.UNBOOST.value:
                field_to_update = "total_unboosted"
            elif task['task_type'] == TaskType.REDEEM.value:
                field_to_update = "total_redeemed"
            
            if field_to_update:
                new_value = stats[field_to_update] + task['amount']
                cursor.execute(f"UPDATE statistics SET {field_to_update} = ?, updated_at = ? WHERE id = ?", 
                              (new_value, now, stats['id']))
        else:
            # 创建新条目
            total_boosted = task['amount'] if task['task_type'] == TaskType.BOOST.value else 0
            total_unboosted = task['amount'] if task['task_type'] == TaskType.UNBOOST.value else 0
            total_redeemed = task['amount'] if task['task_type'] == TaskType.REDEEM.value else 0
            
            cursor.execute('''
            INSERT INTO statistics
            (stat_date, total_boosted, total_unboosted, total_redeemed, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                date,
                total_boosted,
                total_unboosted,
                total_redeemed,
                now
            ))
        
        self.conn.commit()
    
    def get_statistics(self, start_date=None, end_date=None):
        """
        获取日期范围的统计数据
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            stats: 统计数据列表
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM statistics WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND stat_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND stat_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY stat_date ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_history(self, task_type=None, start_date=None, end_date=None, limit=50, offset=0):
        """
        获取操作历史
        
        Args:
            task_type: 按任务类型筛选
            start_date: 开始日期（时间戳）
            end_date: 结束日期（时间戳）
            limit: 限制结果数量
            offset: 分页偏移量
            
        Returns:
            history: 历史记录列表
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM history WHERE 1=1"
        params = []
        
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type.value if isinstance(task_type, TaskType) else task_type)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            record = dict(row)
            # 解析JSON元数据
            if record.get('metadata'):
                record['metadata'] = json.loads(record['metadata'])
            history.append(record)
        
        return history

# 创建单例实例
db = Database() 