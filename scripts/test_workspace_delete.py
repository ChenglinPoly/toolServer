import asyncio
import os
from pathlib import Path

from tools.file_tools import WorkspaceDeleteTasksTool


def prepare_task_dir(root: Path, task_id: str):
    target = root / "tasks" / task_id
    target.mkdir(parents=True, exist_ok=True)
    # 写入一个小文件便于确认
    inner = target / "_probe.txt"
    inner.write_text("probe", encoding="utf-8")


async def run_case(name: str, **kwargs):
    tool = WorkspaceDeleteTasksTool()
    try:
        resp = await tool.execute(**kwargs)
        print(f"CASE: {name}")
        print(f"  success: {resp.success}")
        if resp.error:
            print(f"  error: {resp.error}")
        if resp.data:
            print(f"  data: {resp.data}")
    except Exception as e:
        print(f"CASE: {name}")
        print(f"  EXCEPTION: {e}")


async def main():
    workspace_root = Path("/home/colin/project/AI_Researcher/toolServer/workspace")
    default_task = "default"

    # 准备两个待删除的临时任务
    prepare_task_dir(workspace_root, "tmp_del_a")
    prepare_task_dir(workspace_root, "tmp_del_b")

    # 案例1：删除存在的任务列表
    await run_case(
        "delete_existing",
        task_id=default_task,
        workspace_path=workspace_root,
        taskid_list=["tmp_del_a", "tmp_del_b"],
        stop_on_error=False,
    )

    # 案例2：删除缺失任务（不终止）
    await run_case(
        "delete_missing_no_stop",
        task_id=default_task,
        workspace_path=workspace_root,
        taskid_list=["missing_x"],
        stop_on_error=False,
    )

    # 案例3：先准备一个再与缺失混合，遇缺失立即终止
    prepare_task_dir(workspace_root, "tmp_del_c")
    await run_case(
        "delete_mixed_stop_on_missing",
        task_id=default_task,
        workspace_path=workspace_root,
        taskid_list=["tmp_del_c", "missing_y"],
        stop_on_error=True,
    )


if __name__ == "__main__":
    asyncio.run(main())


