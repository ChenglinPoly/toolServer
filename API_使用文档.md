# Tool Server API 使用文档

## 概述

Tool Server 是一个基于 FastAPI 的多功能工具服务器，提供文件操作、代码执行、网页爬取、文档处理、版本控制等功能。支持本地工具和远程代理工具的统一管理。

**服务器版本**: 2.0.0  
**默认端口**: 8001  
**基础URL**: `http://localhost:8001`

## 启动服务器

```bash
# 本地运行
python3 -m core.server

# 或使用参数
python3 -m core.server --port 8001 --workspace ./workspace --proxy-url http://localhost:8892

# Docker运行（需要先构建镜像）
# 将宿主机的workspace目录映射到容器的/workspace
docker run -p 8001:8001 -v $(pwd)/workspace:/workspace tool-server

# 或者指定绝对路径
docker run -p 8001:8001 -v /Users/your-username/my-workspace:/workspace tool-server
```

## 基础API端点

### 1. 服务器状态

#### GET `/`
获取服务器基本信息和可用工具列表。

**响应示例**:
```json
{
  "message": "Tool Server is running",
  "tools": ["file_read", "file_write", "execute_code", ...],
  "version": "2.0.0"
}
```

#### GET `/health`
健康检查端点。

**响应示例**:
```json
{
  "status": "healthy",
  "service": "tool_server",
  "version": "2.0.0"
}
```

### 2. 工具管理

#### GET `/api/tools`
获取所有可用工具列表。

**响应示例**:
```json
{
  "success": true,
  "data": ["file_read", "file_write", "execute_code", "google_search", ...]
}
```

#### GET `/api/tools/info`
获取所有工具的详细信息。

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_count": 28,
    "local_count": 21,
    "proxy_count": 7,
    "tools": {
      "file_read": {
        "name": "file_read",
        "description": "读取文件内容",
        "version": "1.0.0",
        "class": "FileReadTool"
      },
      ...
    }
  }
}
```

### 3. 任务管理

#### POST `/api/task/create`
创建新任务。

**请求参数**:
```json
{
  "task_id": "my_task_001",
  "task_name": "我的任务",
  "requirements": "任务描述（可选）"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "my_task_001",
    "task_name": "我的任务",
    "created_at": "2025-01-01T12:00:00.000000",
    "path": "/workspace/tasks/my_task_001"
  }
}
```

#### DELETE `/api/task/{task_id}`
删除指定任务。

**响应示例**:
```json
{
  "success": true,
  "data": {
    "deleted_task_id": "my_task_001",
    "deleted_files": 5
  }
}
```

#### GET `/api/task/list`
获取所有任务列表。

#### GET `/api/task/{task_id}/status`
获取指定任务状态。

## 核心API - 工具执行

### POST `/api/tool/execute`
执行指定工具。

**请求格式**:
```json
{
  "task_id": "my_task_001",
  "tool_name": "tool_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**响应格式**:
```json
{
  "success": true,
  "data": { /* 工具执行结果 */ },
  "error": null,
  "timestamp": "2025-01-01T12:00:00.000000",
  "execution_time": 0.123,
  "task_id": "my_task_001",
  "tool_name": "tool_name"
}
```

## 工具详细说明

### 文件操作工具

#### 1. file_upload - 文件上传
上传文件到指定目录。

**参数**:
- `files`: 文件列表 (required)
  - `name`: 文件名
  - `content`: 文件内容（base64编码）
- `target_path`: 目标路径 (optional, default: "upload")

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "file_upload",
  "params": {
    "files": [{
      "name": "test.txt",
      "content": "SGVsbG8gV29ybGQ="
    }],
    "target_path": "documents"
  }
}
```

#### 2. file_read - 文件读取
读取文件内容。

**参数**:
- `file_path`: 文件路径 (required)
- `start_line`: 开始行号 (optional, default: 1)
- `end_line`: 结束行号 (optional)
- `max_length`: 最大长度 (optional, default: 10000)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "file_read",
  "params": {
    "file_path": "test.txt",
    "start_line": 1,
    "end_line": 10
  }
}
```

#### 3. file_write - 文件写入
写入内容到文件。

