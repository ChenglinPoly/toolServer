#!/usr/bin/env python3
"""
Tool Server 代理服务器模板
用于快速创建兼容的外挂代理工具服务器

使用方法：
1. 复制此模板文件
2. 修改 PROXY_TOOLS 列表，添加你的工具
3. 在 execute_tool 函数中实现具体逻辑
4. 运行服务器：python proxy_server_template.py --port 8892

API要求：
- GET  /api/tools          - 返回工具列表
- POST /api/tool/execute   - 执行工具
- GET  /health             - 健康检查
"""

import time
import asyncio
import base64
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx


# =============================================================================
# 请求/响应模型 - 必须与主服务器保持一致
# =============================================================================

class ToolRequest(BaseModel):
    """工具请求模型"""
    task_id: str
    tool_name: str
    params: Dict[str, Any] = {}


class ToolResponse(BaseModel):
    """工具响应模型"""
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


# =============================================================================
# 配置区域 - 修改这里添加你的工具
# =============================================================================

# 工具列表 - 添加你要提供的工具名称
PROXY_TOOLS = [
    "example_hello",
    "example_calculator", 
    "example_file_processor",
    "example_data_analyzer",
    "generate_timestamp_file",  # 🆕 生成时间戳文件并上传
    "execute_code_local",       # 🆕 本地代码执行工具
    "pip_local",                # 🆕 本地pip包安装工具
    # 在这里添加更多工具...
]

# 服务器信息
SERVER_INFO = {
    "name": "My Custom Proxy Server",
    "version": "1.0.0",
    "description": "基于Tool Server模板的自定义代理服务器",
    "author": "Your Name"
}

# 主服务器配置
MAIN_SERVER_URL = "http://localhost:8001"  # 主服务器地址

# 工作空间配置
WORKSPACE_PATH = "/workspace"  # Docker挂载的workspace路径（默认）
# 如果代理服务器也在Docker中运行，可能需要调整路径
# 如果代理服务器在宿主机运行，workspace路径应该指向Docker挂载的实际目录

# 自动检测工作空间路径
def get_workspace_path():
    """自动检测工作空间路径"""
    # 检查当前目录下是否有workspace文件夹（本地开发）
    local_workspace = Path("./workspace")
    if local_workspace.exists():
        return str(local_workspace.absolute())
    
    # 检查Docker标准路径
    docker_workspace = Path("/workspace")
    if docker_workspace.exists():
        return str(docker_workspace)
    
    # 默认返回配置的路径
    return WORKSPACE_PATH

# 更新工作空间路径
WORKSPACE_PATH = get_workspace_path()


# =============================================================================
# 工具实现区域 - 实现你的具体工具逻辑
# =============================================================================

async def execute_tool(tool_name: str, task_id: str, params: Dict[str, Any]) -> ToolResponse:
    """
    工具执行函数 - 在这里实现你的工具逻辑
    
    Args:
        tool_name: 工具名称
        task_id: 任务ID
        params: 工具参数
        
    Returns:
        ToolResponse: 执行结果
    """
    start_time = time.time()
    
    try:
        # 根据工具名称分发到不同的处理函数
        if tool_name == "example_hello":
            result = await _example_hello(params)
            
        elif tool_name == "example_calculator":
            result = await _example_calculator(params)
            
        elif tool_name == "example_file_processor":
            result = await _example_file_processor(params)
            
        elif tool_name == "example_data_analyzer":
            result = await _example_data_analyzer(params)
            
        elif tool_name == "generate_timestamp_file":
            result = await _generate_timestamp_file(task_id, params)
            
        elif tool_name == "execute_code_local":
            result = await _execute_code_local(task_id, params)
            
        elif tool_name == "pip_local":
            result = await _pip_local(task_id, params)
            
        # 在这里添加更多工具的处理逻辑...
        # elif tool_name == "your_new_tool":
        #     result = await _your_new_tool(params)
            
        else:
            return ToolResponse(
                success=False,
                error=f"Unknown tool: {tool_name}",
                task_id=task_id,
                tool_name=tool_name,
                execution_time=time.time() - start_time
            )
        
        return ToolResponse(
            success=True,
            data=result,
            task_id=task_id,
            tool_name=tool_name,
            execution_time=time.time() - start_time
        )
        
    except Exception as e:
        return ToolResponse(
            success=False,
            error=str(e),
            task_id=task_id,
            tool_name=tool_name,
            execution_time=time.time() - start_time
        )


