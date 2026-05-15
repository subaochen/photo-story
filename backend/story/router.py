from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional

from .generator import generate_story

router = APIRouter(prefix="/api/v1/story", tags=["story"])


class StoryGenerateRequest(BaseModel):
    photos: list
    metadata: dict = Field(default_factory=dict)
    template: str = Field(default="timeline")
    title: str = Field(default="")
    custom_prompt: Optional[str] = Field(default=None)


class TaskStateStore:
    tasks = {}


@router.post("/generate")
async def post_generate(request: StoryGenerateRequest, background_tasks: BackgroundTasks):
    import uuid
    task_id = str(uuid.uuid4())
    TaskStateStore.tasks[task_id] = {"status": "pending", "task_id": task_id}

    async def _run():
        TaskStateStore.tasks[task_id]["status"] = "running"
        try:
            story = generate_story(
                photos=request.photos,
                metadata=request.metadata,
                template=request.template,
                title=request.title,
                custom_prompt=request.custom_prompt or "",
            )
            TaskStateStore.tasks[task_id] = {"status": "completed", "task_id": task_id, "story": story}
        except Exception as e:
            TaskStateStore.tasks[task_id] = {"status": "failed", "task_id": task_id, "error": str(e)}

    background_tasks.add_task(_run)

    return {"task_id": task_id, "status": "pending"}


@router.get("/{task_id}")
async def get_story_status(task_id: str):
    task = TaskStateStore.tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Story task {task_id} not found")
    return task