**参数**:
- `file_path`: 文件路径 (required)
- `content`: 文件内容 (required)
- `mode`: 写入模式 (optional, default: "overwrite")
  - "overwrite": 覆盖
  - "append": 追加

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "file_write",
  "params": {
    "file_path": "output.txt",
    "content": "Hello World",
    "mode": "overwrite"
  }
}
```

#### 4. file_search - 文本搜索
在文件中搜索特定文本内容并返回行号。

**参数**:
- `file_path`: 文件路径 (required)
- `search_text`: 搜索文本 (required)
- `case_sensitive`: 是否大小写敏感 (optional, default: false)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "file_search",
  "params": {
    "file_path": "code.py",
    "search_text": "import",
    "case_sensitive": false
  }
}
```

**返回示例**:
```json
{
  "success": true,
  "data": {
    "file_path": "code.py",
    "search_text": "import",
    "total_matches": 3,
    "total_lines": 50,
    "matches": [
      {
        "line_number": 1,
        "line_content": "import requests",
        "match_positions": [0]
      },
      {
        "line_number": 5,
        "line_content": "from datetime import datetime",
        "match_positions": [16]
      }
    ]
  }
}
```

#### 5. file_replace_lines - 行替换
替换指定行的内容。

**参数**:
- `file_path`: 文件路径 (required)
- `replacements`: 替换规则列表 (required)
  - `line_number`: 行号
  - `new_content`: 新内容

#### 6. file_delete - 文件删除
删除文件或目录。

**参数**:
- `path`: 路径 (required)

#### 7. file_move - 文件移动
移动文件或目录。

**参数**:
- `src_path`: 源路径 (required)
- `dest_path`: 目标路径 (required)

#### 8. dir_create - 目录创建
创建目录。

**参数**:
- `dir_path`: 目录路径 (required)

#### 9. dir_list - 目录列举
列出目录内容。

**参数**:
- `dir_path`: 目录路径 (optional, default: ".")
- `show_hidden`: 显示隐藏文件 (optional, default: false)

### 代码执行工具

#### 1. execute_code - Python代码执行
执行Python代码文件。

**参数**:
- `file_path`: Python文件路径 (required)
- `timeout`: 超时时间(秒) (optional, default: 300)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "execute_code",
  "params": {
    "file_path": "script.py",
    "timeout": 60
  }
}
```

#### 2. execute_shell - Shell命令执行
执行Shell命令。

**参数**:
- `command`: 命令 (required)
- `timeout`: 超时时间(秒) (optional, default: 300)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "execute_shell",
  "params": {
    "command": "ls -la",
    "timeout": 30
  }
}
```

#### 3. pip_install - Python包安装
在虚拟环境中安装Python包。

**参数**:
- `packages`: 包名列表 (required)
- `requirements_file`: requirements文件路径 (optional)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "pip_install",
  "params": {
    "packages": ["requests", "numpy==1.21.0"]
  }
}
```

#### 4. git_clone - Git仓库克隆
克隆Git仓库。

**参数**:
- `repo_url`: 仓库URL (required)
- `dest_path`: 目标路径 (optional)
- `branch`: 分支名称 (optional)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "git_clone",
  "params": {
    "repo_url": "https://github.com/user/repo.git",
    "dest_path": "my_repo",
    "branch": "main"
  }
}
```

### 网页工具

#### 1. google_search - Google搜索
执行Google搜索并返回结果。

**参数**:
- `query`: 搜索查询 (required)
- `num_results`: 结果数量 (optional, default: 10)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "google_search",
  "params": {
    "query": "Python FastAPI tutorial",
    "num_results": 5
  }
}
```

**返回示例**:
```json
{
  "success": true,
  "data": {
    "query": "Python FastAPI tutorial",
    "results": [
      {
        "title": "FastAPI Tutorial",
        "url": "https://fastapi.tiangolo.com/tutorial/",
        "description": "Learn FastAPI step by step..."
      }
    ],
    "total_results": 5
  }
}
```

#### 2. crawl_page - 网页爬取
爬取指定URL的页面内容。

**参数**:
- `url`: 网页URL (required)
- `extract_text`: 是否提取文本 (optional, default: true)
- `max_length`: 最大长度 (optional, default: 50000)
- `download_images`: 是否下载图片 (optional, default: false)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "crawl_page",
  "params": {
    "url": "https://example.com",
    "extract_text": true,
    "max_length": 10000
  }
}
```