# =============================================================================
# 具体工具实现示例 - 参考这些例子实现你的工具
# =============================================================================

async def _example_hello(params: Dict[str, Any]) -> Dict[str, Any]:
    """示例：简单问候工具"""
    name = params.get("name", "World")
    message = params.get("message", "Hello")
    
    return {
        "greeting": f"{message}, {name}!",
        "timestamp": datetime.now().isoformat(),
        "server": SERVER_INFO["name"]
    }


async def _example_calculator(params: Dict[str, Any]) -> Dict[str, Any]:
    """示例：简单计算器"""
    operation = params.get("operation", "add")
    a = params.get("a", 0)
    b = params.get("b", 0)
    
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None
    }
    
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    
    result = operations[operation](a, b)
    
    if result is None:
        raise ValueError("Division by zero")
    
    return {
        "operation": operation,
        "operands": {"a": a, "b": b},
        "result": result,
        "expression": f"{a} {operation} {b} = {result}"
    }


async def _example_file_processor(params: Dict[str, Any]) -> Dict[str, Any]:
    """示例：文件处理工具"""
    content = params.get("content", "")
    action = params.get("action", "count_words")
    
    if action == "count_words":
        words = len(content.split())
        chars = len(content)
        lines = len(content.splitlines())
        
        return {
            "action": action,
            "statistics": {
                "words": words,
                "characters": chars,
                "lines": lines
            },
            "content_preview": content[:100] + "..." if len(content) > 100 else content
        }
    
    elif action == "reverse":
        return {
            "action": action,
            "original": content,
            "reversed": content[::-1]
        }
    
    elif action == "uppercase":
        return {
            "action": action,
            "original": content,
            "result": content.upper()
        }
    
    else:
        raise ValueError(f"Unsupported action: {action}")


async def _example_data_analyzer(params: Dict[str, Any]) -> Dict[str, Any]:
    """示例：数据分析工具"""
    data = params.get("data", [])
    analysis_type = params.get("type", "basic_stats")
    
    if not data:
        raise ValueError("No data provided")
    
    if analysis_type == "basic_stats":
        return {
            "type": analysis_type,
            "count": len(data),
            "sum": sum(data) if all(isinstance(x, (int, float)) for x in data) else None,
            "average": sum(data) / len(data) if all(isinstance(x, (int, float)) for x in data) else None,
            "min": min(data) if data else None,
            "max": max(data) if data else None,
            "unique_count": len(set(data))
        }
    
    elif analysis_type == "frequency":
        from collections import Counter
        freq = Counter(data)
        return {
            "type": analysis_type,
            "frequency": dict(freq.most_common()),
            "most_common": freq.most_common(1)[0] if freq else None,
            "unique_items": len(freq)
        }
    
    else:
        raise ValueError(f"Unsupported analysis type: {analysis_type}")


# =============================================================================
# 与主服务器交互的工具 - 展示跨服务调用
# =============================================================================

