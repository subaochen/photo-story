"""FastAPI 后端服务

PhotoStory Pipeline 后端 API 服务器
支持图片去重、美学评分、人脸识别、场景分类、地点聚类等功能
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

# 导入 pipeline 模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import run_pipeline_verbose
from src.pipeline.orchestrator import collect_images

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 FastAPI 应用
app = FastAPI(
    title="PhotoStory Pipeline API",
    description="图片智能整理 Pipeline API 服务",
    version="1.0.0"
)

# 全局状态管理
pipeline_tasks: Dict[str, Dict[str, Any]] = {}


# 请求/响应模型
class PipelineRunRequest(BaseModel):
    """Pipeline 运行请求"""
    input_dir: str = Field(..., description="输入目录路径")
    output_dir: str = Field(..., description="输出目录路径")
    top_k: int = Field(100, ge=1, le=1000, description="保留的精选照片数量")
    dhash_threshold: int = Field(5, ge=0, le=64, description="dHash 海明距离阈值")
    clip_threshold: float = Field(0.92, ge=0.0, le=1.0, description="CLIP 余弦相似度阈值")


class PipelineRunResponse(BaseModel):
    """Pipeline 运行响应"""
    task_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="任务状态")


class PipelineStatusResponse(BaseModel):
    """Pipeline 状态响应"""
    task_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="任务状态")
    progress: float = Field(..., description="进度 (0-100)")
    started_at: Optional[str] = Field(None, description="任务开始时间")
    completed_at: Optional[str] = Field(None, description="任务完成时间")
    error: Optional[str] = Field(None, description="错误信息")


class DedupGroupsResponse(BaseModel):
    """去重分组响应"""
    stage1_dedup: Dict[str, Any]
    stage2_dedup: Dict[str, Any]
    dhash_groups: list
    clip_groups: list
    final_results: list
    summary: Dict[str, Any]


class AestheticsRankingResponse(BaseModel):
    """美学评分响应"""
    ranking: list
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]


class FacesDetectionResponse(BaseModel):
    """人脸检测响应"""
    faces: Dict[str, list]
    summary: Dict[str, Any]


class SceneClassificationResponse(BaseModel):
    """场景分类响应"""
    scenes: Dict[str, Dict[str, Any]]
    summary: Dict[str, Any]


class ClusterResponse(BaseModel):
    """聚类响应"""
    clusters: list
    summary: Dict[str, Any]


# 任务状态
class PipelineTask:
    """Pipeline 任务状态管理"""
    
    def __init__(self, task_id: str, request: PipelineRunRequest):
        self.task_id = task_id
        self.request = request
        self.status = "pending"
        self.progress = 0.0
        self.started_at = None
        self.completed_at = None
        self.error = None
        self.result = None
    
    def start(self):
        self.status = "running"
        self.started_at = datetime.now().isoformat()
        self.progress = 10.0  # 收集图片
    
    def complete(self, result: dict):
        self.status = "completed"
        self.completed_at = datetime.now().isoformat()
        self.progress = 100.0
        self.result = result
    
    def fail(self, error: str):
        self.status = "failed"
        self.completed_at = datetime.now().isoformat()
        self.error = error


# API 端点
@app.get("/")
async def root():
    """根路径 - API 信息"""
    return {
        "name": "PhotoStory Pipeline API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/api/pipeline/run",
            "/api/pipeline/status/{task_id}",
            "/api/dedup/groups",
            "/api/aesthetics/ranking",
            "/api/faces/detection",
            "/api/scene/classification",
            "/api/cluster"
        ]
    }


@app.post("/api/pipeline/run")
async def run_pipeline_api(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks
) -> PipelineRunResponse:
    """启动 Pipeline 处理任务"""
    task_id = str(uuid.uuid4())
    
    # 创建任务并保存状态
    task = PipelineTask(task_id, request)
    pipeline_tasks[task_id] = task
    
    # 异步执行任务
    async def execute_pipeline():
        try:
            task.start()
            
            # 创建输出目录
            output_path = Path(request.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 运行 pipeline
            result = run_pipeline_verbose(
                input_dir=request.input_dir,
                output_dir=request.output_dir,
                top_k=request.top_k,
                dhash_threshold=request.dhash_threshold,
                clip_threshold=request.clip_threshold
            )
            
            task.complete(result)
            logger.info(f"Pipeline 任务 {task_id} 完成")
            
        except Exception as e:
            task.fail(str(e))
            logger.error(f"Pipeline 任务 {task_id} 失败: {e}")
    
    background_tasks.add_task(execute_pipeline)
    
    return PipelineRunResponse(
        task_id=task_id,
        status="started"
    )


@app.get("/api/pipeline/status/{task_id}")
async def get_pipeline_status(task_id: str) -> PipelineStatusResponse:
    """查询 Pipeline 任务状态"""
    if task_id not in pipeline_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = pipeline_tasks[task_id]
    
    return PipelineStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error=task.error
    )


@app.get("/api/dedup/groups")
async def get_dedup_groups(task_id: str) -> DedupGroupsResponse:
    """获取去重分组信息"""
    if task_id not in pipeline_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = pipeline_tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务 {task_id} 尚未完成")
    
    if not task.result or "dedup" not in task.result:
        raise HTTPException(status_code=404, detail="去重信息不存在")
    
    dedup = task.result["dedup"]
    
    return DedupGroupsResponse(
        stage1_dedup=dedup.get("stage1_dedup", {}),
        stage2_dedup=dedup.get("stage2_dedup", {}),
        dhash_groups=dedup.get("dhash_groups", []),
        clip_groups=dedup.get("clip_groups", []),
        final_results=dedup.get("final_results", []),
        summary=dedup.get("summary", {})
    )


@app.get("/api/aesthetics/ranking")
async def get_aesthetics_ranking(task_id: str) -> AestheticsRankingResponse:
    """获取美学评分排名"""
    if task_id not in pipeline_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = pipeline_tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务 {task_id} 尚未完成")
    
    if not task.result or "aesthetics" not in task.result:
        raise HTTPException(status_code=404, detail="美学评分信息不存在")
    
    aesthetics = task.result["aesthetics"]
    
    return AestheticsRankingResponse(
        ranking=aesthetics.get("ranking", []),
        statistics=aesthetics.get("statistics", {}),
        metadata=aesthetics.get("metadata", {})
    )


@app.get("/api/faces/detection")
async def get_faces_detection(task_id: str) -> FacesDetectionResponse:
    """获取人脸检测结果"""
    if task_id not in pipeline_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = pipeline_tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务 {task_id} 尚未完成")
    
    if not task.result or "faces" not in task.result:
        raise HTTPException(status_code=404, detail="人脸检测信息不存在")
    
    faces = task.result["faces"]
    
    # 统计信息
    total_faces = sum(len(f) for f in faces.values())
    
    return FacesDetectionResponse(
        faces=faces,
        summary={
            "total_images": len(faces),
            "total_faces": total_faces,
            "images_with_faces": len([f for f in faces.values() if f])
        }
    )


@app.get("/api/scene/classification")
async def get_scene_classification(task_id: str) -> SceneClassificationResponse:
    """获取场景分类结果"""
    if task_id not in pipeline_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = pipeline_tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务 {task_id} 尚未完成")
    
    if not task.result or "scenes" not in task.result:
        raise HTTPException(status_code=404, detail="场景分类信息不存在")
    
    scenes = task.result["scenes"]
    
    # 统计场景分布
    scene_distribution = {}
    for path, scene_info in scenes.items():
        for scene, prob in scene_info.items():
            if scene not in scene_distribution:
                scene_distribution[scene] = 0
            scene_distribution[scene] += 1
    
    return SceneClassificationResponse(
        scenes=scenes,
        summary={
            "total_images": len(scenes),
            "scene_distribution": scene_distribution
        }
    )


@app.get("/api/cluster")
async def get_cluster(task_id: str) -> ClusterResponse:
    """获取地点/时间聚类结果"""
    if task_id not in pipeline_tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = pipeline_tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务 {task_id} 尚未完成")
    
    if not task.result or "clusters" not in task.result:
        raise HTTPException(status_code=404, detail="聚类信息不存在")
    
    clusters = task.result["clusters"]
    
    return ClusterResponse(
        clusters=clusters.get("clusters", []),
        summary=clusters.get("summary", {})
    )


# 错误处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.error(f"全局异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误，请查看日志"}
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PhotoStory Pipeline API Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开发模式，热重载")
    
    args = parser.parse_args()
    
    logger.info(f"启动 API 服务器: {args.host}:{args.port}")
    
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
