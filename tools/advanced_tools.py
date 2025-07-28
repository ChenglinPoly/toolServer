import os
import sys
import shutil
import subprocess
import tempfile
import time
import concurrent.futures
import asyncio
from pathlib import Path
from typing import List, Optional
from .base_tool import LocalTool
from utils.response import ToolResponse
from utils.logger import global_logger


class Tex2PdfTool(LocalTool):
    """LaTeX转PDF工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "tex2pdf_convert"
        self.description = "将LaTeX文档转换为PDF"
    
    async def execute(self, task_id: str, workspace_path: Path, input_path: str, output_path: str = None, engine: str = 'pdflatex', clean_aux: bool = True, tex_filename: str = None, **kwargs) -> ToolResponse:
        try:
            if not input_path:
                return ToolResponse(success=False, error="input_path is required")
            
            task_path = self.get_task_path(task_id, workspace_path)
            input_full_path = task_path / input_path
            
            if not input_full_path.exists():
                return ToolResponse(success=False, error=f"Input path not found: {input_path}")
            
            if not input_full_path.is_dir():
                return ToolResponse(success=False, error=f"Input path must be a directory: {input_path}")
            
            # 设置输出路径
            if output_path:
                output_full_path = task_path / output_path
            else:
                output_full_path = input_full_path
            
            output_full_path.mkdir(parents=True, exist_ok=True)
            
            # 内嵌TexToPdfConverter类
            class TexToPdfConverter:
                """TeX到PDF转换器"""
                
                def __init__(self, input_dir: str, output_dir: str = None, engine: str = 'pdflatex'):
                    self.input_dir = Path(input_dir).resolve()
                    self.output_dir = Path(output_dir).resolve() if output_dir else self.input_dir
                    self.engine = engine
                    
                    if not self.input_dir.exists():
                        raise FileNotFoundError(f"输入目录不存在: {self.input_dir}")
                    
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                    
                    if not self._check_latex_engine():
                        raise RuntimeError(f"LaTeX引擎 {self.engine} 不可用")
                
                def _check_latex_engine(self) -> bool:
                    """检查LaTeX引擎是否可用"""
                    try:
                        result = subprocess.run(
                            [self.engine, '--version'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        return result.returncode == 0
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        return False
                
                def find_main_tex_file(self, specified_filename: str = None) -> Optional[Path]:
                    """查找主要的tex文件"""
                    import re
                    tex_files = list(self.input_dir.glob('*.tex'))
                    
                    if not tex_files:
                        global_logger.error("没有找到tex文件")
                        return None
                    
                    # 如果指定了文件名，优先使用指定的文件
                    if specified_filename:
                        if not specified_filename.endswith('.tex'):
                            specified_filename += '.tex'
                        
                        specified_file = self.input_dir / specified_filename
                        if specified_file.exists():
                            global_logger.info(f"使用指定的tex文件: {specified_file}")
                            return specified_file
                        else:
                            global_logger.warning(f"指定的tex文件不存在: {specified_filename}，尝试自动查找")
                    
                    # 首先查找名为main.tex的文件
                    main_candidates = [f for f in tex_files if f.name.lower() == 'main.tex']
                    if main_candidates:
                        global_logger.info(f"找到主文件: {main_candidates[0]}")
                        return main_candidates[0]
                    
                    # 查找包含documentclass的文件
                    for tex_file in tex_files:
                        try:
                            with open(tex_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if re.search(r'\\documentclass', content):
                                    global_logger.info(f"找到包含documentclass的主文件: {tex_file}")
                                    return tex_file
                        except Exception as e:
                            global_logger.warning(f"读取文件 {tex_file} 时出错: {e}")
                    
                    # 如果只有一个tex文件，就使用它
                    if len(tex_files) == 1:
                        global_logger.info(f"只有一个tex文件，使用: {tex_files[0]}")
                        return tex_files[0]
                    
                    global_logger.error("无法确定主要的tex文件")
                    return None
                
                def has_bibliography(self, tex_file: Path) -> bool:
                    """检查是否有参考文献"""
                    import re
                    try:
                        with open(tex_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            return bool(re.search(r'\\bibliography\{', content) or 
                                       re.search(r'\\bibliographystyle\{', content))
                    except Exception as e:
                        global_logger.warning(f"检查参考文献时出错: {e}")
                        return False
                
                def run_latex_command(self, command: List[str], cwd: Path):
                    """运行LaTeX命令"""
                    try:
                        result = subprocess.run(
                            command,
                            cwd=cwd,
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        
                        success = result.returncode == 0
                        output = result.stdout + result.stderr
                        
                        if not success:
                            global_logger.error(f"命令执行失败: {' '.join(command)}")
                            global_logger.error(f"输出: {output}")
                        
                        return success, output
                        
                    except subprocess.TimeoutExpired:
                        global_logger.error("命令执行超时")
                        return False, "命令执行超时"
                    except Exception as e:
                        global_logger.error(f"运行命令时出错: {e}")
                        return False, str(e)
                
                def compile_tex(self, tex_file: Path) -> bool:
                    """编译tex文件为PDF"""
                    global_logger.info(f"开始编译: {tex_file}")
                    
                    # 基本LaTeX编译命令
                    base_command = [
                        self.engine,
                        '-interaction=nonstopmode',
                        '-halt-on-error',
                        '-file-line-error',
                        tex_file.name
                    ]
                    
                    # 检查是否有参考文献
                    has_bib = self.has_bibliography(tex_file)
                    
                    # 第一次编译
                    global_logger.info("第一次编译...")
                    success, output = self.run_latex_command(base_command, tex_file.parent)
                    if not success:
                        return False
                    
                    # 如果有参考文献，运行bibtex
                    if has_bib:
                        global_logger.info("处理参考文献...")
                        bib_command = ['bibtex', tex_file.stem]
                        success, output = self.run_latex_command(bib_command, tex_file.parent)
                        if not success:
                            global_logger.warning("bibtex处理失败，继续编译...")
                        
                        # 再次编译以处理参考文献
                        global_logger.info("第二次编译（处理参考文献）...")
                        success, output = self.run_latex_command(base_command, tex_file.parent)
                        if not success:
                            return False
                    
                    # 最后一次编译以确保所有引用正确
                    global_logger.info("最后一次编译...")
                    success, output = self.run_latex_command(base_command, tex_file.parent)
                    if not success:
                        return False
                    
                    global_logger.info("编译完成")
                    return True
                
                def clean_auxiliary_files(self, tex_file: Path):
                    """清理辅助文件"""
                    aux_extensions = ['.aux', '.log', '.bbl', '.blg', '.toc', '.out', '.fdb_latexmk', '.fls']
                    
                    for ext in aux_extensions:
                        aux_file = tex_file.parent / (tex_file.stem + ext)
                        if aux_file.exists():
                            try:
                                aux_file.unlink()
                                global_logger.debug(f"删除辅助文件: {aux_file}")
                            except Exception as e:
                                global_logger.warning(f"删除辅助文件 {aux_file} 失败: {e}")
                
                def move_pdf_to_output(self, tex_file: Path) -> bool:
                    """将生成的PDF移动到输出目录"""
                    pdf_file = tex_file.parent / (tex_file.stem + '.pdf')
                    
                    if not pdf_file.exists():
                        global_logger.error(f"没有找到生成的PDF文件: {pdf_file}")
                        return False
                    
                    if self.output_dir != tex_file.parent:
                        target_pdf = self.output_dir / pdf_file.name
                        try:
                            shutil.move(str(pdf_file), str(target_pdf))
                            global_logger.info(f"PDF文件已移动到: {target_pdf}")
                        except Exception as e:
                            global_logger.error(f"移动PDF文件失败: {e}")
                            return False
                    else:
                        global_logger.info(f"PDF文件已生成: {pdf_file}")
                    
                    return True
                
                def convert(self, clean_aux: bool = True, tex_filename: str = None) -> bool:
                    """执行转换"""
                    global_logger.info(f"开始转换，输入目录: {self.input_dir}")
                    
                    # 查找主tex文件
                    main_tex = self.find_main_tex_file(tex_filename)
                    if not main_tex:
                        return False
                    
                    # 编译tex文件
                    success = self.compile_tex(main_tex)
                    if not success:
                        return False
                    
                    # 移动PDF到输出目录
                    success = self.move_pdf_to_output(main_tex)
                    if not success:
                        return False
                    
                    # 清理辅助文件
                    if clean_aux:
                        self.clean_auxiliary_files(main_tex)
                    
                    global_logger.info("转换完成")
                    return True
            
            # 在线程池中执行转换以避免阻塞事件循环
            def run_conversion():
                converter = TexToPdfConverter(
                    input_dir=str(input_full_path),
                    output_dir=str(output_full_path),
                    engine=engine
                )
                return converter.convert(clean_aux=clean_aux, tex_filename=tex_filename)
            
            # 使用线程池执行器运行阻塞的转换操作
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(executor, run_conversion)
            
            if success:
                # 查找生成的PDF文件
                pdf_files = list(output_full_path.glob('*.pdf'))
                pdf_files_relative = [str(f.relative_to(task_path)) for f in pdf_files]
                
                return ToolResponse(
                    success=True,
                    data={
                        "input_path": input_path,
                        "output_path": str(output_full_path.relative_to(task_path)),
                        "engine": engine,
                        "pdf_files": pdf_files_relative,
                        "clean_aux": clean_aux
                    }
                )
            else:
                return ToolResponse(
                    success=False,
                    error="LaTeX to PDF conversion failed"
                )
            
        except Exception as e:
            global_logger.error(f"TeX to PDF conversion error: {str(e)}")
            return ToolResponse(success=False, error=str(e))


class CodeTaskExecuteTool(LocalTool):
    """Claude Code SDK执行工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "code_task_execute"
        self.description = "使用Claude Code SDK执行编程任务"
    
    async def execute(self, task_id: str, workspace_path: Path, prompt: str, workspace_dir: str = 'claude_workspace', api_key: str = None, max_turns: int = 10, allowed_tools: List[str] = None, system_prompt: str = None, **kwargs) -> ToolResponse:
        try:
            if not prompt:
                return ToolResponse(success=False, error="prompt is required")
            
            if not api_key:
                # 尝试从环境变量获取
                api_key = os.environ.get('ANTHROPIC_API_KEY')
                if not api_key:
                    return ToolResponse(success=False, error="api_key is required")
            
            # 构建工作目录的绝对路径
            task_path = self.get_task_path(task_id, workspace_path)
            workspace_path_full = task_path / workspace_dir
            workspace_path_full.mkdir(parents=True, exist_ok=True)
            
            # 设置环境变量
            os.environ['ANTHROPIC_API_KEY'] = api_key
            
            # 导入 claude_code_sdk
            try:
                from claude_code_sdk import query, ClaudeCodeOptions
            except ImportError:
                return ToolResponse(
                    success=False, 
                    error="claude_code_sdk not installed. Please rebuild the Docker image."
                )
            
            # 确保任务的虚拟环境存在
            venv_path = task_path / "code_env"
            venv_python = venv_path / "bin" / "python"
            venv_pip = venv_path / "bin" / "pip"
            
            # 如果虚拟环境不存在，创建它（异步版本）
            if not venv_python.exists():
                global_logger.info(f"Creating virtual environment for task {task_id}")
                # 如果目录已存在，先删除
                if venv_path.exists():
                    shutil.rmtree(venv_path)
                
                # 使用异步进程创建虚拟环境
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "venv", str(venv_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    global_logger.error(f"Failed to create virtual environment: {stderr.decode('utf-8')}")
                    # 继续使用系统Python
                    venv_python = sys.executable
                else:
                    global_logger.info(f"Virtual environment created at {venv_path}")
            
            # 设置默认系统提示
            if system_prompt is None:
                system_prompt = f"""你是一个专业的软件开发助手。请按照以下要求完成任务：
1. **重要**：所有文件必须在当前工作目录 {workspace_path_full} 中创建，不要使用 /tmp 或其他目录
2. **重要**：如果需要运行Python代码，请使用虚拟环境 {venv_python}
3. **重要**：如果需要安装Python包，请使用虚拟环境的pip {venv_pip}
4. 在完成任务后，简洁报告你的工作进展：
   - 在之前项目基础上完成了哪些新的具体工作
   - 创建了哪些文件（仅相对文件路径）
   - 如何运行（简短命令）
5. 请用中文简洁说明，避免冗长输出
6. 不要输出过多内容，减少token使用
"""
            
            # 设置默认允许的工具
            if allowed_tools is None:
                allowed_tools = ["Read", "Write", "Edit", "Bash"]
            
            # 配置选项
            options = ClaudeCodeOptions(
                max_turns=max_turns,
                system_prompt=system_prompt,
                cwd=str(workspace_path_full),
                allowed_tools=allowed_tools,
                permission_mode="acceptEdits"
            )
            
            # 记录任务开始前的文件状态
            files_before = set()
            if workspace_path_full.exists():
                for file_path in workspace_path_full.rglob("*"):
                    if file_path.is_file():
                        files_before.add(str(file_path.relative_to(workspace_path_full)))
            
            # 执行任务
            messages = []
            session_id = None
            total_cost = 0.0
            duration_ms = 0
            final_result = ""
            
            global_logger.info(f"Starting Claude Code task for {task_id} in {workspace_path_full}")
            
            async for message in query(prompt=prompt, options=options):
                messages.append(message)
                
                # 记录会话信息
                if hasattr(message, 'session_id') and message.session_id:
                    session_id = message.session_id
                
                # 记录成本和时间
                if hasattr(message, 'total_cost_usd'):
                    total_cost = message.total_cost_usd
                if hasattr(message, 'duration_ms'):
                    duration_ms = message.duration_ms
                
                # 获取最终结果
                if hasattr(message, 'result') and message.result:
                    final_result = message.result
            
            # 记录任务完成后的文件状态
            files_after = set()
            if workspace_path_full.exists():
                for file_path in workspace_path_full.rglob("*"):
                    if file_path.is_file():
                        files_after.add(str(file_path.relative_to(workspace_path_full)))
            
            # 计算文件变化
            files_created = list(files_after - files_before)
            
            # 如果没有获取到 result，尝试从最后的消息中提取
            if not final_result and messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    if isinstance(last_message.content, list):
                        for block in last_message.content:
                            if hasattr(block, 'text'):
                                final_result += block.text
                    elif hasattr(last_message.content, 'text'):
                        final_result = last_message.content.text
                    else:
                        final_result = str(last_message.content)
            
            global_logger.info(f"Claude Code task completed for {task_id}, cost: ${total_cost:.4f}")
            
            return ToolResponse(
                success=True,
                data={
                    "result": final_result,
                    "session_id": session_id,
                    "files_created": files_created,
                    "total_cost": total_cost,
                    "duration_ms": duration_ms,
                    "workspace_path": str(workspace_path_full.relative_to(task_path)),
                    "message_count": len(messages)
                }
            )
            
        except Exception as e:
            global_logger.error(f"Claude Code execution error: {str(e)}")
            return ToolResponse(success=False, error=str(e)) 