async def call_main_server_tool(task_id: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用主服务器的工具
    
    Args:
        task_id: 任务ID
        tool_name: 主服务器工具名称
        params: 工具参数
        
    Returns:
        主服务器返回的结果
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        request_data = {
            "task_id": task_id,
            "tool_name": tool_name,
            "params": params
        }
        
        response = await client.post(
            f"{MAIN_SERVER_URL}/api/tool/execute",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Main server error: {response.text}"
            )
        
        result = response.json()
        
        if not result.get("success", False):
            raise ValueError(f"Main server tool failed: {result.get('error', 'Unknown error')}")
        
        return result.get("data", {})


async def _generate_timestamp_file(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    示例：生成时间戳文件并上传到主服务器
    
    这个工具展示了代理服务器如何：
    1. 生成内容
    2. 调用主服务器的file_upload工具
    3. 将文件保存到容器的workspace中
    """
    try:
        # 1. 生成时间戳内容
        now = datetime.now()
        filename = params.get("filename", f"timestamp_{now.strftime('%Y%m%d_%H%M%S')}.txt")
        
        content_lines = [
            f"时间戳文件 - 由代理服务器生成",
            f"生成时间: {now.isoformat()}",
            f"Unix时间戳: {now.timestamp()}",
            f"格式化时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')}",
            f"任务ID: {task_id}",
            f"代理服务器: {SERVER_INFO['name']} v{SERVER_INFO['version']}",
            "",
            "--- 系统信息 ---",
            f"生成工具: generate_timestamp_file",
            f"文件名: {filename}",
            f"编码: UTF-8",
            ""
        ]
        
        # 添加额外信息（如果有参数）
        if params.get("include_params", True):
            content_lines.extend([
                "--- 调用参数 ---",
                f"原始参数: {params}",
                ""
            ])
        
        content = "\n".join(content_lines)
        
        # 2. 将内容编码为base64（用于文件上传）
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        # 3. 调用主服务器的file_upload工具
        target_folder = params.get("target_folder", "")  # 获取目标文件夹参数
        upload_params = {
            "files": [
                {
                    "filename": filename,  # 修正字段名
                    "content": content_base64,
                    "is_base64": True  # 明确标记为base64编码
                }
            ],
            "target_path": target_folder  # 使用指定的目标文件夹
        }
        
        upload_result = await call_main_server_tool(task_id, "file_upload", upload_params)
        
        # 4. 返回结果
        return {
            "action": "generate_timestamp_file",
            "success": True,
            "generated_file": {
                "filename": filename,
                "size": len(content_bytes),
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "encoding": "UTF-8"
            },
            "upload_result": upload_result,
            "timestamp": now.isoformat(),
            "task_id": task_id,
            "proxy_server": SERVER_INFO["name"],
            "main_server_call": {
                "tool": "file_upload",
                "target_path": f"/workspace/tasks/{task_id}/{target_folder + '/' if target_folder else ''}{filename}",
                "success": True
            }
        }
        
    except Exception as e:
        # 如果出错，返回详细错误信息
        return {
            "action": "generate_timestamp_file", 
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "proxy_server": SERVER_INFO["name"]
        }


async def _execute_code_local(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    本地代码执行工具 - 直接在代理服务器本地执行Python代码
    
    这个工具展示了代理服务器如何：
    1. 访问Docker挂载的workspace文件夹
    2. 在本地执行Python代码
    3. 返回执行结果
    
    适用场景：
    - 需要在代理服务器环境中执行代码
    - 利用代理服务器的特殊Python包或环境
    - 绕过主服务器的虚拟环境限制
    """
    try:
        # 获取参数
        file_path = params.get("file_path")
        working_dir = params.get("working_dir", "")
        timeout = params.get("timeout", 300)
        python_executable = params.get("python_executable", sys.executable)
        
        if not file_path:
            return {
                "success": False,
                "error": "file_path parameter is required",
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id
            }
        
        # 构建完整的文件路径
        workspace_path = Path(WORKSPACE_PATH)
        task_path = workspace_path / "tasks" / task_id
        full_file_path = task_path / file_path
        
        # 检查文件是否存在
        if not full_file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path} (full path: {full_file_path})",
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "workspace_info": {
                    "workspace_path": str(workspace_path),
                    "task_path": str(task_path),
                    "file_exists": full_file_path.exists(),
                    "workspace_exists": workspace_path.exists(),
                    "task_dir_exists": task_path.exists()
                }
            }
        
        # 设置工作目录，默认使用code_run（与主服务器execute_code一致）
        if working_dir:
            work_path = task_path / working_dir
        else:
            work_path = task_path / "code_run"
        
        # 确保工作目录存在
        work_path.mkdir(parents=True, exist_ok=True)
        
        # 执行Python代码
        start_time = time.time()
        
        try:
            # 使用异步子进程执行
            process = await asyncio.create_subprocess_exec(
                python_executable, str(full_file_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_path)
            )
            
            # 等待执行完成，带超时
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "data": {
                    "exit_code": process.returncode,
                    "stdout": stdout.decode('utf-8') if stdout else "",
                    "stderr": stderr.decode('utf-8') if stderr else "",
                    "execution_time": execution_time,
                    "file_path": file_path,
                    "working_directory": str(work_path),
                    "python_executable": python_executable
                },
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "proxy_server": SERVER_INFO["name"],
                "execution_location": "proxy_server_local"
            }
            
        except asyncio.TimeoutError:
            # 超时处理
            try:
                process.kill()
                await process.wait()
            except:
                pass
            
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": f"Code execution timeout after {timeout} seconds",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "proxy_server": SERVER_INFO["name"]
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": f"Code execution failed: {str(e)}",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "proxy_server": SERVER_INFO["name"]
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "proxy_server": SERVER_INFO["name"]
        }


