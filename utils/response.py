from datetime import datetime
from typing import Any, Optional, Dict
from pydantic import BaseModel
import time


class ToolResponse(BaseModel):
    """统一的工具响应格式"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = None
    execution_time: Optional[float] = None
    task_id: Optional[str] = None
    tool_name: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)
    
    def set_execution_time(self, start_time: float):
        """设置执行时间"""
        self.execution_time = time.time() - start_time
        
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolRequest(BaseModel):
    """统一的工具请求格式"""
    task_id: str
    tool_name: str
    params: Dict[str, Any] = {}
    multimodal_inputs: Optional[Dict[str, Any]] = None
