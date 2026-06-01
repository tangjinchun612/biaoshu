from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    TENDER = "tender"
    BID = "bid"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: FileType
    uploaded_at: datetime


class TaskCreateRequest(BaseModel):
    tender_file_id: str
    bid_file_id: str
    config: Optional[Dict[str, Any]] = None


class TaskCreateResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int
    created_at: datetime
    updated_at: datetime


class RequirementItem(BaseModel):
    category: str
    requirement: str
    location: str
    is_mandatory: bool


class AnalysisResult(BaseModel):
    status: str
    severity: str
    issues: List[str]
    suggestions: List[str]


class RequirementAnalysis(BaseModel):
    requirement: RequirementItem
    analysis: AnalysisResult
    bid_response_text: str


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    requirements_count: int
    issues_count: int
    score: float
    analyses: List[RequirementAnalysis]
    created_at: datetime
    completed_at: datetime


class TaskListItem(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    tasks: List[TaskListItem]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    detail: str
