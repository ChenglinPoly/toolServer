# Tool Server 代理服务器模板

这个模板帮助你快速创建与 Tool Server Uni 兼容的外挂代理工具服务器。

## 🚀 快速开始

### 1. 复制模板

```bash
# 复制模板文件
cp template/proxy_server_template.py my_proxy_server.py
cp template/requirements.txt proxy_requirements.txt
```

### 2. 安装依赖

```bash
# 安装基础依赖
pip install -r proxy_requirements.txt

# 根据需要安装额外依赖
pip install pandas numpy requests  # 数据处理
pip install httpx aiofiles          # 异步操作
```

### 3. 自定义你的工具

编辑 `my_proxy_server.py`：

```python
# 1. 修改服务器信息
SERVER_INFO = {
    "name": "My AI Analysis Server",
    "version": "1.0.0", 
    "description": "专门用于AI分析的代理服务器",
    "author": "Your Name"
}

# 2. 添加你的工具
PROXY_TOOLS = [
    "ai_text_analysis",
    "image_processing", 
    "data_mining",
    # 你的工具...
]

# 3. 实现工具逻辑
async def _ai_text_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    text = params.get("text", "")
    # 实现你的AI文本分析逻辑
    return {"analysis": "结果"}
```

### 4. 启动服务器

```bash
# 启动代理服务器
python my_proxy_server.py --port 8892

# 或指定其他端口
python my_proxy_server.py --port 9000 --host 0.0.0.0
```

### 5. 连接到主服务器

启动主服务器时指定代理地址：

```bash
# 连接到你的代理服务器
python -m core.server --proxy-url http://localhost:8892

# Docker方式
docker run -p 8001:8001 \
  -v $(pwd)/workspace:/workspace \
  tool_server_uni:v1.1 \
  --proxy-url http://host.docker.internal:8892
```

## 📋 必需的API端点

你的代理服务器必须实现以下端点才能与主服务器兼容：

### GET `/api/tools`
返回可用工具列表

```json
{
  "success": true,
  "data": ["tool1", "tool2", "tool3"]
}
```

### POST `/api/tool/execute`
执行工具

**请求**:
```json
{
  "task_id": "task_123",
  "tool_name": "my_tool",
  "params": {"param1": "value1"}
}
```

**响应**:
```json
{
  "success": true,
  "data": {"result": "工具执行结果"},
  "error": null,
  "timestamp": "2025-01-01T12:00:00.000000",
  "execution_time": 0.123,
  "task_id": "task_123",
  "tool_name": "my_tool"
}
```

### GET `/health`
健康检查

```json
{
  "status": "healthy",
  "service": "My Proxy Server"
}
```

## 🛠️ 工具实现示例

### 1. 简单工具

```python
async def _simple_calculator(params: Dict[str, Any]) -> Dict[str, Any]:
    a = params.get("a", 0)
    b = params.get("b", 0)
    operation = params.get("operation", "add")
    
    if operation == "add":
        result = a + b
    elif operation == "multiply":
        result = a * b
    else:
        raise ValueError(f"Unsupported operation: {operation}")
    
    return {
        "result": result,
        "expression": f"{a} {operation} {b} = {result}"
    }
```

### 2. 异步工具

```python
async def _async_web_scraper(params: Dict[str, Any]) -> Dict[str, Any]:
    import httpx
    
    url = params.get("url")
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        
    return {
        "url": url,
        "status_code": response.status_code,
        "content_length": len(response.text),
        "title": "提取的标题"  # 实际解析HTML
    }
```

### 3. 文件处理工具

```python
async def _file_analyzer(params: Dict[str, Any]) -> Dict[str, Any]:
    import aiofiles
    
    file_path = params.get("file_path")
    
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
    
    return {
        "file_path": file_path,
        "size": len(content),
        "lines": len(content.splitlines()),
        "words": len(content.split())
    }
```

### 4. 数据库工具

```python
async def _database_query(params: Dict[str, Any]) -> Dict[str, Any]:
    import sqlite3
    
    query = params.get("query")
    db_path = params.get("database", "data.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return {
        "query": query,
        "rows": len(results),
        "data": results[:10]  # 限制返回数据量
    }
```

### 5. 本地代码执行工具

```python
async def _execute_code_local(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """在代理服务器本地执行Python代码，直接访问Docker挂载的workspace"""
    
    file_path = params.get("file_path")
    timeout = params.get("timeout", 300)
    
    # 直接访问Docker挂载的workspace
    workspace_path = Path("/workspace")  # 或你的实际挂载路径
    task_path = workspace_path / "tasks" / task_id
    full_file_path = task_path / file_path
    
    # 异步执行Python代码
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(full_file_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(task_path)
    )
    
    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=timeout
    )
    
    return {
        "exit_code": process.returncode,
        "stdout": stdout.decode('utf-8'),
        "stderr": stderr.decode('utf-8'),
        "execution_location": "proxy_server_local"
    }
```

