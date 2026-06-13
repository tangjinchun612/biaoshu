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
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CriteriaItem(BaseModel):
    category: str
    requirement: str
    location: str
    is_mandatory: bool


class BidContentItem(BaseModel):
    criteria_index: int
    matched_text: str


class ComparisonItem(BaseModel):
    criteria_index: int
    status: str
    severity: str
    issues: List[str]
    suggestions: List[str]


class TaskResult(BaseModel):
    task_id: str
    requirements_count: int
    issues_count: int
    score: float
    criteria: List[CriteriaItem]
    bid_contents: List[BidContentItem]
    comparisons: List[ComparisonItem]


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
