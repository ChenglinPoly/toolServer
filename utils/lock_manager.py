import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from utils.logger import global_logger

# 全局锁管理器实例
_global_lock_manager = None

def set_global_lock_manager(lock_manager):
    """设置全局锁管理器实例"""
    global _global_lock_manager
    _global_lock_manager = lock_manager

def get_global_lock_manager():
    """获取全局锁管理器实例"""
    return _global_lock_manager

@dataclass
class FileLock:
    """文件锁数据类"""
    path: str
    level: int
    locker_name: str
    locked_at: float
    task_id: str
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FileLock':
        """从字典创建"""
        return cls(**data)

class LockManager:
    """文件锁管理器"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.locks_file = workspace_path / "locks.json"
        self._locks: Dict[str, FileLock] = {}
        self._load_locks()
    
    def _load_locks(self):
        """加载锁信息"""
        try:
            if self.locks_file.exists():
                with open(self.locks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._locks = {
                        path: FileLock.from_dict(lock_data) 
                        for path, lock_data in data.items()
                    }
                global_logger.info(f"已加载 {len(self._locks)} 个文件锁")
        except Exception as e:
            global_logger.error(f"加载锁信息失败: {e}")
            self._locks = {}
    
    def _save_locks(self):
        """保存锁信息"""
        try:
            # 确保目录存在
            self.locks_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {path: lock.to_dict() for path, lock in self._locks.items()}
            with open(self.locks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            global_logger.info(f"已保存 {len(self._locks)} 个文件锁")
        except Exception as e:
            global_logger.error(f"保存锁信息失败: {e}")
    
    def _normalize_path(self, file_path: str, task_id: str) -> str:
        """标准化路径"""
        # 获取任务路径
        task_path = self.workspace_path / "tasks" / task_id
        
        # 如果是相对路径，相对于任务目录
        if not os.path.isabs(file_path):
            full_path = task_path / file_path
        else:
            full_path = Path(file_path)
        
        # 转换为相对于workspace的路径进行存储
        try:
            relative_path = full_path.relative_to(self.workspace_path)
            return str(relative_path)
        except ValueError:
            # 如果路径不在workspace内，使用绝对路径
            return str(full_path.absolute())
    
    def lock_file(self, file_path: str, level: int, locker_name: str, task_id: str) -> Tuple[bool, str]:
        """
        锁定文件或目录
        
        Args:
            file_path: 文件路径
            level: 锁等级 (数字越大权限越高)
            locker_name: 上锁者名称
            task_id: 任务ID
            
        Returns:
            (成功标志, 消息)
        """
        norm_path = self._normalize_path(file_path, task_id)
        
        # 检查是否已被锁定
        if norm_path in self._locks:
            existing_lock = self._locks[norm_path]
            return False, f"文件已被锁定 - 锁定者: {existing_lock.locker_name}, 等级: {existing_lock.level}"
        
        # 检查父目录是否被锁定
        parent_lock = self._find_parent_lock(norm_path)
        if parent_lock:
            return False, f"父目录已被锁定 - 路径: {parent_lock.path}, 锁定者: {parent_lock.locker_name}, 等级: {parent_lock.level}"
        
        # 检查子文件/目录是否被锁定
        child_locks = self._find_child_locks(norm_path)
        if child_locks:
            child_paths = [lock.path for lock in child_locks]
            return False, f"子路径已被锁定: {child_paths}"
        
        # 创建锁
        lock = FileLock(
            path=norm_path,
            level=level,
            locker_name=locker_name,
            locked_at=time.time(),
            task_id=task_id
        )
        
        self._locks[norm_path] = lock
        self._save_locks()
        
        global_logger.info(f"文件已锁定: {norm_path} by {locker_name} (level {level})")
        return True, f"成功锁定文件: {norm_path}"
    
    def unlock_file(self, file_path: str, unlocker_name: str, unlocker_level: int, task_id: str) -> Tuple[bool, str]:
        """
        解锁文件或目录
        
        Args:
            file_path: 文件路径
            unlocker_name: 解锁者名称
            unlocker_level: 解锁者等级
            task_id: 任务ID
            
        Returns:
            (成功标志, 消息)
        """
        norm_path = self._normalize_path(file_path, task_id)
        
        if norm_path not in self._locks:
            return False, f"文件未被锁定: {norm_path}"
        
        lock = self._locks[norm_path]
        
        # 高等级可以无条件解锁低等级
        if unlocker_level > lock.level:
            del self._locks[norm_path]
            self._save_locks()
            global_logger.info(f"高等级解锁: {norm_path} by {unlocker_name} (level {unlocker_level} > {lock.level})")
            return True, f"成功解锁文件: {norm_path} (高等级解锁)"
        
        # 同等级或低等级需要验证名称
        if unlocker_name == lock.locker_name:
            del self._locks[norm_path]
            self._save_locks()
            global_logger.info(f"名称匹配解锁: {norm_path} by {unlocker_name}")
            return True, f"成功解锁文件: {norm_path} (名称匹配)"
        
        return False, f"解锁失败: 权限不足或名称不匹配 (需要等级 > {lock.level} 或名称 = '{lock.locker_name}')"
    
    def check_access(self, file_path: str, task_id: str) -> Tuple[bool, Optional[FileLock]]:
        """
        检查文件访问权限
        
        Returns:
            (可访问标志, 锁信息)
        """
        norm_path = self._normalize_path(file_path, task_id)
        
        # 检查直接锁定
        if norm_path in self._locks:
            return False, self._locks[norm_path]
        
        # 检查父目录锁定
        parent_lock = self._find_parent_lock(norm_path)
        if parent_lock:
            return False, parent_lock
        
        return True, None
    
    def _find_parent_lock(self, file_path: str) -> Optional[FileLock]:
        """查找父目录锁"""
        path_parts = Path(file_path).parts
        
        for i in range(len(path_parts) - 1, 0, -1):
            parent_path = str(Path(*path_parts[:i]))
            if parent_path in self._locks:
                return self._locks[parent_path]
        
        return None
    
    def _find_child_locks(self, dir_path: str) -> List[FileLock]:
        """查找子路径锁"""
        child_locks = []
        dir_path_obj = Path(dir_path)
        
        for locked_path, lock in self._locks.items():
            locked_path_obj = Path(locked_path)
            try:
                # 检查是否是子路径
                locked_path_obj.relative_to(dir_path_obj)
                child_locks.append(lock)
            except ValueError:
                # 不是子路径
                continue
        
        return child_locks
    
    def list_locks(self, task_id: Optional[str] = None) -> List[FileLock]:
        """
        列出所有锁
        
        Args:
            task_id: 可选，只列出特定任务的锁
            
        Returns:
            锁列表
        """
        if task_id:
            return [lock for lock in self._locks.values() if lock.task_id == task_id]
        return list(self._locks.values())
    
    def get_lock_info(self, file_path: str, task_id: str) -> Optional[FileLock]:
        """获取特定文件的锁信息"""
        norm_path = self._normalize_path(file_path, task_id)
        return self._locks.get(norm_path)
    
    def clear_task_locks(self, task_id: str) -> int:
        """清理特定任务的所有锁"""
        removed_count = 0
        paths_to_remove = []
        
        for path, lock in self._locks.items():
            if lock.task_id == task_id:
                paths_to_remove.append(path)
        
        for path in paths_to_remove:
            del self._locks[path]
            removed_count += 1
        
        if removed_count > 0:
            self._save_locks()
            global_logger.info(f"已清理任务 {task_id} 的 {removed_count} 个锁")
        
        return removed_count 