async def _pip_local(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    本地pip包安装工具 - 在代理服务器本地环境安装Python包
    
    这个工具展示了代理服务器如何：
    1. 在本地Python环境中安装包
    2. 支持多个包的批量安装
    3. 与主服务器的pip_install工具保持API兼容
    
    适用场景：
    - 在代理服务器环境中安装特殊包
    - 利用代理服务器的网络环境安装包
    - 为execute_code_local准备依赖环境
    """
    try:
        # 获取参数
        packages = params.get("packages", [])
        requirements_file = params.get("requirements_file")
        python_executable = params.get("python_executable", sys.executable)
        
        if not packages and not requirements_file:
            return {
                "success": False,
                "error": "Either 'packages' list or 'requirements_file' parameter is required",
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id
            }
        
        # 确保packages是列表
        if isinstance(packages, str):
            packages = [packages]
        
        # 构建pip路径
        pip_executable = python_executable.replace("python", "pip")
        # 如果pip路径不存在，尝试使用 python -m pip
        use_module_pip = False
        try:
            process = await asyncio.create_subprocess_exec(
                pip_executable, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                use_module_pip = True
        except:
            use_module_pip = True
        
        results = []
        
        # 处理requirements文件
        if requirements_file:
            workspace_path = Path(WORKSPACE_PATH)
            task_path = workspace_path / "tasks" / task_id
            req_file_path = task_path / requirements_file
            
            if req_file_path.exists():
                try:
                    if use_module_pip:
                        cmd = [python_executable, "-m", "pip", "install", "-r", str(req_file_path)]
                    else:
                        cmd = [pip_executable, "install", "-r", str(req_file_path)]
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    results.append({
                        "source": f"requirements_file: {requirements_file}",
                        "success": process.returncode == 0,
                        "stdout": stdout.decode('utf-8') if stdout else "",
                        "stderr": stderr.decode('utf-8') if stderr else ""
                    })
                except Exception as e:
                    results.append({
                        "source": f"requirements_file: {requirements_file}",
                        "success": False,
                        "error": str(e)
                    })
            else:
                results.append({
                    "source": f"requirements_file: {requirements_file}",
                    "success": False,
                    "error": f"Requirements file not found: {req_file_path}"
                })
        
        # 处理单个包
        for package in packages:
            try:
                if use_module_pip:
                    cmd = [python_executable, "-m", "pip", "install", package]
                else:
                    cmd = [pip_executable, "install", package]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                results.append({
                    "package": package,
                    "success": process.returncode == 0,
                    "stdout": stdout.decode('utf-8') if stdout else "",
                    "stderr": stderr.decode('utf-8') if stderr else ""
                })
            except Exception as e:
                results.append({
                    "package": package,
                    "success": False,
                    "error": str(e)
                })
        
        all_success = all(r.get("success", False) for r in results)
        
        return {
            "success": all_success,
            "data": {
                "results": results,
                "python_executable": python_executable,
                "pip_executable": pip_executable if not use_module_pip else f"{python_executable} -m pip",
                "total_packages": len(packages),
                "successful_installs": sum(1 for r in results if r.get("success", False)),
                "failed_installs": sum(1 for r in results if not r.get("success", False))
            },
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "proxy_server": SERVER_INFO["name"],
            "execution_location": "proxy_server_local"
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "proxy_server": SERVER_INFO["name"]
        }


# =============================================================================
# FastAPI 应用设置
# =============================================================================

app = FastAPI(
    title=SERVER_INFO["name"],
    description=SERVER_INFO["description"],
    version=SERVER_INFO["version"]
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API 端点 - 必须实现这些端点以兼容主服务器
# =============================================================================

@app.get("/")
async def root():
    """根端点 - 服务器信息"""
    return {
        "message": f"{SERVER_INFO['name']} is running",
        "tools": PROXY_TOOLS,
        "server_info": SERVER_INFO,
        "api_version": "v1",
        "compatible_with": "Tool Server Uni v1.1+"
    }


@app.get("/health")
async def health_check():
    """健康检查端点 - 必需"""
    return {
        "status": "healthy",
        "service": SERVER_INFO["name"],
        "version": SERVER_INFO["version"],
        "tools_count": len(PROXY_TOOLS),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/tools")
async def list_tools():
    """列出所有可用工具 - 必需"""
    return {
        "success": True,
        "data": PROXY_TOOLS,
        "count": len(PROXY_TOOLS),
        "server": SERVER_INFO["name"]
    }


@app.post("/api/tool/execute")
async def execute_tool_endpoint(request: ToolRequest):
    """执行工具 - 必需的主要端点"""
    if request.tool_name not in PROXY_TOOLS:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' not found. Available tools: {PROXY_TOOLS}"
        )
    
    try:
        result = await execute_tool(request.tool_name, request.task_id, request.params)
        return result
    except Exception as e:
        return ToolResponse(
            success=False,
            error=f"Tool execution failed: {str(e)}",
            task_id=request.task_id,
            tool_name=request.tool_name
        )


@app.get("/api/server/info")
async def get_server_info():
    """获取服务器详细信息 - 可选"""
    return {
        "success": True,
        "data": {
            **SERVER_INFO,
            "tools": PROXY_TOOLS,
            "api_endpoints": [
                "GET /",
                "GET /health", 
                "GET /api/tools",
                "POST /api/tool/execute",
                "GET /api/server/info"
            ],
            "uptime": "运行中",
            "python_version": "3.8+",
            "fastapi_version": "0.100+"
        }
    }


# =============================================================================
# 服务器启动
# =============================================================================

def main():
    """启动服务器"""
    import argparse
    
    parser = argparse.ArgumentParser(description=f'{SERVER_INFO["name"]} - Tool Server Compatible Proxy')
    parser.add_argument('--port', type=int, default=8892, help='服务器端口 (默认: 8892)')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机 (默认: 0.0.0.0)')
    parser.add_argument('--reload', action='store_true', help='启用自动重载 (开发模式)')
    
    args = parser.parse_args()
    
    print(f"🚀 启动 {SERVER_INFO['name']} v{SERVER_INFO['version']}")
    print(f"📡 监听地址: http://{args.host}:{args.port}")
    print(f"🔧 可用工具: {len(PROXY_TOOLS)} 个")
    print(f"📋 工具列表: {', '.join(PROXY_TOOLS)}")
    print(f"📖 API文档: http://{args.host}:{args.port}/docs")
    print(f"💡 健康检查: http://{args.host}:{args.port}/health")
    print("-" * 60)
    
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main() 