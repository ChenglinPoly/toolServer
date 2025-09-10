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

class WorkspaceCopyTool(LocalTool):
    """工作区复制工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "workspace_copy"
        self.description = "复制工作区生成多个副本"
    
    async def execute(
        self,
        task_id: str,
        workspace_path: Path,
        copyed_taskid: str,
        numV: int,
        copyid_list: List[str],
        **kwargs
    ) -> ToolResponse:
        try:
            # 参数校验
            if not copyed_taskid:
                return ToolResponse(success=False, error="copyed_taskid is required")
            if not isinstance(numV, int) or numV <= 0:
                return ToolResponse(success=False, error="numV must be a positive integer")
            if not copyid_list or not isinstance(copyid_list, list):
                return ToolResponse(success=False, error="copyid_list must be a non-empty list")
            if len(copyid_list) != numV:
                return ToolResponse(success=False, error="numV must equal the length of copyid_list")
            # 检查目标ID是否有重复
            if len(set(copyid_list)) != len(copyid_list):
                return ToolResponse(success=False, error="copyid_list contains duplicate ids")
            # 检查是否包含源ID
            if copyed_taskid in copyid_list:
                return ToolResponse(success=False, error="copyid_list should not contain copyed_taskid")

            tasks_root = workspace_path / "tasks"
            src_path = tasks_root / copyed_taskid
            if not src_path.exists() or not src_path.is_dir():
                return ToolResponse(success=False, error=f"source task not found: {copyed_taskid}")

            tasks_root.mkdir(parents=True, exist_ok=True)

            created: List[Dict[str, Any]] = []

            # 预检查：任一目标已存在则整体失败，避免部分复制
            existing_targets = [tid for tid in copyid_list if (tasks_root / tid).exists()]
            if existing_targets:
                return ToolResponse(
                    success=False,
                    error=f"target task(s) already exist: {', '.join(existing_targets)}"
                )

            # 执行复制
            for target_id in copyid_list:
                dest_path = tasks_root / target_id
                # 父目录已存在，copytree禁止覆盖，按预检查可安全复制
                shutil.copytree(str(src_path), str(dest_path))
                created.append({
                    "task_id": target_id,
                    "path": str(dest_path)
                })

            return ToolResponse(
                success=True,
                data={
                    "source_task_id": copyed_taskid,
                    "created_count": len(created),
                    "created": created
                }
            )
        except Exception as e:
            return ToolResponse(success=False, error=str(e))


class WorkspaceDeleteTool(LocalTool):
    """批量删除指定 taskid 的工作空间目录"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "workspace_delete"
        self.description = "根据 taskid 列表删除 /tasks 下对应的工作空间目录"
    
    async def execute(
        self,
        task_id: str,
        workspace_path: Path,
        taskid_list: List[str],
        stop_on_error: bool = False,
        **kwargs
    ) -> ToolResponse:
        try:
            if not taskid_list or not isinstance(taskid_list, list):
                return ToolResponse(success=False, error="taskid_list must be a non-empty list")
            if any((not isinstance(t, str) or not t.strip()) for t in taskid_list):
                return ToolResponse(success=False, error="taskid_list contains empty or invalid id")

            tasks_root = workspace_path / "tasks"
            if not tasks_root.exists():
                return ToolResponse(success=False, error=f"tasks root not found: {tasks_root}")

            deleted: List[Dict[str, Any]] = []
            missing: List[str] = []
            errors: List[Dict[str, Any]] = []

            for tid in taskid_list:
                target_path = tasks_root / tid
                if not target_path.exists():
                    missing.append(tid)
                    if stop_on_error:
                        return ToolResponse(
                            success=False,
                            error=f"task not found: {tid}",
                            data={
                                "missing": missing,
                                "deleted": deleted,
                                "errors": errors,
                            },
                        )
                    continue
                try:
                    if target_path.is_dir():
                        shutil.rmtree(target_path)
                    else:
                        # 若为文件（非预期），也尝试删除
                        os.remove(target_path)
                    deleted.append({"task_id": tid, "path": str(target_path)})
                except Exception as ex:
                    err = {"task_id": tid, "path": str(target_path), "error": str(ex)}
                    errors.append(err)
                    if stop_on_error:
                        return ToolResponse(
                            success=False,
                            error=f"failed to delete: {tid}",
                            data={
                                "missing": missing,
                                "deleted": deleted,
                                "errors": errors,
                            },
                        )

            success = len(errors) == 0 and True
            return ToolResponse(
                success=success,
                data={
                    "requested": taskid_list,
                    "deleted_count": len(deleted),
                    "deleted": deleted,
                    "missing": missing,
                    "errors": errors,
                },
                error=(None if success else "some tasks failed to delete"),
            )
        except Exception as e:
            return ToolResponse(success=False, error=str(e))