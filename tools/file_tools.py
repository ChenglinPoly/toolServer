import os
import base64
import shutil
from pathlib import Path
from typing import Dict, Any, List
from .base_tool import LocalTool
from utils.response import ToolResponse
from datetime import datetime
from utils.lock_decorator import require_write_access, require_read_access, bypass_lock_check


class FileUploadTool(LocalTool):
    """文件上传工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_upload"
        self.description = "上传文件到指定目录"
    
    @require_write_access('target_path')
    async def execute(self, task_id: str, workspace_path: Path, files: List[Dict] = None, target_path: str = '', **kwargs) -> ToolResponse:
        try:
            if not files:
                files = []
            
            task_path = self.get_task_path(task_id, workspace_path)
            if target_path:
                upload_dir = task_path / target_path
            else:
                upload_dir = task_path / "upload"
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            uploaded_files = []
            
            for file_data in files:
                filename = file_data.get('filename')
                content = file_data.get('content')
                
                if not filename or content is None:
                    continue
                
                file_path = upload_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if file_data.get('is_base64', False):
                    content = base64.b64decode(content)
                    with open(file_path, 'wb') as f:
                        f.write(content)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                file_stat = os.stat(file_path)
                uploaded_files.append({
                    'filename': filename,
                    'path': str(file_path),
                    'size': file_stat.st_size,
                    'created_at': datetime.fromtimestamp(file_stat.st_ctime).isoformat()
                })
            
            return ToolResponse(
                success=True,
                data={
                    'uploaded_files': uploaded_files,
                    'upload_dir': str(upload_dir)
                }
            )
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class FileReadTool(LocalTool):
    """文件读取工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_read"
        self.description = "读取文件内容"
    
    @require_read_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, start_line: int = None, end_line: int = None, **kwargs) -> ToolResponse:
        try:
            if not file_path:
                return ToolResponse(success=False, error="file_path is required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / file_path
            
            if not full_path.exists():
                return ToolResponse(success=False, error=f"File not found: {file_path}")
            
            if not full_path.is_file():
                return ToolResponse(success=False, error=f"Not a file: {file_path}")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            if start_line is None and end_line is None:
                content = ''.join(lines)
                line_range = f"1-{total_lines}"
            else:
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else total_lines
                
                start_idx = max(0, min(start_idx, total_lines - 1))
                end_idx = max(start_idx + 1, min(end_idx, total_lines))
                
                content = ''.join(lines[start_idx:end_idx])
                line_range = f"{start_idx + 1}-{end_idx}"
            
            return ToolResponse(
                success=True,
                data={
                    "content": content,
                    "total_lines": total_lines,
                    "line_range": line_range,
                    "file_path": file_path,
                    "container_path": str(full_path)
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class FileWriteTool(LocalTool):
    """文件写入工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_write"
        self.description = "写入文件内容"
    
    @require_write_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, content: str = '', mode: str = 'overwrite', is_base64: bool = False, **kwargs) -> ToolResponse:
        try:
            if not file_path:
                return ToolResponse(success=False, error="file_path is required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / file_path
            
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            if is_base64:
                try:
                    content = base64.b64decode(content).decode('utf-8')
                except Exception as e:
                    return ToolResponse(success=False, error=f"Base64 decode error: {str(e)}")
            
            write_mode = 'w' if mode == 'overwrite' else 'a'
            
            with open(full_path, write_mode, encoding='utf-8') as f:
                f.write(content)
            
            file_stat = os.stat(full_path)
            
            return ToolResponse(
                success=True,
                data={
                    "file_path": file_path,
                    "mode": mode,
                    "size": file_stat.st_size,
                    "container_path": str(full_path),
                    "was_base64": is_base64
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class FileReplaceTool(LocalTool):
    """文件行替换工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_replace_lines"
        self.description = "替换指定行的内容"
    
    @require_write_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, start_line: int, end_line: int, new_content: str = '', is_base64: bool = False, **kwargs) -> ToolResponse:
        try:
            if not all([file_path, start_line, end_line]):
                return ToolResponse(
                    success=False, 
                    error="file_path, start_line, and end_line are required"
                )
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / file_path
            
            if not full_path.exists():
                return ToolResponse(success=False, error=f"File not found: {file_path}")
            
            if is_base64:
                try:
                    new_content = base64.b64decode(new_content).decode('utf-8')
                except Exception as e:
                    return ToolResponse(success=False, error=f"Failed to decode base64: {str(e)}")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            start_idx = start_line - 1
            end_idx = end_line
            
            if start_idx < 0 or start_idx >= total_lines:
                return ToolResponse(success=False, error=f"Invalid start line: {start_line}")
            
            if end_idx < start_idx or end_idx > total_lines:
                return ToolResponse(success=False, error=f"Invalid end line: {end_line}")
            
            new_lines = new_content.splitlines(keepends=True)
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            
            lines[start_idx:end_idx] = new_lines
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return ToolResponse(
                success=True,
                data={
                    "file_path": file_path,
                    "replaced_lines": f"{start_line}-{end_line}",
                    "new_line_count": len(new_lines),
                    "total_lines": len(lines),
                    "was_base64": is_base64
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class FileDeleteTool(LocalTool):
    """文件删除工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_delete"
        self.description = "删除文件或目录"
    
    @require_write_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, **kwargs) -> ToolResponse:
        try:
            if not file_path:
                return ToolResponse(success=False, error="file_path is required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / file_path
            
            if not full_path.exists():
                return ToolResponse(success=False, error=f"File not found: {file_path}")
            
            file_type = "file" if full_path.is_file() else "directory"
            
            if full_path.is_file():
                os.remove(full_path)
            else:
                shutil.rmtree(full_path)
            
            return ToolResponse(
                success=True,
                data={
                    "deleted": file_path,
                    "type": file_type
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class FileMoveTool(LocalTool):
    """文件移动工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_move"
        self.description = "移动文件或目录"
    
    @require_write_access('src_path', 'dest_path')
    async def execute(self, task_id: str, workspace_path: Path, src_path: str, dest_path: str, **kwargs) -> ToolResponse:
        try:
            if not all([src_path, dest_path]):
                return ToolResponse(
                    success=False, 
                    error="src_path and dest_path are required"
                )
            
            task_path = self.get_task_path(task_id, workspace_path)
            src_full = task_path / src_path
            dest_full = task_path / dest_path
            
            if not src_full.exists():
                return ToolResponse(success=False, error=f"Source not found: {src_path}")
            
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_full), str(dest_full))
            
            return ToolResponse(
                success=True,
                data={
                    "moved_from": src_path,
                    "moved_to": dest_path
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class DirCreateTool(LocalTool):
    """目录创建工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "dir_create"
        self.description = "创建目录"
    
    @require_write_access('dir_path')
    async def execute(self, task_id: str, workspace_path: Path, dir_path: str, **kwargs) -> ToolResponse:
        try:
            if not dir_path:
                return ToolResponse(success=False, error="dir_path is required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            return ToolResponse(
                success=True,
                data={
                    "created": dir_path,
                    "container_path": str(full_path)
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class DirListTool(LocalTool):
    """目录列表工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "dir_list"
        self.description = "列出目录内容"
    
    @require_read_access('dir_path')
    async def execute(self, task_id: str, workspace_path: Path, dir_path: str = '', recursive: bool = False, **kwargs) -> ToolResponse:
        try:
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / dir_path if dir_path else task_path
            
            if not full_path.exists():
                return ToolResponse(success=False, error=f"Directory not found: {dir_path}")
            
            if not full_path.is_dir():
                return ToolResponse(success=False, error=f"Not a directory: {dir_path}")
            
            def build_tree(path: Path, base_path: Path) -> Dict:
                result = {
                    "name": path.name,
                    "type": "directory" if path.is_dir() else "file",
                    "path": str(path.relative_to(base_path))
                }
                
                if path.is_file():
                    stat = path.stat()
                    result["size"] = stat.st_size
                elif path.is_dir() and recursive:
                    result["children"] = []
                    for child in sorted(path.iterdir()):
                        result["children"].append(build_tree(child, base_path))
                
                return result
            
            if recursive:
                tree = build_tree(full_path, task_path)
            else:
                items = []
                for item in sorted(full_path.iterdir()):
                    item_info = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": str(item.relative_to(task_path))
                    }
                    if item.is_file():
                        item_info["size"] = item.stat().st_size
                    items.append(item_info)
                
                tree = {
                    "name": full_path.name,
                    "type": "directory",
                    "path": dir_path or ".",
                    "children": items
                }
            
            return ToolResponse(
                success=True,
                data={
                    "tree": tree,
                    "base_path": str(task_path)
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e)) 


class FileSearchTool(LocalTool):
    """文本搜索工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_search"
        self.description = "在文件中搜索特定文本内容并返回行号"
    
    @require_read_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, search_text: str, case_sensitive: bool = False, **kwargs) -> ToolResponse:
        try:
            if not file_path:
                return ToolResponse(success=False, error="file_path is required")
            
            if not search_text:
                return ToolResponse(success=False, error="search_text is required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / file_path
            
            if not full_path.exists():
                return ToolResponse(success=False, error=f"File not found: {file_path}")
            
            if not full_path.is_file():
                return ToolResponse(success=False, error=f"Not a file: {file_path}")
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # 搜索匹配的行
                matches = []
                search_term = search_text if case_sensitive else search_text.lower()
                
                for line_num, line in enumerate(lines, 1):
                    line_content = line if case_sensitive else line.lower()
                    if search_term in line_content:
                        matches.append({
                            "line_number": line_num,
                            "line_content": line.rstrip('\n\r'),
                            "match_positions": self._find_match_positions(line_content, search_term)
                        })
                
                return ToolResponse(
                    success=True,
                    data={
                        "file_path": file_path,
                        "search_text": search_text,
                        "case_sensitive": case_sensitive,
                        "total_matches": len(matches),
                        "total_lines": len(lines),
                        "matches": matches
                    }
                )
                
            except UnicodeDecodeError:
                return ToolResponse(success=False, error=f"Cannot read file as text: {file_path}")
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))
    
    def _find_match_positions(self, line: str, search_term: str) -> List[int]:
        """查找搜索词在行中的位置"""
        positions = []
        start = 0
        while True:
            pos = line.find(search_term, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions 