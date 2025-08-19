import json
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from threading import Lock
from utils.logger import global_logger


@dataclass
class HumanTask:
    """人类任务数据类"""
    human_task_id: str
    task_id: str
    human_task: str
    completed: bool = False
    created_at: str = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class HumanTaskManager:
    """人类任务管理器 - 线程安全的任务存储和状态管理"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.human_tasks_file = workspace_path / "human_tasks.json"
        self._lock = Lock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保人类任务文件存在"""
        if not self.human_tasks_file.exists():
            with open(self.human_tasks_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_tasks(self) -> Dict[str, Dict[str, Any]]:
        """加载所有任务"""
        try:
            with open(self.human_tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            global_logger.error(f"Failed to load human tasks: {str(e)}")
            return {}
    
    def _save_tasks(self, tasks: Dict[str, Dict[str, Any]]):
        """保存任务到文件"""
        try:
            with open(self.human_tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            global_logger.error(f"Failed to save human tasks: {str(e)}")
            raise
    
    def create_human_task(self, task_id: str, human_task: str) -> str:
        """创建新的人类任务"""
        human_task_id = str(uuid.uuid4())
        
        with self._lock:
            tasks = self._load_tasks()
            
            # 确保 task_id 键存在
            if task_id not in tasks:
                tasks[task_id] = {}
            
            # 创建人类任务
            human_task_obj = HumanTask(
                human_task_id=human_task_id,
                task_id=task_id,
                human_task=human_task
            )
            
            tasks[task_id][human_task_id] = asdict(human_task_obj)
            self._save_tasks(tasks)
            
            global_logger.info(f"Created human task {human_task_id} for task {task_id}")
            return human_task_id
    
    def get_human_tasks(self, task_id: str) -> List[HumanTask]:
        """获取指定任务下的所有人类任务"""
        with self._lock:
            tasks = self._load_tasks()
            task_human_tasks = tasks.get(task_id, {})
            
            return [
                HumanTask(**task_data) 
                for task_data in task_human_tasks.values()
            ]
    
    def update_human_task_status(self, task_id: str, human_task_id: str, 
                                completed: bool, result: Optional[str] = None) -> bool:
        """更新人类任务状态"""
        with self._lock:
            tasks = self._load_tasks()
            
            if task_id not in tasks or human_task_id not in tasks[task_id]:
                return False
            
            # 更新任务状态
            tasks[task_id][human_task_id]['completed'] = completed
            if result is not None:
                tasks[task_id][human_task_id]['result'] = result
            
            if completed:
                tasks[task_id][human_task_id]['completed_at'] = datetime.now().isoformat()
            
            self._save_tasks(tasks)
            
            global_logger.info(f"Updated human task {human_task_id} status to {completed}")
            return True
    
    def get_human_task(self, task_id: str, human_task_id: str) -> Optional[HumanTask]:
        """获取特定的人类任务"""
        with self._lock:
            tasks = self._load_tasks()
            
            if task_id not in tasks or human_task_id not in tasks[task_id]:
                return None
            
            return HumanTask(**tasks[task_id][human_task_id])
    
    async def wait_for_completion(self, task_id: str, human_task_id: str, 
                                 timeout: Optional[float] = None, 
                                 check_interval: float = 5.0) -> Optional[HumanTask]:
        """等待人类任务完成"""
        start_time = datetime.now()
        
        while True:
            human_task = self.get_human_task(task_id, human_task_id)
            
            if human_task is None:
                global_logger.error(f"Human task {human_task_id} not found")
                return None
            
            if human_task.completed:
                global_logger.info(f"Human task {human_task_id} completed")
                return human_task
            
            # 检查超时
            if timeout and (datetime.now() - start_time).total_seconds() > timeout:
                global_logger.warning(f"Human task {human_task_id} timed out")
                return None
            
            # 等待下次检查
            await asyncio.sleep(check_interval) 