#### 3. google_scholar_search - Google Scholar搜索
搜索Google Scholar并保存结果。

**参数**:
- `query`: 搜索查询 (required)
- `num_results`: 结果数量 (optional, default: 10)
- `year_low`: 起始年份 (optional)
- `year_high`: 结束年份 (optional)

### GitHub工具

#### 1. github_search_repositories - GitHub仓库搜索
搜索GitHub仓库。

**参数**:
- `query`: 搜索查询 (required)
- `sort`: 排序方式 (optional, default: "stars")
  - "stars", "forks", "updated"
- `order`: 排序顺序 (optional, default: "desc")
- `per_page`: 每页结果数 (optional, default: 10)
- `page`: 页码 (optional, default: 1)
- `token`: GitHub Token (optional)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "github_search_repositories",
  "params": {
    "query": "python machine learning",
    "sort": "stars",
    "per_page": 5
  }
}
```

#### 2. github_get_repository_info - GitHub仓库信息
获取GitHub仓库详细信息。

**参数**:
- `full_name`: 仓库全名 (required, 格式: "owner/repo")
- `token`: GitHub Token (optional)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "github_get_repository_info",
  "params": {
    "full_name": "microsoft/vscode"
  }
}
```

### 文档处理工具

#### 1. parse_document - 文档解析
解析文档（PDF、Word、PPT、Markdown）。

**参数**:
- `file_path`: 文档路径 (required)
- `output_format`: 输出格式 (optional, default: "text")
  - "text", "markdown", "json"

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "parse_document",
  "params": {
    "file_path": "document.pdf",
    "output_format": "markdown"
  }
}
```

#### 2. tex2pdf_convert - LaTeX转PDF
将LaTeX文档转换为PDF。

**参数**:
- `input_path`: 输入路径 (required)
- `output_path`: 输出路径 (optional)
- `engine`: 编译引擎 (optional, default: "pdflatex")
  - "pdflatex", "xelatex", "lualatex"
- `clean_aux`: 清理辅助文件 (optional, default: true)
- `tex_filename`: 指定tex文件名 (optional, default: "main.tex")

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "tex2pdf_convert",
  "params": {
    "input_path": "latex_project",
    "output_path": "output",
    "tex_filename": "paper",
    "engine": "xelatex"
  }
}
```

### 高级工具

#### 1. code_task_execute - Claude Code任务执行
使用Claude Code SDK执行编程任务。

**参数**:
- `prompt`: 任务描述 (required)
- `workspace_dir`: 工作目录 (optional, default: "claude_workspace")
- `api_key`: API密钥 (optional)
- `max_turns`: 最大轮次 (optional, default: 10)
- `allowed_tools`: 允许的工具列表 (optional)
- `system_prompt`: 系统提示 (optional)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "code_task_execute",
  "params": {
    "prompt": "创建一个简单的计算器程序",
    "workspace_dir": "calculator_project",
    "max_turns": 5
  }
}
```

## 代理工具

以下工具通过代理服务器提供（需要代理服务器运行在 http://localhost:8892）:

### 基础示例工具
- `example_hello`: 简单问候工具
- `example_calculator`: 计算工具
- `example_file_processor`: 文件处理工具
- `example_data_analyzer`: 数据分析工具

### 跨服务文件操作工具
- `generate_timestamp_file`: 生成时间戳文件并上传到主服务器

### 🆕 本地执行工具
#### 1. execute_code_local - 代理服务器本地代码执行
在代理服务器本地环境执行Python代码，访问Docker挂载的workspace。

**参数**:
- `file_path`: Python文件路径 (required)
- `working_dir`: 工作目录 (optional, default: "code_run")
- `timeout`: 超时时间(秒) (optional, default: 300)
- `python_executable`: Python可执行文件路径 (optional, default: sys.executable)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "execute_code_local",
  "params": {
    "file_path": "script.py",
    "timeout": 60
  }
}
```

**特点**:
- 🌟 在代理服务器本地环境执行（如宿主机Anaconda环境）
- 📁 默认工作目录为`code_run`，与主服务器execute_code一致
- 🔗 直接访问Docker挂载的workspace文件夹
- 🐍 可指定特定的Python环境

