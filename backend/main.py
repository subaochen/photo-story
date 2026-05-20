import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.upload.router import router as upload_router
from backend.tasks.pipeline import router as tasks_router
from backend.story.router import router as story_router
from backend.auth.router import router as auth_router
from backend.pay.router import router as pay_router
from backend.tasks.state import router as tasks_status_router, ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="PhotoStory", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(story_router)
app.include_router(auth_router)
app.include_router(pay_router)
app.include_router(tasks_status_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
