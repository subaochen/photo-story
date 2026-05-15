from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.upload.router import router as upload_router
from backend.tasks.pipeline import router as tasks_router
from backend.story.router import router as story_router
from backend.auth.router import router as auth_router
from backend.pay.router import router as pay_router
from backend.tasks.state import router as tasks_status_router, ws_router, manager as ws_manager

app = FastAPI(title="PhotoStory", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers with own prefixes defined: upload (/api/v1/upload), pay (/api/v1/pay), auth (/api/v1/auth), story (/api/v1/story), tasks states (/api/v1/tasks)
app.include_router(upload_router)
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(story_router)
app.include_router(auth_router)
app.include_router(pay_router)
app.include_router(tasks_status_router)
app.include_router(ws_router)


@app.websocket("/ws/task/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    await ws_manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(task_id, websocket)
    except Exception:
        ws_manager.disconnect(task_id, websocket)


@app.get("/health")
async def health():
    return {"status": "ok"}