## 🔧 高级功能

### 1. 认证和授权

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(token: str = Depends(security)):
    if token.credentials != "your-secret-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

@app.post("/api/tool/execute")
async def execute_tool_endpoint(
    request: ToolRequest, 
    token: str = Depends(verify_token)
):
    # 受保护的工具执行
    pass
```

### 2. 工具限流

```python
from collections import defaultdict
import time

# 简单的令牌桶限流
class RateLimiter:
    def __init__(self, max_calls=100, time_window=60):
        self.calls = defaultdict(list)
        self.max_calls = max_calls
        self.time_window = time_window
    
    def is_allowed(self, key: str) -> bool:
        now = time.time()
        # 清理过期记录
        self.calls[key] = [t for t in self.calls[key] 
                          if now - t < self.time_window]
        
        if len(self.calls[key]) >= self.max_calls:
            return False
        
        self.calls[key].append(now)
        return True

rate_limiter = RateLimiter()

@app.post("/api/tool/execute")
async def execute_tool_endpoint(request: ToolRequest):
    if not rate_limiter.is_allowed(request.task_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # 继续执行...
```

### 3. 日志记录

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proxy_server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ProxyServer")

async def execute_tool(tool_name: str, task_id: str, params: Dict[str, Any]):
    start_time = time.time()
    logger.info(f"开始执行工具: {tool_name}, 任务: {task_id}")
    
    try:
        result = await _actual_tool_execution(tool_name, params)
        execution_time = time.time() - start_time
        logger.info(f"工具执行成功: {tool_name}, 耗时: {execution_time:.3f}s")
        return result
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}, 耗时: {execution_time:.3f}s")
        raise
```

## 🔗 与主服务器集成

### 测试连接

```bash
# 1. 启动你的代理服务器
python my_proxy_server.py --port 8892

# 2. 启动主服务器
python -m core.server --proxy-url http://localhost:8892

# 3. 测试工具调用
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "test", "tool_name": "your_tool", "params": {}}'
```

### 部署建议

1. **开发环境**: 使用 `--reload` 参数进行热重载
2. **生产环境**: 使用 `gunicorn` 或 `uvicorn` 的生产配置
3. **Docker部署**: 创建独立的Docker镜像
4. **负载均衡**: 在多个代理服务器实例之间分发请求

### 💡 本地代码执行工具使用指南

`execute_code_local` 工具是代理服务器的特色功能，它可以：

#### 🎯 使用场景
- **环境特异性**: 代理服务器有特殊的Python包或环境配置
- **绕过限制**: 不受主服务器虚拟环境限制
- **性能优化**: 减少网络传输，直接本地执行
- **调试目的**: 在代理服务器环境中调试代码

#### 📂 路径配置
```python
# 代理服务器运行在宿主机，访问Docker挂载的workspace
WORKSPACE_PATH = "/Users/username/project/workspace"  # 宿主机实际路径

# 代理服务器运行在Docker容器中
WORKSPACE_PATH = "/workspace"  # 容器内路径
```

#### 🔧 使用示例
```bash
# 1. 先通过主服务器创建Python文件
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "file_write",
    "params": {
      "file_path": "local_test.py",
      "content": "import sys\nprint(f\"Python version: {sys.version}\")\nprint(f\"Current working directory: {os.getcwd()}\")\nprint(\"Hello from proxy server local execution!\")"
    }
  }'

# 2. 使用代理服务器本地执行
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "execute_code_local",
    "params": {
      "file_path": "local_test.py",
      "timeout": 60
    }
  }'
```

#### 🆚 对比主服务器执行
| 特性 | 主服务器执行 | 代理服务器本地执行 |
|------|-------------|------------------|
| 执行环境 | 主服务器虚拟环境 | 代理服务器本地环境 |
| Python包 | 主服务器已安装的包 | 代理服务器已安装的包 |
| 文件访问 | 容器内文件系统 | 挂载的workspace |
| 网络延迟 | 无（本地） | HTTP请求延迟 |
| 适用场景 | 标准执行 | 特殊环境需求 |

## 📚 示例项目

查看 `template/` 目录下的完整示例：

- `proxy_server_template.py` - 完整的代理服务器模板
- `requirements.txt` - 最小依赖集合
- `README.md` - 本文档

## 🤝 贡献

如果你创建了有用的代理工具，欢迎分享：

1. 提交 Pull Request 添加到示例中
2. 在 Issues 中分享你的使用经验
3. 改进模板和文档

---

**快速上手，专注业务逻辑，让 Tool Server 处理其余的一切！** 🚀 