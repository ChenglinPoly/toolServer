import functools
from typing import Callable, Any
from utils.response import ToolResponse
from utils.logger import global_logger

def require_file_access(*file_path_params):
    """
    文件访问权限装饰器
    
    Args:
        *file_path_params: 参数名列表，指定哪些参数包含文件路径
                          如果为空，默认检查 'file_path' 参数
    """
    if not file_path_params:
        file_path_params = ('file_path',)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, task_id: str, **params) -> Any:
            try:
                # 获取LockManager实例
                from utils.lock_manager import get_global_lock_manager
                lock_manager = get_global_lock_manager()
                if lock_manager is None:
                    # 如果没有锁管理器，直接执行原函数
                    return await func(self, task_id, **params)
                
                # 检查所有指定的文件路径参数
                for param_name in file_path_params:
                    if param_name in params:
                        file_path = params[param_name]
                        if file_path and file_path.strip():  # 只检查非空且非空白的路径
                            can_access, lock_info = lock_manager.check_access(file_path, task_id)
                            
                            if not can_access:
                                global_logger.warning(
                                    f"文件访问被拒绝: {file_path} - 锁定者: {lock_info.locker_name}, "
                                    f"等级: {lock_info.level}, 工具: {self.tool_name}"
                                )
                                return ToolResponse(
                                    success=False,
                                    message=f"文件访问被拒绝: {file_path} - 文件已被锁定 "
                                           f"(锁定者: {lock_info.locker_name}, 等级: {lock_info.level})",
                                    data={
                                        "locked_file": file_path,
                                        "lock_info": {
                                            "locker_name": lock_info.locker_name,
                                            "level": lock_info.level,
                                            "locked_path": lock_info.path,
                                            "task_id": lock_info.task_id
                                        }
                                    }
                                )
                
                # 如果所有文件都可以访问，执行原函数
                return await func(self, task_id, **params)
                
            except Exception as e:
                global_logger.error(f"锁检查装饰器异常: {e}")
                # 发生异常时，继续执行原函数（降级处理）
                return await func(self, task_id, **params)
        
        return wrapper
    return decorator

def bypass_lock_check(func: Callable) -> Callable:
    """
    绕过锁检查装饰器
    用于标记不需要进行锁检查的工具方法
    """
    func._bypass_lock_check = True
    return func

def require_write_access(*file_path_params):
    """
    写入访问权限装饰器（require_file_access的别名）
    用于需要写入权限的操作
    """
    return require_file_access(*file_path_params)

def require_read_access(*file_path_params):
    """
    读取访问权限装饰器
    目前与require_file_access相同，但可以在未来扩展为不同的权限检查
    """
    return require_file_access(*file_path_params) 