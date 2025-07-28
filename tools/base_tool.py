from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from utils.response import ToolResponse
from pathlib import Path


class BaseTool(ABC):
    """工具基类，定义统一的工具接口"""
    
    def __init__(self):
        self.tool_name = self.__class__.__name__.lower().replace('tool', '')
        self.description = ""
        self.version = "1.0.0"
    
    @abstractmethod
    async def execute(self, task_id: str, **params) -> ToolResponse:
        """
        执行工具
        
        Args:
            task_id: 任务ID
            **params: 工具参数
            
        Returns:
            ToolResponse: 执行结果
        """
        pass
    
    def get_task_path(self, task_id: str, workspace_path: Path) -> Path:
        """获取任务路径"""
        return workspace_path / "tasks" / task_id
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "name": self.tool_name,
            "description": self.description,
            "version": self.version,
            "class": self.__class__.__name__
        }


class LocalTool(BaseTool):
    """本地工具基类"""
    
    def __init__(self):
        super().__init__()
        self.tool_type = "local"


class RemoteTool(BaseTool):
    """远程工具基类"""
    
    def __init__(self, base_url: str):
        super().__init__()
        self.tool_type = "remote"
        self.base_url = base_url 