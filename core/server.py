import os
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn

from core.task_manager import TaskManager
from core.tool_manager import ToolManager
from utils.response import ToolResponse, ToolRequest
from utils.logger import global_logger
from utils.lock_manager import LockManager

# 全局服务器实例，用于工具访问
server_instance = None


class ToolServer:
    """工具服务器 - 专注于路由和网络服务"""
    
    def __init__(self):
        self.app = FastAPI(title="Tool Server", version="2.0.0")
        self.task_manager: Optional[TaskManager] = None
        self.tool_manager: Optional[ToolManager] = None
        self.lock_manager: Optional[LockManager] = None
        self.workspace_path: Optional[Path] = None
        self.is_running = False
        
        # 设置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册API路由
        self._register_routes()
        
        # 添加全局异常处理
        self._register_exception_handlers()
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/")
        async def root():
            return {
                "message": "Tool Server is running",
                "tools": self.tool_manager.list_tools() if self.tool_manager else [],
                "version": "2.0.0"
            }
        
        @self.app.post("/api/tool/execute")
        async def execute_tool(request: ToolRequest):
            """执行工具"""
            start_time = time.time()
            
            try:
                # 检查工具管理器是否已初始化
                if not self.tool_manager:
                    raise HTTPException(status_code=500, detail="Tool manager not initialized")
                
                # 检查任务是否存在
                task_info = self.task_manager.get_task(request.task_id)
                
                # 执行工具
                result = await self.tool_manager.execute_tool(
                    tool_name=request.tool_name,
                    task_id=request.task_id,
                    **request.params
                )
                
                # 如果结果不是ToolResponse，包装它
                if not isinstance(result, ToolResponse):
                    result = ToolResponse(success=True, data=result)
                
                # 设置执行信息
                result.execution_time = time.time() - start_time
                result.task_id = request.task_id
                result.tool_name = request.tool_name
                
                # 记录日志
                if result.success:
                    task_info.logger.log_tool_success(
                        request.tool_name, 
                        result.data or {}, 
                        result.execution_time, 
                        request.params
                    )
                else:
                    task_info.logger.log_tool_error(
                        request.tool_name, 
                        result.error, 
                        result.execution_time, 
                        request.params
                    )
                
                return result
                
            except ValueError as e:
                # 工具不存在或任务不存在
                error_response = ToolResponse(
                    success=False,
                    error=str(e),
                    task_id=request.task_id,
                    tool_name=request.tool_name,
                    execution_time=time.time() - start_time
                )
                return error_response
                
            except Exception as e:
                # 其他错误
                error_response = ToolResponse(
                    success=False,
                    error=f"Internal server error: {str(e)}",
                    task_id=request.task_id,
                    tool_name=request.tool_name,
                    execution_time=time.time() - start_time
                )
                return error_response
        
        @self.app.post("/api/task/create")
        async def create_task(task_id: str, task_name: str, requirements: Optional[str] = None):
            """创建任务"""
            try:
                result = self.task_manager.create_task(task_id, task_name, requirements)
                return {"success": True, "data": result}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.delete("/api/task/{task_id}")
        async def delete_task(task_id: str):
            """删除任务"""
            try:
                result = self.task_manager.delete_task(task_id)
                return {"success": True, "data": result}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/task/list")
        async def list_tasks():
            """列出所有任务"""
            tasks = self.task_manager.list_tasks()
            return {"success": True, "data": tasks}
        
        @self.app.get("/api/task/{task_id}/status")
        async def get_task_status(task_id: str):
            """获取任务状态"""
            try:
                task_info = self.task_manager.get_task(task_id)
                return {
                    "success": True,
                    "data": {
                        "task_id": task_info.task_id,
                        "task_name": task_info.task_name,
                        "created_at": task_info.created_at.isoformat(),
                        "path": str(task_info.path)
                    }
                }
            except Exception as e:
                raise HTTPException(status_code=404, detail=str(e))
        
        @self.app.get("/api/tools")
        async def list_tools():
            """列出所有可用工具"""
            if not self.tool_manager:
                return {"success": False, "error": "Tool manager not initialized"}
            return {"success": True, "data": self.tool_manager.list_tools()}
        
        @self.app.get("/api/tools/info")
        async def get_tools_info():
            """获取工具详细信息"""
            if not self.tool_manager:
                return {"success": False, "error": "Tool manager not initialized"}
            return {"success": True, "data": self.tool_manager.get_tool_info()}
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {"status": "healthy", "service": "tool_server", "version": "2.0.0"}
    
    def _register_exception_handlers(self):
        """注册异常处理器"""
        
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            """处理JSON解析错误"""
            error_details = []
            for error in exc.errors():
                if error["type"] == "json_invalid":
                    error_details.append({
                        "type": "json_parse_error",
                        "message": "JSON格式错误，可能包含未转义的特殊字符",
                        "suggestion": "请使用file_upload工具上传包含特殊字符的文件内容",
                        "location": error.get("loc", []),
                        "input_preview": str(error.get("input", ""))[:100] + "..." if len(str(error.get("input", ""))) > 100 else str(error.get("input", ""))
                    })
                else:
                    error_details.append({
                        "type": error["type"],
                        "message": error["msg"],
                        "location": error.get("loc", []),
                        "input": error.get("input")
                    })
            
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error": "请求格式错误",
                    "error_type": "validation_error",
                    "details": error_details,
                    "suggestions": [
                        "服务器已自动处理常见的JSON特殊字符问题",
                        "如果仍有问题，请使用file_upload工具上传文件",
                        "或者将内容保存为本地文件后上传"
                    ]
                }
            )
    
    async def start_async(self, port: int = 8001, workspace_path: str = "./workspace", 
                         proxy_base_url: str = "http://localhost:8892"):
        """异步启动服务器（用于工具注册）"""
        self.workspace_path = Path(workspace_path).absolute()
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化任务管理器
        self.task_manager = TaskManager(str(self.workspace_path))
        
        # 初始化锁管理器
        self.lock_manager = LockManager(self.workspace_path)
        
        # 设置全局锁管理器实例
        from utils.lock_manager import set_global_lock_manager
        set_global_lock_manager(self.lock_manager)
        
        # 设置全局服务器实例（在工具注册之前，让工具能够访问）
        global server_instance
        server_instance = self
        
        # 初始化工具管理器
        self.tool_manager = ToolManager(self.workspace_path, proxy_base_url)
        
        # 注册所有工具（本地+代理）
        await self.tool_manager.register_all_tools()
        
        # 设置运行状态
        self.is_running = True
        
        global_logger.info(f"Tool Server ready on port {port}")
        global_logger.info(f"Workspace: {self.workspace_path}")
        global_logger.info(f"Available tools: {self.tool_manager.list_tools()}")
    
    def start(self, port: int = 8001, workspace_path: str = "./workspace", 
              proxy_base_url: str = "http://localhost:8892"):
        """启动服务器"""
        
        # 创建startup事件
        @self.app.on_event("startup")
        async def startup_event():
            await self.start_async(port, workspace_path, proxy_base_url)
        
        # 启动服务器
        global_logger.info(f"Starting Tool Server on port {port}")
        uvicorn.run(self.app, host="0.0.0.0", port=port)
    
    def stop(self):
        """停止服务器"""
        global_logger.info("Stopping Tool Server...")
        self.is_running = False
        
        # 关闭工具管理器的资源
        if self.tool_manager and self.tool_manager.proxy_tools_manager:
            import asyncio
            asyncio.create_task(self.tool_manager.proxy_tools_manager.client.aclose())
        
        global_logger.info("Tool Server stopped")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        global_logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)


def main():
    """主函数 - 支持Docker和本机运行"""
    import argparse
    
    # 自动检测运行环境，设置默认workspace路径
    if os.path.exists('/.dockerenv'):
        # Docker环境
        default_workspace = '/workspace'
        description = 'Tool Server - Docker容器版本'
    else:
        # 本机环境
        default_workspace = './workspace'
        description = 'Tool Server - 本机运行版本'
    
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--port', type=int, default=8001, help='服务器端口')
    parser.add_argument('--workspace', default=default_workspace, help='工作空间路径')
    parser.add_argument('--proxy-url', default='http://localhost:8892', help='代理服务地址')
    
    args = parser.parse_args()
    
    server = ToolServer()
    server.start(
        port=args.port,
        workspace_path=args.workspace,
        proxy_base_url=args.proxy_url
    )


if __name__ == "__main__":
    main() 