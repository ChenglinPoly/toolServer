import asyncio
from typing import Optional
from pathlib import Path
from tools.base_tool import LocalTool
from utils.response import ToolResponse
from utils.human_task_manager import HumanTaskManager
from utils.logger import global_logger


class HumanInLoopTool(LocalTool):
    """人机交互工具 - 创建人类任务并等待完成"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "human_in_loop"
        self.description = "创建人类任务并等待完成，用于需要人工干预的场景"
        self.version = "1.0.0"
        self._human_task_manager: Optional[HumanTaskManager] = None
    
    def _get_human_task_manager(self, workspace_path: Path) -> HumanTaskManager:
        """获取人类任务管理器实例"""
        if self._human_task_manager is None:
            self._human_task_manager = HumanTaskManager(workspace_path)
        return self._human_task_manager
    
    async def execute(self, task_id: str, human_task: str, 
                     workspace_path: Path, timeout: Optional[float] = None, 
                     check_interval: float = 5.0) -> ToolResponse:
        """
        执行人机交互工具
        
        Args:
            task_id: 任务ID
            human_task: 人类任务描述
            workspace_path: 工作空间路径
            timeout: 超时时间（秒），None 表示无限等待
            check_interval: 检查间隔（秒）
            
        Returns:
            ToolResponse: 执行结果
        """
        try:
            if not human_task or not human_task.strip():
                return ToolResponse(
                    success=False,
                    error="human_task 参数不能为空"
                )
            
            # 获取人类任务管理器
            human_task_manager = self._get_human_task_manager(workspace_path)
            
            # 创建人类任务
            human_task_id = human_task_manager.create_human_task(task_id, human_task.strip())
            
            global_logger.info(f"Created human task {human_task_id}, waiting for completion...")
            
            # 等待任务完成
            completed_task = await human_task_manager.wait_for_completion(
                task_id=task_id,
                human_task_id=human_task_id,
                timeout=timeout,
                check_interval=check_interval
            )
            
            if completed_task is None:
                return ToolResponse(
                    success=False,
                    error=f"人类任务 {human_task_id} 超时或不存在",
                    data={
                        "human_task_id": human_task_id,
                        "task_id": task_id,
                        "human_task": human_task,
                        "status": "timeout_or_not_found"
                    }
                )
            
            # 返回完成的任务信息
            return ToolResponse(
                success=True,
                data={
                    "human_task_id": completed_task.human_task_id,
                    "task_id": completed_task.task_id,
                    "human_task": completed_task.human_task,
                    "completed": completed_task.completed,
                    "result": completed_task.result,
                    "created_at": completed_task.created_at,
                    "completed_at": completed_task.completed_at,
                    "message": "人类任务已完成"
                }
            )
            
        except Exception as e:
            global_logger.error(f"Human in loop tool execution failed: {str(e)}")
            return ToolResponse(
                success=False,
                error=f"执行人机交互工具时发生错误: {str(e)}"
            ) 