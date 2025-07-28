import os
import json
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from utils.logger import TaskLogger, global_logger


class TaskManager:
    """任务管理器"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path).absolute()
        self.tasks_dir = self.workspace_path / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, TaskInfo] = {}
        global_logger.info(f"TaskManager initialized with workspace: {self.workspace_path}")
    
    def create_task(self, task_id: str, task_name: str, requirements: Optional[str] = None) -> Dict:
        """创建新任务"""
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id} already exists")
        
        task_path = self.tasks_dir / task_id
        if task_path.exists():
            raise ValueError(f"Task directory {task_path} already exists")
        
        try:
            # 创建任务目录结构
            dirs = ['config', 'upload', 'rag_db', 'code_env', 'code_run', 'logs', 'checkpoint']
            for dir_name in dirs:
                (task_path / dir_name).mkdir(parents=True, exist_ok=True)
            
            # 创建meta.json
            meta_data = {
                "task_id": task_id,
                "task_name": task_name,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "embedded_files": [],
                "requirements": requirements
            }
            
            meta_file = task_path / "config" / "meta.json"
            with open(meta_file, 'w') as f:
                json.dump(meta_data, f, indent=2)
            
            # 注意：虚拟环境将在Docker容器内创建，不在主机上创建
            # 如果有requirements，将保存到meta.json中，由Docker容器内的pip_install处理
            
            # 创建任务logger
            logger = TaskLogger(task_id, str(task_path / "logs"))
            logger.log_process(f"Task {task_id} created successfully")
            
            # 保存任务信息
            task_info = TaskInfo(
                task_id=task_id,
                task_name=task_name,
                path=task_path,
                created_at=datetime.now(),
                logger=logger
            )
            self.tasks[task_id] = task_info
            
            global_logger.info(f"Task {task_id} created at {task_path}")
            
            return {
                "task_id": task_id,
                "task_name": task_name,
                "path": str(task_path),
                "status": "created"
            }
            
        except Exception as e:
            # 清理失败的任务
            if task_path.exists():
                shutil.rmtree(task_path)
            raise Exception(f"Failed to create task: {str(e)}")
    
    def delete_task(self, task_id: str) -> Dict:
        """删除任务"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task_info = self.tasks[task_id]
        task_path = task_info.path
        
        try:
            # 删除任务目录
            if task_path.exists():
                shutil.rmtree(task_path)
            
            # 从内存中删除
            del self.tasks[task_id]
            
            global_logger.info(f"Task {task_id} deleted")
            
            return {
                "task_id": task_id,
                "status": "deleted"
            }
            
        except Exception as e:
            raise Exception(f"Failed to delete task: {str(e)}")
    
    def get_task(self, task_id: str) -> 'TaskInfo':
        """获取任务信息"""
        if task_id not in self.tasks:
            # 尝试从磁盘加载
            task_path = self.tasks_dir / task_id
            if task_path.exists():
                meta_file = task_path / "config" / "meta.json"
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        meta_data = json.load(f)
                    
                    logger = TaskLogger(task_id, str(task_path / "logs"))
                    task_info = TaskInfo(
                        task_id=task_id,
                        task_name=meta_data.get('task_name', 'Unknown'),
                        path=task_path,
                        created_at=datetime.fromisoformat(meta_data['created_at']),
                        logger=logger
                    )
                    self.tasks[task_id] = task_info
                    return task_info
            
            raise ValueError(f"Task {task_id} not found")
        
        return self.tasks[task_id]
    
    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        tasks = []
        
        # 扫描任务目录
        for task_dir in self.tasks_dir.iterdir():
            if task_dir.is_dir():
                meta_file = task_dir / "config" / "meta.json"
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        meta_data = json.load(f)
                    tasks.append({
                        "task_id": meta_data["task_id"],
                        "task_name": meta_data["task_name"],
                        "created_at": meta_data["created_at"],
                        "status": meta_data.get("status", "unknown")
                    })
        
        return tasks
    



class TaskInfo:
    """任务信息"""
    def __init__(self, task_id: str, task_name: str, path: Path, created_at: datetime, logger: TaskLogger):
        self.task_id = task_id
        self.task_name = task_name
        self.path = path
        self.created_at = created_at
        self.logger = logger
