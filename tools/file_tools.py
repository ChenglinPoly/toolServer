import os
import base64
import shutil
import chardet
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from .base_tool import LocalTool
from utils.response import ToolResponse
from datetime import datetime
from utils.lock_decorator import require_write_access, require_read_access, bypass_lock_check


def detect_file_encoding(file_path: Path) -> Tuple[str, float]:
    """
    检测文件编码格式
    Returns: (encoding, confidence)
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10240)  # 读取前10KB用于检测
        
        result = chardet.detect(raw_data)
        encoding = result.get('encoding', 'utf-8')
        confidence = result.get('confidence', 0.0)
        
        # 对常见的中文编码进行优化判断
        if encoding and encoding.lower() in ['gb2312', 'gbk', 'gb18030']:
            # 尝试用检测到的编码解码，如果成功且包含中文字符，则确认
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    test_content = f.read(1024)
                # 检查是否包含中文字符
                if any('\u4e00' <= char <= '\u9fff' for char in test_content):
                    return encoding, min(confidence + 0.1, 1.0)  # 提高中文编码的置信度
            except (UnicodeDecodeError, UnicodeError):
                pass
        
        return encoding or 'utf-8', confidence
        
    except Exception:
        return 'utf-8', 0.0


def read_file_with_encoding(file_path: Path, preferred_encoding: Optional[str] = None) -> Tuple[str, str]:
    """
    使用自动编码检测读取文件
    Returns: (content, actual_encoding)
    """
    encodings_to_try = []
    
    # 如果指定了首选编码，先尝试
    if preferred_encoding:
        encodings_to_try.append(preferred_encoding)
    
    # 自动检测编码
    detected_encoding, confidence = detect_file_encoding(file_path)
    if detected_encoding and detected_encoding not in encodings_to_try:
        encodings_to_try.append(detected_encoding)
    
    # 常见的中文编码回退列表
    fallback_encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-16', 'latin1']
    for enc in fallback_encodings:
        if enc not in encodings_to_try:
            encodings_to_try.append(enc)
    
    # 尝试各种编码
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return content, encoding
        except (UnicodeDecodeError, UnicodeError, LookupError):
            continue
    
    # 如果所有编码都失败，使用二进制模式读取并尝试解码
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        # 尝试用utf-8解码，忽略错误
        content = raw_data.decode('utf-8', errors='replace')
        return content, 'utf-8 (with errors replaced)'
    except Exception as e:
        raise Exception(f"无法读取文件，所有编码尝试都失败: {str(e)}")


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
    """文件读取工具 - 支持自动编码检测"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_read"
        self.description = "读取文件内容，支持自动编码检测"
    
    @require_read_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, start_line: int = None, end_line: int = None, encoding: str = None, silent: bool = False, **kwargs) -> ToolResponse:
        try:
            if not file_path:
                return ToolResponse(success=False, error="file_path is required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / file_path
            
            if not full_path.exists():
                return ToolResponse(success=False, error=f"File not found: {file_path}")
            
            if not full_path.is_file():
                return ToolResponse(success=False, error=f"Not a file: {file_path}")
            
            # 检查文件扩展名，禁止读取二进制文件
            binary_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.tiff', '.webp', 
                                '.mp3', '.mp4', '.avi', '.mov', '.wav', '.zip', '.rar', '.7z', '.tar', '.gz',
                                '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.db', '.sqlite', '.pkl'}
            
            if full_path.suffix.lower() in binary_extensions:
                return ToolResponse(
                    success=False, 
                    error=f"Cannot read binary file: {file_path}. File type '{full_path.suffix}' is not supported for text reading."
                )
            
            # 使用自动编码检测读取文件
            try:
                content, actual_encoding = read_file_with_encoding(full_path, encoding)
                lines = content.splitlines(keepends=True)
            except Exception as e:
                return ToolResponse(success=False, error=f"读取文件失败: {str(e)}")
            
            total_lines = len(lines)
            
            if start_line is None and end_line is None:
                final_content = content
                line_range = f"1-{total_lines}"
            else:
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else total_lines
                
                start_idx = max(0, min(start_idx, total_lines - 1))
                end_idx = max(start_idx + 1, min(end_idx, total_lines))
                
                final_content = ''.join(lines[start_idx:end_idx])
                line_range = f"{start_idx + 1}-{end_idx}"
            
            return ToolResponse(
                success=True,
                data={
                    "content": final_content,
                    "total_lines": total_lines,
                    "line_range": line_range,
                    "file_path": file_path,
                    "container_path": str(full_path),
                    "detected_encoding": actual_encoding,
                    "file_size": full_path.stat().st_size
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class FileWriteTool(LocalTool):
    """文件写入工具 - 支持编码指定"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_write"
        self.description = "写入文件内容，支持指定编码格式"
    
    @require_write_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, content: str = '', mode: str = 'overwrite', is_base64: bool = False, encoding: str = 'utf-8', **kwargs) -> ToolResponse:
        try:
            if not file_path:
                return ToolResponse(success=False, error="file_path is required")
            
            if content == '':
                return ToolResponse(success=False, error="content cannot be empty")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_path = task_path / file_path
            
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            if is_base64:
                try:
                    content = base64.b64decode(content).decode(encoding)
                except Exception as e:
                    return ToolResponse(success=False, error=f"Base64 decode error: {str(e)}")
            
            write_mode = 'w' if mode == 'overwrite' else 'a'
            
            try:
                with open(full_path, write_mode, encoding=encoding) as f:
                    f.write(content)
            except UnicodeEncodeError as e:
                return ToolResponse(success=False, error=f"编码错误 ({encoding}): {str(e)}。建议使用 utf-8 编码。")
            
            file_stat = os.stat(full_path)
            
            return ToolResponse(
                success=True,
                data={
                    "file_path": file_path,
                    "mode": mode,
                    "size": file_stat.st_size,
                    "container_path": str(full_path),
                    "was_base64": is_base64,
                    "encoding_used": encoding
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class FileReplaceTool(LocalTool):
    """文件行替换工具 - 支持编码检测"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_replace_lines"
        self.description = "替换指定行的内容，支持自动编码检测"
    
    @require_write_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, start_line: int, end_line: int, new_content: str = '', is_base64: bool = False, encoding: str = None, **kwargs) -> ToolResponse:
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
            
            # 使用自动编码检测读取文件
            try:
                content, actual_encoding = read_file_with_encoding(full_path, encoding)
                lines = content.splitlines(keepends=True)
            except Exception as e:
                return ToolResponse(success=False, error=f"读取文件失败: {str(e)}")
            
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
            
            # 使用原文件的编码写回（如果检测成功的话）
            write_encoding = actual_encoding if actual_encoding and 'with errors' not in actual_encoding else 'utf-8'
            
            try:
                with open(full_path, 'w', encoding=write_encoding) as f:
                    f.writelines(lines)
            except UnicodeEncodeError:
                # 如果原编码写入失败，回退到utf-8
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                write_encoding = 'utf-8'
            
            return ToolResponse(
                success=True,
                data={
                    "file_path": file_path,
                    "replaced_lines": f"{start_line}-{end_line}",
                    "new_line_count": len(new_lines),
                    "total_lines": len(lines),
                    "was_base64": is_base64,
                    "original_encoding": actual_encoding,
                    "write_encoding": write_encoding
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
                    # 禁止递归展开code_env文件夹
                    if path.name == "code_env":
                        # 不添加children，阻止递归展开
                        pass
                    else:
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
    """文本搜索工具 - 支持编码检测"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_search"
        self.description = "在文件中搜索特定文本内容并返回行号，支持自动编码检测"
    
    @require_read_access('file_path')
    async def execute(self, task_id: str, workspace_path: Path, file_path: str, search_text: str, case_sensitive: bool = False, encoding: str = None, **kwargs) -> ToolResponse:
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
                # 使用自动编码检测读取文件
                content, actual_encoding = read_file_with_encoding(full_path, encoding)
                lines = content.splitlines()
                
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
                        "matches": matches,
                        "detected_encoding": actual_encoding
                    }
                )
                
            except Exception as e:
                return ToolResponse(success=False, error=f"读取或搜索文件失败: {str(e)}")
            
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


class FileCopyTool(LocalTool):
    """文件复制工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_copy"
        self.description = "复制文件或目录到指定位置"
    
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
            
            # 如果源是文件，则校验后缀名一致
            if src_full.is_file():
                if src_full.suffix != dest_full.suffix:
                    return ToolResponse(
                        success=False,
                        error=f"File extension mismatch: {src_full.suffix} != {dest_full.suffix}"
                    )
                dest_full.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src_full), str(dest_full))
            else:
                # 目录复制
                dest_full.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(src_full), str(dest_full), dirs_exist_ok=True)
            
            return ToolResponse(
                success=True,
                data={
                    "copied_from": src_path,
                    "copied_to": dest_path
                }
            )
            
        except Exception as e:
            return ToolResponse(success=False, error=str(e))
        
