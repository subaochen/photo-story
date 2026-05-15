import logging
from typing import Dict, Optional, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi import HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)

task_state: Dict[str, dict] = {}

STATUS_VALUES = {"pending", "processing", "completed", "failed"}
STAGE_VALUES = {"upload", "dedup", "aesthetics", "faces", "scenes", "cluster", "story", "export", "complete"}


def create_task(task_id: str, **kwargs) -> dict:
    entry = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0.0,
        "stage": "upload",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
        "result": None,
        "user_id": None,
        "generate_story": kwargs.get("generate_story", False),
        "output_format": kwargs.get("output_format", "json"),
        "top_k": kwargs.get("top_k", 100),
        "input_dir": kwargs.get("input_dir"),
        "output_dir": kwargs.get("output_dir"),
    }
    task_state[task_id] = entry
    return entry


def update_task(task_id: str, **kwargs):
    if task_id not in task_state:
        raise ValueError(f"Task {task_id} not found")
    task_state[task_id].update(kwargs)


def get_task(task_id: str) -> Optional[dict]:
    return task_state.get(task_id)


def delete_task(task_id: str) -> bool:
    if task_id in task_state:
        del task_state[task_id]
        return True
    return False


def update_progress(task_id: str, progress: float, stage: str):
    if task_id not in task_state:
        raise ValueError(f"Task {task_id} not found")
    task_state[task_id]["progress"] = progress
    task_state[task_id]["stage"] = stage


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, list] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            dead = []
            for conn in self.active_connections[task_id]:
                try:
                    await conn.send_json(message)
                except Exception:
                    dead.append(conn)
            for conn in dead:
                self.disconnect(task_id, conn)


manager = ConnectionManager()

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@router.get("/{task_id}/results")
async def get_task_results(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task {task_id} is not completed (status: {task['status']})")
    return task.get("result", {})


@router.delete("/{task_id}")
async def delete_task_endpoint(task_id: str):
    if not delete_task(task_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {"status": "deleted", "task_id": task_id}


class StoryRequest(BaseModel):
    template: str = Field(default="default")
    title: str = Field(default="My Photo Story")
    custom_prompt: Optional[str] = Field(default=None)


@router.post("/{task_id}/story")
async def trigger_story(task_id: str, request: StoryRequest):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    update_task(task_id, stage="story", status="processing")

    mock_story = {
        "title": request.title,
        "narrative": [
            {
                "chapter": 1,
                "title": "Getting Started",
                "summary": "Story generated",
                "photos": [],
                "story": "This is a placeholder story."
            }
        ]
    }

    update_task(task_id, result=mock_story)
    await manager.broadcast(task_id, {"type": "story_generated", "data": mock_story})
    return mock_story


ws_router = APIRouter()


@ws_router.websocket("/ws/task/{task_id}")
async def websocket_task_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
    except Exception:
        manager.disconnect(task_id, websocket)