#### 2. pip_local - 代理服务器本地包安装
在代理服务器本地环境安装Python包。

**参数**:
- `packages`: 包名列表 (required)
- `requirements_file`: requirements文件路径 (optional)
- `python_executable`: Python可执行文件路径 (optional, default: sys.executable)

**示例**:
```json
{
  "task_id": "test",
  "tool_name": "pip_local",
  "params": {
    "packages": ["beautifulsoup4", "requests==2.28.0"]
  }
}
```

**特点**:
- 🌟 在代理服务器本地环境安装包
- 📦 支持单个包和requirements文件
- 🔧 自动检测pip路径，支持多种调用方式
- 📊 提供详细的安装统计和日志

### 🎯 使用场景

#### 环境优势对比
| 特性 | 主服务器工具 | 代理服务器本地工具 |
|------|-------------|------------------|
| **执行环境** | Docker容器内 | 宿主机本地环境 |
| **Python版本** | 容器版本 | 宿主机版本（如Anaconda） |
| **包环境** | 容器安装的包 | 宿主机丰富的包环境 |
| **工作目录** | `/workspace/tasks/{task_id}/code_run` | `{host_path}/workspace/tasks/{task_id}/code_run` |
| **文件访问** | 容器内文件系统 | Docker挂载的workspace |
| **适用场景** | 标准化执行 | 特殊环境需求、复杂依赖 |

#### 完整工作流示例
```bash
# 1. 在代理服务器环境安装特殊包
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo", 
    "tool_name": "pip_local",
    "params": {"packages": ["tensorflow", "scikit-learn"]}
  }'

# 2. 使用代理服务器本地环境执行机器学习代码
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "execute_code_local", 
    "params": {"file_path": "ml_analysis.py"}
  }'

# 3. 主服务器可以直接读取结果文件
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "file_read",
    "params": {"file_path": "code_run/analysis_results.json"}
  }'
```

代理工具的使用方式与本地工具相同，都通过主服务器的统一API接口调用。

## 错误处理

所有API调用都返回标准格式：

**成功响应**:
```json
{
  "success": true,
  "data": { /* 结果数据 */ },
  "error": null,
  "timestamp": "2025-01-01T12:00:00.000000",
  "execution_time": 0.123,
  "task_id": "task_id",
  "tool_name": "tool_name"
}
```

**错误响应**:
```json
{
  "success": false,
  "data": null,
  "error": "错误描述",
  "timestamp": "2025-01-01T12:00:00.000000",
  "execution_time": 0.123,
  "task_id": "task_id",
  "tool_name": "tool_name"
}
```

## 使用示例

### 完整工作流示例

```bash
# 1. 创建任务
curl -X POST "http://localhost:8001/api/task/create" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "demo", "task_name": "演示任务"}'

# 2. 写入Python代码
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "file_write",
    "params": {
      "file_path": "hello.py",
      "content": "print(\"Hello, World!\")\nprint(\"Tool Server is working!\")"
    }
  }'

# 3. 执行代码
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "execute_code",
    "params": {
      "file_path": "hello.py"
    }
  }'

# 4. 搜索文件中的内容
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "file_search",
    "params": {
      "file_path": "hello.py",
      "search_text": "print"
    }
  }'

# 5. 进行网页搜索
curl -X POST "http://localhost:8001/api/tool/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo",
    "tool_name": "google_search",
    "params": {
      "query": "Python教程",
      "num_results": 3
    }
  }'
```

## 注意事项

1. **任务隔离**: 每个任务都有独立的工作目录 (`/workspace/tasks/{task_id}`)
2. **文件路径**: 所有文件路径都相对于任务目录
3. **虚拟环境**: Python代码执行和包安装都在任务专用的虚拟环境中进行
4. **超时设置**: 长时间运行的工具建议设置合适的超时时间
5. **代理服务**: 代理工具需要代理服务器运行在指定地址
6. **权限控制**: 确保服务器对工作目录有读写权限

## 环境要求

- Python 3.8+
- FastAPI
- 相关依赖包（见 requirements.txt）
- 可选：LaTeX（用于PDF转换）
- 可选：Git（用于仓库克隆）
- 可选：代理服务器（用于代理工具）

更多详细信息，请参考项目源码和配置文件。 