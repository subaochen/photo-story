import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.orchestrator import run_pipeline_verbose

from .state import (
    manager,
    ConnectionManager,
    create_task,
    update_task,
    get_task,
    update_progress,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class StoryRequest(BaseModel):
    template: str = Field(default="default")
    title: str = Field(default="My Photo Story")
    custom_prompt: Optional[str] = Field(default=None)


async def execute_pipeline(
    task_id: str,
    input_dir: str,
    output_dir: str,
    top_k: int,
    generate_story: bool,
    output_format: str,
    manager: ConnectionManager,
) -> None:
    try:
        update_task(task_id, status="processing")
        await manager.broadcast(task_id, {"type": "status_update", "status": "processing", "progress": 10, "stage": "upload"})

        update_progress(task_id, progress=20, stage="dedup")
        await manager.broadcast(task_id, {"type": "progress", "progress": 20, "stage": "dedup"})

        update_progress(task_id, progress=40, stage="aesthetics")
        await manager.broadcast(task_id, {"type": "progress", "progress": 40, "stage": "aesthetics"})

        update_progress(task_id, progress=60, stage="faces")
        await manager.broadcast(task_id, {"type": "progress", "progress": 60, "stage": "faces"})

        update_progress(task_id, progress=70, stage="scenes")
        await manager.broadcast(task_id, {"type": "progress", "progress": 70, "stage": "scenes"})

        update_progress(task_id, progress=80, stage="cluster")
        await manager.broadcast(task_id, {"type": "progress", "progress": 80, "stage": "cluster"})

        result = await asyncio.to_thread(
            run_pipeline_verbose,
            input_dir=input_dir,
            output_dir=output_dir,
            top_k=top_k,
        )

        update_task(
            task_id,
            status="completed",
            progress=100,
            stage="complete",
            result=result,
        )
        await manager.broadcast(task_id, {"type": "completed", "progress": 100, "stage": "complete", "result": result})
        logger.info(f"Pipeline task {task_id} completed")

    except Exception as e:
        update_task(task_id, status="failed", error=str(e))
        await manager.broadcast(task_id, {"type": "failed", "error": str(e)})
        logger.error(f"Pipeline task {task_id} failed: {e}")
