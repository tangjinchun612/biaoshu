import os
import json
import uuid
import base64
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from api.models import (
    FileType, TaskStatus, FileUploadResponse, TaskCreateRequest, 
    TaskCreateResponse, TaskStatusResponse, TaskListResponse, ErrorResponse
)
from api.database import (
    init_database, create_file, get_file, create_task, get_task,
    update_task_status, list_tasks, delete_task
)
from core.config import load_config
from core.analyzer import Analyzer
from core.report_generator import ReportGenerator


router = APIRouter(prefix="/api/v1")

init_database()

UPLOAD_DIR = "uploads"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...)
):
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    filename = f"{file_id}{ext}"
    filepath = Path(UPLOAD_DIR) / filename
    
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    from doc_processor import file_hash
    fhash = file_hash(content)
    
    create_file(
        filename=file.filename,
        file_type=file_type.value,
        file_path=str(filepath),
        file_hash=fhash
    )
    
    return FileUploadResponse(
        file_id=file_id,
        filename=file.filename,
        file_type=file_type,
        uploaded_at=datetime.now()
    )


@router.post("/tasks/create", response_model=TaskCreateResponse)
async def create_analysis_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks
):
    tender_file = get_file(request.tender_file_id)
    if not tender_file:
        raise HTTPException(status_code=404, detail="招标文件不存在")
    
    bid_file = get_file(request.bid_file_id)
    if not bid_file:
        raise HTTPException(status_code=404, detail="标书文件不存在")
    
    if tender_file['file_type'] != 'tender':
        raise HTTPException(status_code=400, detail="文件类型错误，应为招标文件")
    
    if bid_file['file_type'] != 'bid':
        raise HTTPException(status_code=400, detail="文件类型错误，应为标书文件")
    
    config_json = None
    if request.config:
        config_json = json.dumps(request.config)
    
    task_id = create_task(
        tender_file_id=request.tender_file_id,
        bid_file_id=request.bid_file_id,
        config_override=config_json
    )
    
    background_tasks.add_task(
        run_analysis_task,
        task_id=task_id,
        tender_file_path=tender_file['file_path'],
        bid_file_path=bid_file['file_path']
    )
    
    return TaskCreateResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        created_at=datetime.now()
    )


async def run_analysis_task(task_id: str, tender_file_path: str, bid_file_path: str):
    try:
        update_task_status(task_id, "processing", progress=0)
        
        config = load_config()
        analyzer = Analyzer(config=config)
        
        def progress_callback(progress: int):
            update_task_status(task_id, "processing", progress=progress)
        
        result = analyzer.analyze(
            task_id=task_id,
            tender_file_path=tender_file_path,
            bid_file_path=bid_file_path,
            progress_callback=progress_callback
        )
        
        report_generator = ReportGenerator()
        report_generator.save_report(result, "json")
        
        update_task_status(
            task_id, 
            "completed", 
            progress=100,
            result_json=json.dumps(result)
        )
        
    except Exception as e:
        update_task_status(task_id, "failed", error_message=str(e))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatusResponse(
        task_id=task['task_id'],
        status=TaskStatus(task['status']),
        progress=task['progress'],
        created_at=task['created_at'],
        updated_at=task['updated_at']
    )


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str, format: str = "json"):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail="任务未完成")
    
    if not task['result_json']:
        raise HTTPException(status_code=500, detail="结果数据不存在")
    
    result = json.loads(task['result_json'])
    
    if format == "json":
        return result
    
    report_generator = ReportGenerator()
    
    if format == "markdown":
        return {"markdown": report_generator.generate_markdown(result)}
    
    elif format == "word":
        word_bytes = report_generator.generate_word(result)
        return {"word_base64": base64.b64encode(word_bytes).decode()}
    
    else:
        raise HTTPException(status_code=400, detail="不支持的格式")


@router.get("/tasks/{task_id}/download")
async def download_report(task_id: str, format: str = "markdown"):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail="任务未完成")
    
    result = json.loads(task['result_json'])
    
    report_generator = ReportGenerator()
    filepath = report_generator.save_report(result, format)
    
    return FileResponse(
        filepath,
        media_type='application/octet-stream',
        filename=f"report_{task_id}.{format}"
    )


@router.get("/tasks", response_model=TaskListResponse)
async def get_task_list(
    status: Optional[TaskStatus] = None,
    page: int = 1,
    page_size: int = 10
):
    result = list_tasks(
        status=status.value if status else None,
        page=page,
        page_size=page_size
    )
    
    return TaskListResponse(**result)


@router.delete("/tasks/{task_id}")
async def delete_analysis_task(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    deleted = delete_task(task_id)
    if deleted:
        return {"success": True, "message": "任务已删除"}
    else:
        raise HTTPException(status_code=500, detail="删除失败")
