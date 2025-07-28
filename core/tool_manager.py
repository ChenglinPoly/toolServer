import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional
from tools.base_tool import BaseTool, LocalTool, RemoteTool
from tools.proxy_tools import ProxyTools
from utils.logger import global_logger


class ToolManager:
    """工具管理器 - 自动发现和注册工具"""
    
    def __init__(self, workspace_path: Path, proxy_base_url: str = "http://localhost:8892"):
        self.workspace_path = workspace_path
        self.proxy_base_url = proxy_base_url
        self.tools: Dict[str, BaseTool] = {}
        self.local_tools: Dict[str, LocalTool] = {}
        self.proxy_tools_manager: Optional[ProxyTools] = None
        self.proxy_tool_names: set = set()
        
        # 初始化代理工具管理器
        try:
            self.proxy_tools_manager = ProxyTools(proxy_base_url)
        except Exception as e:
            global_logger.warning(f"Failed to initialize proxy tools: {str(e)}")
    
    def discover_local_tools(self) -> Dict[str, LocalTool]:
        """自动发现tools文件夹下的所有本地工具"""
        discovered_tools = {}
        tools_dir = Path(__file__).parent.parent / "tools"
        
        if not tools_dir.exists():
            global_logger.warning(f"Tools directory not found: {tools_dir}")
            return discovered_tools
        
        # 扫描tools目录下的所有Python文件
        for py_file in tools_dir.glob("*.py"):
            if py_file.name.startswith("__") or py_file.name in ["base_tool.py", "proxy_tools.py"]:
                continue
            
            module_name = f"tools.{py_file.stem}"
            
            try:
                # 动态导入模块
                module = importlib.import_module(module_name)
                
                # 检查模块中的所有类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # 检查是否是LocalTool的子类且不是基类本身
                    if (issubclass(obj, LocalTool) and 
                        obj != LocalTool and 
                        obj != BaseTool and
                        hasattr(obj, '__module__') and 
                        obj.__module__ == module_name):
                        
                        try:
                            # 实例化工具
                            tool_instance = obj()
                            tool_name = tool_instance.tool_name
                            
                            if tool_name not in discovered_tools:
                                discovered_tools[tool_name] = tool_instance
                                global_logger.info(f"Discovered local tool: {tool_name} from {py_file.name}")
                            else:
                                global_logger.warning(f"Duplicate tool name: {tool_name}")
                                
                        except Exception as e:
                            global_logger.error(f"Failed to instantiate tool {name}: {str(e)}")
                            
            except Exception as e:
                global_logger.error(f"Failed to import module {module_name}: {str(e)}")
        
        return discovered_tools
    
    async def discover_proxy_tools(self) -> List[str]:
        """发现代理工具"""
        if not self.proxy_tools_manager:
            return []
        
        try:
            proxy_tools = await self.proxy_tools_manager.discover_proxy_tools()
            self.proxy_tool_names = set(proxy_tools)
            return proxy_tools
        except Exception as e:
            global_logger.error(f"Failed to discover proxy tools: {str(e)}")
            return []
    
    async def register_all_tools(self) -> None:
        """注册所有工具（本地+代理）"""
        # 发现并注册本地工具
        self.local_tools = self.discover_local_tools()
        
        for tool_name, tool_instance in self.local_tools.items():
            self.tools[tool_name] = tool_instance
        
        global_logger.info(f"Registered {len(self.local_tools)} local tools")
        
        # 发现并注册代理工具
        proxy_tools = await self.discover_proxy_tools()
        
        # 为代理工具创建代理包装器
        for tool_name in proxy_tools:
            if tool_name not in self.tools:  # 避免覆盖本地工具
                proxy_wrapper = ProxyToolWrapper(
                    tool_name=tool_name,
                    proxy_manager=self.proxy_tools_manager
                )
                self.tools[tool_name] = proxy_wrapper
        
        global_logger.info(f"Registered {len(proxy_tools)} proxy tools")
        global_logger.info(f"Total tools registered: {len(self.tools)}")
    
    async def execute_tool(self, tool_name: str, task_id: str, **params) -> Any:
        """执行工具"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        tool = self.tools[tool_name]
        
        # 为本地工具添加workspace_path参数
        if isinstance(tool, LocalTool):
            params['workspace_path'] = self.workspace_path
        
        return await tool.execute(task_id=task_id, **params)
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取所有工具信息"""
        tool_info = {
            "total_count": len(self.tools),
            "local_count": len(self.local_tools),
            "proxy_count": len(self.proxy_tool_names),
            "tools": {}
        }
        
        for tool_name, tool in self.tools.items():
            if hasattr(tool, 'get_tool_info'):
                tool_info["tools"][tool_name] = tool.get_tool_info()
            else:
                tool_info["tools"][tool_name] = {
                    "name": tool_name,
                    "type": "proxy" if tool_name in self.proxy_tool_names else "local"
                }
        
        return tool_info
    
    def list_tools(self) -> List[str]:
        """获取所有工具名称列表"""
        return list(self.tools.keys())
    
    def is_local_tool(self, tool_name: str) -> bool:
        """检查是否为本地工具"""
        return tool_name in self.local_tools
    
    def is_proxy_tool(self, tool_name: str) -> bool:
        """检查是否为代理工具"""
        return tool_name in self.proxy_tool_names


class ProxyToolWrapper(BaseTool):
    """代理工具包装器"""
    
    def __init__(self, tool_name: str, proxy_manager: ProxyTools):
        super().__init__()
        self.tool_name = tool_name
        self.proxy_manager = proxy_manager
        self.tool_type = "proxy"
        self.description = f"Proxy tool: {tool_name}"
    
    async def execute(self, task_id: str, **params) -> Any:
        """执行代理工具"""
        return await self.proxy_manager.execute_proxy_tool(task_id, self.tool_name, params)
    
    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "name": self.tool_name,
            "description": self.description,
            "type": "proxy",
            "proxy_url": self.proxy_manager.proxy_base_url
        } 