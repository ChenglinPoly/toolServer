import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any


class TaskLogger:
    """任务级别的双层日志系统"""
    
    def __init__(self, task_id: str, log_dir: str):
        self.task_id = task_id
        self.log_dir = log_dir
        self.process_logger = self._setup_process_logger()
        self.detail_logger = self._setup_detail_logger()
    
    def _setup_process_logger(self) -> logging.Logger:
        """设置进程日志（工具执行摘要）"""
        logger_name = f"task_{self.task_id}_process"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
            
        # 创建日志文件
        os.makedirs(self.log_dir, exist_ok=True)
        log_file = os.path.join(self.log_dir, f"{self.task_id}_process.log")
        
        # 文件handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 简洁格式化（只显示时间和消息）
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_detail_logger(self) -> logging.Logger:
        """设置详细日志（完整的执行细节）"""
        logger_name = f"task_{self.task_id}_detail"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
            
        # 创建详细日志文件
        os.makedirs(self.log_dir, exist_ok=True)
        log_file = os.path.join(self.log_dir, f"{self.task_id}_detail.log")
        
        # 只写入文件，不输出到控制台
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 详细格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def _format_params_summary(self, params: Dict[str, Any]) -> str:
        """格式化参数摘要（限制长度）"""
        # 过滤掉task_id参数
        filtered_params = {k: v for k, v in params.items() if k != 'task_id'}
        
        if not filtered_params:
            return ""
        
        # 转换为字符串
        params_str = str(filtered_params)
        
        # 如果超过100字符，截取前100字符
        if len(params_str) > 100:
            params_str = params_str[:100] + "..."
        
        return f" | {params_str}"
    
    def _format_result_summary(self, result: Dict[str, Any]) -> str:
        """格式化结果摘要（限制长度）"""
        if not result:
            return ""
        
        result_str = str(result)
        
        # 如果超过200字符，取前100字符和后100字符
        if len(result_str) > 200:
            result_str = result_str[:100] + "..." + result_str[-100:]
        
        return f" | {result_str}"
    
    def log_tool_start(self, tool_name: str, params: Dict[str, Any]):
        """记录工具开始执行"""
        # 进程日志：包含参数摘要
        params_summary = self._format_params_summary(params)
        self.process_logger.info(f"[START] {tool_name}{params_summary}")
        
        # 详细日志：完整记录
        self.detail_logger.info(f"Tool {tool_name} started")
        self.detail_logger.debug(f"Parameters: {params}")
    
    def log_tool_success(self, tool_name: str, result: Dict[str, Any], execution_time: float, params: Dict[str, Any] = None, silent: bool = False):
        """记录工具执行成功"""
        # 检查是否为静默模式（主要针对前端日志查看请求）
        if silent or (params and params.get('silent', False)):
            # 静默模式：只记录简化日志
            self.detail_logger.debug(f"Tool {tool_name} executed silently in {execution_time:.3f}s")
            return
            
        # 正常模式：进程日志包含参数和结果摘要
        params_summary = self._format_params_summary(params) if params else ""
        result_summary = self._format_result_summary(result)
        self.process_logger.info(f"[SUCCESS] {tool_name} ({execution_time:.3f}s){params_summary}{result_summary}")
        
        # 详细日志：完整记录
        self.detail_logger.info(f"Tool {tool_name} executed successfully in {execution_time:.3f}s")
        self.detail_logger.debug(f"Result: {result}")
    
    def log_tool_error(self, tool_name: str, error: str, execution_time: float, params: Dict[str, Any] = None):
        """记录工具执行失败"""
        # 进程日志：包含参数摘要和错误信息
        params_summary = self._format_params_summary(params) if params else ""
        # 错误信息也限制长度
        error_summary = error if len(error) <= 100 else error[:100] + "..."
        self.process_logger.error(f"[ERROR] {tool_name} ({execution_time:.3f}s){params_summary} | Error: {error_summary}")
        
        # 详细日志：完整记录
        self.detail_logger.error(f"Tool {tool_name} failed after {execution_time:.3f}s: {error}")
    
    def log_detail(self, message: str, level: str = "info"):
        """记录详细信息（仅写入详细日志）"""
        if level.lower() == "debug":
            self.detail_logger.debug(message)
        elif level.lower() == "warning":
            self.detail_logger.warning(message)
        elif level.lower() == "error":
            self.detail_logger.error(message)
        else:
            self.detail_logger.info(message)
    
    def log_process(self, message: str):
        """记录进程信息（写入进程日志）"""
        self.process_logger.info(message)

    # 保持向后兼容的方法
    def log_tool_call(self, tool_name: str, params: dict, result: Optional[dict] = None, error: Optional[str] = None):
        """记录工具调用（向后兼容）"""
        if error:
            self.log_tool_error(tool_name, error, 0.0)
            self.log_detail(f"Parameters: {params}")
        else:
            self.log_tool_success(tool_name, result or {}, 0.0)
            self.log_detail(f"Parameters: {params}")


# 全局logger
def setup_global_logger():
    """设置全局logger"""
    logger = logging.getLogger('tool_server')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 文件handler
        file_handler = logging.FileHandler('tool_server.log')
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger


# 初始化全局logger
global_logger = setup_global_logger()
