import httpx
import asyncio
from typing import Dict, Any, Optional, List
from utils.response import ToolResponse
from utils.logger import global_logger


class ProxyTools:
    """通用工具代理服务（代理远程工具服务器）"""
    
    def __init__(self, proxy_base_url: str = "http://localhost:8892", timeout: float = 120.0):
        """
        初始化ProxyTools
        
        Args:
            proxy_base_url: 代理服务的基础URL，格式为 http://host:port
            timeout: 请求超时时间（秒）
        """
        self.proxy_base_url = proxy_base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.available_tools = set()
        global_logger.info(f"ProxyTools initialized with proxy service at {self.proxy_base_url}")
    
    async def discover_proxy_tools(self) -> List[str]:
        """发现代理服务器上可用的工具"""
        try:
            url = f"{self.proxy_base_url}/api/tools"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    tools = result.get("data", [])
                    self.available_tools = set(tools)
                    global_logger.info(f"Discovered {len(tools)} proxy tools: {tools}")
                    return tools
                else:
                    global_logger.warning(f"Failed to discover proxy tools: {result.get('error')}")
                    return []
            else:
                global_logger.warning(f"Proxy tools discovery failed: {response.status_code}")
                return []
                
        except Exception as e:
            global_logger.error(f"Failed to discover proxy tools: {str(e)}")
            return []
    
    async def execute_proxy_tool(self, task_id: str, tool_name: str, params: Dict[str, Any]) -> ToolResponse:
        """
        执行代理工具
        
        Args:
            task_id: 任务ID
            tool_name: 工具名称
            params: 工具参数（不包含task_id）
            
        Returns:
            ToolResponse: 代理服务器的响应
        """
        try:
            url = f"{self.proxy_base_url}/api/tool/execute"
            
            # 构建请求体，完全按照本地格式
            request_data = {
                "task_id": task_id,
                "tool_name": tool_name,
                "params": params
            }
            
            global_logger.debug(f"Proxying tool {tool_name} to {url}")
            
            response = await self.client.post(url, json=request_data)
            
            if response.status_code == 200:
                result = response.json()
                # 直接返回代理服务器的响应，不做任何转换
                return ToolResponse(**result)
            else:
                error_msg = f"Proxy tool execution failed: {response.status_code}"
                if response.text:
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', response.text)}"
                    except:
                        error_msg += f" - {response.text}"
                
                global_logger.error(error_msg)
                return ToolResponse(success=False, error=error_msg)
                
        except httpx.TimeoutException:
            error_msg = f"Proxy tool {tool_name} request timeout"
            global_logger.error(error_msg)
            return ToolResponse(success=False, error=error_msg)
        except httpx.ConnectError:
            error_msg = f"Cannot connect to proxy service: {self.proxy_base_url}"
            global_logger.error(error_msg)
            return ToolResponse(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"Proxy tool {tool_name} execution failed: {str(e)}"
            global_logger.error(error_msg)
            return ToolResponse(success=False, error=error_msg)
    
    async def health_check(self) -> bool:
        """检查代理服务器健康状态"""
        try:
            url = f"{self.proxy_base_url}/health"
            response = await self.client.get(url, timeout=10.0)
            return response.status_code == 200
        except Exception as e:
            global_logger.warning(f"Proxy health check failed: {str(e)}")
            return False
    
    async def get_proxy_info(self) -> Dict[str, Any]:
        """获取代理服务器信息"""
        try:
            url = f"{self.proxy_base_url}/"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get proxy info: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to get proxy info: {str(e)}"}
    
    def is_proxy_tool(self, tool_name: str) -> bool:
        """检查工具是否为代理工具"""
        return tool_name in self.available_tools
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose() 