class FileDownloadTool(LocalTool):
    """文件下载工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "file_download"
        self.description = "下载文件到本地"
    
    @bypass_lock_check
    async def execute(self, task_id: str, workspace_path: Path, download_url: str, save_path: str, **kwargs) -> ToolResponse:
        try:
            if not download_url or not save_path:
                return ToolResponse(success=False, error="download_url and save_path are required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            full_save_path = task_path / save_path
            
            # 确保目录存在
            full_save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 下载文件
            response = await self.download_file(download_url, full_save_path)
            if not response.success:
                return response
            
            return ToolResponse(
                success=True,
                data={
                    "downloaded_file": str(full_save_path),
                    "file_size": full_save_path.stat().st_size
                }
            )
        
        except Exception as e:
            return ToolResponse(success=False, error=str(e))
    async def download_file(self, url: str, save_path: Path) -> ToolResponse:
        """下载文件的辅助方法"""
        import aiohttp
        
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return ToolResponse(success=False, error=f"下载失败，HTTP状态码: {response.status}")
                    
                    with open(save_path, 'wb') as f:
                        content = await response.read()
                        f.write(content)
            
            return ToolResponse(success=True)
        
        except Exception as e:
            return ToolResponse(success=False, error=f"下载过程中发生错误: {str(e)}")
