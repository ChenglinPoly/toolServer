import asyncio
from pathlib import Path

from tools.file_tools import WorkspaceCopyTool


async def run_case(name: str, **kwargs):
    tool = WorkspaceCopyTool()
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

    cases = [
        {
            "name": "source_not_exist",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="not_exist",
                numV=1,
                copyid_list=["x1"],
            ),
        },
        {
            "name": "empty_source",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="",
                numV=1,
                copyid_list=["x1"],
            ),
        },
        {
            "name": "numV_zero",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="test",
                numV=0,
                copyid_list=["x1"],
            ),
        },
        {
            "name": "empty_list",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="test",
                numV=1,
                copyid_list=[],
            ),
        },
        {
            "name": "length_mismatch",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="test",
                numV=2,
                copyid_list=["x1"],
            ),
        },
        {
            "name": "duplicate_ids",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="test",
                numV=2,
                copyid_list=["x1", "x1"],
            ),
        },
        {
            "name": "contains_source_id",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="test",
                numV=1,
                copyid_list=["test"],
            ),
        },
        {
            "name": "target_already_exists",
            "kwargs": dict(
                task_id=default_task,
                workspace_path=workspace_root,
                copyed_taskid="test",
                numV=2,
                copyid_list=["test1", "test2"],
            ),
        },
    ]

    for case in cases:
        await run_case(case["name"], **case["kwargs"]) 


if __name__ == "__main__":
    asyncio.run(main())


