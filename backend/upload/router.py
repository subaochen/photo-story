"""文件上传模块路由"""

import os
import uuid
import json
import shutil
import logging
from typing import Dict, Any, Set
from pathlib import Path, PurePath
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Header, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .utils import validate_file_extension, validate_file_size

logger = logging.getLogger(__name__)

CHUNK_SIZE = 5 * 1024 * 1024

upload_tasks: Dict[str, dict] = {}

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])


class InitiateRequest(BaseModel):
    filename: str = Field(..., description="文件名")
    total_size: int = Field(..., description="文件总大小(字节)")
    total_chunks: int = Field(..., description="总分块数")


class CompleteRequest(BaseModel):
    task_id: str = Field(..., description="任务ID")
    generate_story: bool = Field(False, description="是否生成故事")
    output_format: str = Field("pdf", description="输出格式")
    top_k: int = Field(100, description="保留的精选照片数量")


@router.post("/initiate")
async def initiate_upload(request: InitiateRequest):
    if not validate_file_extension(request.filename):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，仅支持: {', '.join(sorted({e.lstrip('.') for e in {'.jpg', '.jpeg', '.png', '.heic'}}))}")

    if not validate_file_size(request.total_size):
        raise HTTPException(status_code=400, detail=f"文件大小超过限制(最大100MB)")

    task_id = str(uuid.uuid4())
    upload_dir = Path(f"/tmp/upload-{task_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)

    upload_tasks[task_id] = {
        "filename": request.filename,
        "total_size": request.total_size,
        "total_chunks": request.total_chunks,
        "uploaded_chunks": set(),
        "status": "initiated",
        "created_at": datetime.now().isoformat(),
    }

    logger.info(f"上传初始化: task_id={task_id}, filename={request.filename}, chunks={request.total_chunks}")

    return {
        "task_id": task_id,
        "chunk_size": CHUNK_SIZE,
        "upload_url": "/api/v1/upload/chunk",
    }


@router.post("/chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    x_task_id: str = Header(..., alias="X-Task-ID"),
    x_chunk_index: int = Header(..., alias="X-Chunk-Index"),
    x_total_chunks: int = Header(..., alias="X-Total-Chunks"),
):
    if x_task_id not in upload_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {x_task_id} 不存在，请先调用 /initiate")

    task = upload_tasks[x_task_id]
    upload_dir = Path(f"/tmp/upload-{x_task_id}")

    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail=f"上传目录不存在")

    chunk_path = upload_dir / f"{x_chunk_index}.part"
    content = await file.read()
    chunk_path.write_bytes(content)

    task["uploaded_chunks"].add(x_chunk_index)
    uploaded_count = len(task["uploaded_chunks"])

    logger.info(f"分块上传: task_id={x_task_id}, chunk={x_chunk_index}/{x_total_chunks}")

    return {
        "chunk_index": x_chunk_index,
        "status": "uploaded",
        "uploaded_chunks": uploaded_count,
        "total_chunks": task["total_chunks"],
    }


@router.post("/complete")
async def complete_upload(request: CompleteRequest):
    task_id = request.task_id

    if task_id not in upload_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    task = upload_tasks[task_id]
    upload_dir = Path(f"/tmp/upload-{task_id}")

    if len(task["uploaded_chunks"]) != task["total_chunks"]:
        missing = set(range(task["total_chunks"])) - task["uploaded_chunks"]
        raise HTTPException(status_code=400, detail=f"分块不完整，缺失: {sorted(missing)}")

    for i in range(task["total_chunks"]):
        chunk_path = upload_dir / f"{i}.part"
        if not chunk_path.exists():
            raise HTTPException(status_code=400, detail=f"分块 {i} 文件不存在")

    safe_name = Path(PurePath(task["filename"]).name)
    output_path = upload_dir / safe_name
    with open(output_path, "wb") as out:
        for i in range(task["total_chunks"]):
            chunk_path = upload_dir / f"{i}.part"
            out.write(chunk_path.read_bytes())

    metadata = {
        "task_id": task_id,
        "filename": task["filename"],
        "total_size": task["total_size"],
        "total_chunks": task["total_chunks"],
        "generate_story": request.generate_story,
        "output_format": request.output_format,
        "top_k": request.top_k,
        "completed_at": datetime.now().isoformat(),
    }
    (upload_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    task["status"] = "processing"

    logger.info(f"上传完成: task_id={task_id}, merged to {output_path}")

    return {
        "task_id": task_id,
        "status": "processing",
        "progress": 10.0,
        "stage": "dedup",
        "started_at": datetime.now().isoformat(),
    }


@router.get("/status/{task_id}")
async def get_upload_status(task_id: str):
    if task_id not in upload_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    task = upload_tasks[task_id]
    uploaded_count = len(task["uploaded_chunks"])

    return {
        "task_id": task_id,
        "status": task["status"],
        "filename": task["filename"],
        "total_chunks": task["total_chunks"],
        "uploaded_chunks": uploaded_count,
        "progress": round(uploaded_count / task["total_chunks"] * 100, 1) if task["total_chunks"] > 0 else 0,
        "created_at": task["created_at"],
    }


@router.delete("/{task_id}")
async def delete_upload(task_id: str):
    if task_id not in upload_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    upload_dir = Path(f"/tmp/upload-{task_id}")
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    del upload_tasks[task_id]
    logger.info(f"上传清理: task_id={task_id}")

    return {"task_id": task_id, "status": "deleted"}
