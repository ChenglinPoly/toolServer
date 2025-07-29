import asyncio
from pathlib import Path
from typing import Dict, Any, List
from tools.base_tool import LocalTool
from utils.response import ToolResponse
from utils.lock_manager import LockManager, FileLock, get_global_lock_manager
from utils.lock_decorator import bypass_lock_check
import time

class FileLockTool(LocalTool):
    """文件锁定工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_lock"
        self.description = "锁定文件或目录，防止其他操作修改。支持等级制锁定系统"
        self.version = "1.0.0"
    
    @bypass_lock_check
    async def execute(self, task_id: str, workspace_path: Path, **params) -> ToolResponse:
        """
        执行文件锁定
        
        参数:
        - file_path: 要锁定的文件或目录路径
        - level: 锁等级 (数字越大权限越高，默认为1)
        - locker_name: 上锁者名称 (必需)
        """
        try:
            file_path = params.get('file_path')
            level = params.get('level', 1)
            locker_name = params.get('locker_name')
            
            if not file_path:
                return ToolResponse(
                    success=False,
                    error="缺少必需参数: file_path",
                    data={}
                )
            
            if not locker_name:
                return ToolResponse(
                    success=False,
                    error="缺少必需参数: locker_name",
                    data={}
                )
            
            if not isinstance(level, int) or level < 1:
                return ToolResponse(
                    success=False,
                    error="level必须是大于0的整数",
                    data={}
                )
            
            # 获取LockManager实例
            lock_manager = get_global_lock_manager()
            if lock_manager is None:
                return ToolResponse(
                    success=False,
                    error="锁管理器未初始化",
                    data={}
                )
            
            # 执行锁定
            success, message = lock_manager.lock_file(file_path, level, locker_name, task_id)
            
            return ToolResponse(
                success=success,
                error=None if success else message,
                data={
                    "file_path": file_path,
                    "level": level,
                    "locker_name": locker_name,
                    "locked": success,
                    "message": message
                }
            )
            
        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"锁定文件失败: {str(e)}",
                data={}
            )

class FileUnlockTool(LocalTool):
    """文件解锁工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_unlock"
        self.description = "解锁文件或目录。高等级可无条件解锁低等级，同等级需要提供正确的上锁者名称"
        self.version = "1.0.0"
    
    @bypass_lock_check
    async def execute(self, task_id: str, workspace_path: Path, **params) -> ToolResponse:
        """
        执行文件解锁
        
        参数:
        - file_path: 要解锁的文件或目录路径
        - unlocker_name: 解锁者名称 (必需)
        - unlocker_level: 解锁者等级 (默认为1)
        """
        try:
            file_path = params.get('file_path')
            unlocker_name = params.get('unlocker_name')
            unlocker_level = params.get('unlocker_level', 1)
            
            if not file_path:
                return ToolResponse(
                    success=False,
                    error="缺少必需参数: file_path",
                    data={}
                )
            
            if not unlocker_name:
                return ToolResponse(
                    success=False,
                    error="缺少必需参数: unlocker_name",
                    data={}
                )
            
            if not isinstance(unlocker_level, int) or unlocker_level < 1:
                return ToolResponse(
                    success=False,
                    error="unlocker_level必须是大于0的整数",
                    data={}
                )
            
            # 获取LockManager实例
            lock_manager = get_global_lock_manager()
            if lock_manager is None:
                return ToolResponse(
                    success=False,
                    error="锁管理器未初始化",
                    data={}
                )
            
            # 执行解锁
            success, message = lock_manager.unlock_file(file_path, unlocker_name, unlocker_level, task_id)
            
            return ToolResponse(
                success=success,
                error=None if success else message,
                data={
                    "file_path": file_path,
                    "unlocker_name": unlocker_name,
                    "unlocker_level": unlocker_level,
                    "unlocked": success,
                    "message": message
                }
            )
            
        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"解锁文件失败: {str(e)}",
                data={}
            )

class ListLocksTool(LocalTool):
    """列出文件锁工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "list_locks"
        self.description = "列出当前所有文件锁或特定任务的文件锁"
        self.version = "1.0.0"
    
    @bypass_lock_check
    async def execute(self, task_id: str, workspace_path: Path, **params) -> ToolResponse:
        """
        列出文件锁
        
        参数:
        - filter_task_id: 可选，只显示特定任务的锁 (默认显示当前任务的锁)
        - show_all: 是否显示所有任务的锁 (默认为False)
        """
        try:
            filter_task_id = params.get('filter_task_id', task_id)
            show_all = params.get('show_all', False)
            
            # 获取LockManager实例
            lock_manager = get_global_lock_manager()
            if lock_manager is None:
                return ToolResponse(
                    success=False,
                    error="锁管理器未初始化",
                    data={}
                )
            
            # 获取锁列表
            if show_all:
                locks = lock_manager.list_locks()
            else:
                locks = lock_manager.list_locks(filter_task_id)
            
            # 格式化锁信息
            locks_data = []
            for lock in locks:
                lock_info = {
                    "path": lock.path,
                    "level": lock.level,
                    "locker_name": lock.locker_name,
                    "task_id": lock.task_id,
                    "locked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(lock.locked_at)),
                    "locked_at_timestamp": lock.locked_at
                }
                locks_data.append(lock_info)
            
            return ToolResponse(
                success=True,
                error=None,
                data={
                    "locks": locks_data,
                    "count": len(locks_data),
                    "filter_task_id": filter_task_id if not show_all else None,
                    "show_all": show_all,
                    "message": f"找到 {len(locks_data)} 个文件锁"
                }
            )
            
        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"列出文件锁失败: {str(e)}",
                data={}
            )

class CheckLockTool(LocalTool):
    """检查文件锁状态工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "check_lock"
        self.description = "检查特定文件或目录的锁状态"
        self.version = "1.0.0"
    
    @bypass_lock_check
    async def execute(self, task_id: str, workspace_path: Path, **params) -> ToolResponse:
        """
        检查文件锁状态
        
        参数:
        - file_path: 要检查的文件或目录路径
        """
        try:
            file_path = params.get('file_path')
            
            if not file_path:
                return ToolResponse(
                    success=False,
                    error="缺少必需参数: file_path",
                    data={}
                )
            
            # 获取LockManager实例
            lock_manager = get_global_lock_manager()
            if lock_manager is None:
                return ToolResponse(
                    success=False,
                    error="锁管理器未初始化",
                    data={}
                )
            
            # 检查访问权限
            can_access, lock_info = lock_manager.check_access(file_path, task_id)
            
            result_data = {
                "file_path": file_path,
                "can_access": can_access,
                "is_locked": not can_access
            }
            
            if lock_info:
                result_data["lock_info"] = {
                    "path": lock_info.path,
                    "level": lock_info.level,
                    "locker_name": lock_info.locker_name,
                    "task_id": lock_info.task_id,
                    "locked_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(lock_info.locked_at)),
                    "locked_at_timestamp": lock_info.locked_at
                }
            
            message = "文件可访问" if can_access else f"文件被锁定 - 锁定者: {lock_info.locker_name}, 等级: {lock_info.level}"
            result_data["message"] = message
            
            return ToolResponse(
                success=True,
                error=None,
                data=result_data
            )
            
        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"检查文件锁状态失败: {str(e)}",
                data={}
            ) 