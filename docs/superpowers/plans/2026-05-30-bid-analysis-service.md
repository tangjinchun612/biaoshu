# 标书对比分析服务实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个支持上传标书和招标文件，自动对比分析并生成报告的后端API服务

**Architecture:** 基于FastAPI的异步服务，复用现有RAG检索和文档处理模块，新增任务管理、配置管理和报告生成功能

**Tech Stack:** FastAPI, SQLite, Qdrant, Claude/Qwen LLM, python-docx, PyYAML

---

## 文件结构

```
zhaobiao/
├── app.py                    # 现有Streamlit应用（保留）
├── retriever.py              # 现有检索模块（扩展）
├── doc_processor.py          # 现有文档处理（保留）
├── indexer.py                # 现有索引模块（保留）
├── data.py                   # 现有数据模块（保留）
│
├── api/                      # 新增：API服务
│   ├── __init__.py
│   ├── main.py              # FastAPI入口
│   ├── routes.py            # API路由定义
│   ├── models.py            # 数据模型（Pydantic）
│   └── database.py          # SQLite任务管理
│
├── core/                     # 新增：核心业务逻辑
│   ├── __init__.py
│   ├── analyzer.py          # 分析引擎
│   ├── llm_client.py        # LLM客户端
│   ├── report_generator.py  # 报告生成
│   └── config.py            # 配置管理
│
├── config.yaml              # 新增：配置文件
├── uploads/                 # 新增：上传文件存储
├── tasks/                   # 新增：任务结果存储
│
├── tests/                   # 新增：测试目录
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_analyzer.py
│   └── test_report.py
│
├── requirements.txt         # 更新依赖
└── docker-compose.yml       # 更新部署配置
```

---

## Task 1: 创建配置文件和配置管理模块

**Files:**
- Create: `config.yaml`
- Create: `core/__init__.py`
- Create: `core/config.py`

- [ ] **Step 1: 创建配置文件**

```yaml
# config.yaml

# 对比维度配置
dimensions:
  - name: "资质要求"
    description: "企业资质、人员证书、业绩要求等"
    weight: 30
    
  - name: "技术规范"
    description: "技术参数、方案要求、工期等"
    weight: 40
    
  - name: "商务条款"
    description: "报价、付款方式、违约责任等"
    weight: 30

# 提示词配置
prompts:
  extract_requirements: |
    你是一位专业的招标文件分析师。请分析以下招标文件内容，提取所有实质性要求。
    
    【输出格式】
    请以JSON数组格式输出，每个要求包含：
    - category: 所属类别（如"资质要求"/"技术规范"/"商务条款"）
    - requirement: 具体要求内容
    - location: 在文档中的位置（章节/页码）
    - is_mandatory: 是否为强制性要求（true/false）
    
    【招标文件内容】
    {tender_content}
    
  compare_analysis: |
    你是一位专业的标书审查专家。请对比分析以下招标要求和标书响应。
    
    【招标要求】
    {requirement}
    
    【标书响应内容】
    {bid_response}
    
    【分析要求】
    1. 判断标书是否完全响应了招标要求
    2. 识别缺失、偏差或不一致之处
    3. 评估问题严重程度（严重/一般/轻微）
    4. 给出具体修改建议
    
    【输出格式】
    请以JSON格式输出：
    {
      "status": "符合/部分符合/不符合",
      "severity": "严重/一般/轻微",
      "issues": ["问题1", "问题2"],
      "suggestions": ["建议1", "建议2"]
    }

# 评分规则配置
scoring:
  severity_weights:
    "严重": 10
    "一般": 5
    "轻微": 2
  pass_threshold: 80

# 输出配置
output:
  formats: ["json", "markdown", "word"]
  default_format: "json"
  include_original_text: true
```

- [ ] **Step 2: 创建core模块init文件**

```python
# core/__init__.py
```

- [ ] **Step 3: 创建配置管理模块**

```python
# core/config.py

import yaml
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel


class Dimension(BaseModel):
    name: str
    description: str
    weight: int


class Prompts(BaseModel):
    extract_requirements: str
    compare_analysis: str


class Scoring(BaseModel):
    severity_weights: Dict[str, int]
    pass_threshold: int


class OutputConfig(BaseModel):
    formats: List[str]
    default_format: str
    include_original_text: bool


class AppConfig(BaseModel):
    dimensions: List[Dimension]
    prompts: Prompts
    scoring: Scoring
    output: OutputConfig


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """加载配置文件"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return AppConfig(**data)


def get_extraction_prompt(config: AppConfig, tender_content: str) -> str:
    """获取需求提取提示词"""
    return config.prompts.extract_requirements.format(
        tender_content=tender_content
    )


def get_comparison_prompt(config: AppConfig, requirement: str, bid_response: str) -> str:
    """获取对比分析提示词"""
    return config.prompts.compare_analysis.format(
        requirement=requirement,
        bid_response=bid_response
    )
```

- [ ] **Step 4: 验证配置加载**

```bash
cd /Users/tangjinchun/Documents/biao_shu/zhaobiao
python -c "from core.config import load_config; config = load_config(); print(f'Loaded {len(config.dimensions)} dimensions')"
```

Expected: `Loaded 3 dimensions`

- [ ] **Step 5: 提交代码**

```bash
git add config.yaml core/__init__.py core/config.py
git commit -m "feat: add config management module"
```

---

## Task 2: 创建数据库管理模块

**Files:**
- Create: `api/__init__.py`
- Create: `api/database.py`

- [ ] **Step 1: 创建api模块init文件**

```python
# api/__init__.py
```

- [ ] **Step 2: 创建数据库管理模块**

```python
# api/database.py

import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


DATABASE_PATH = "tasks/tasks.db"


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            tender_file_id TEXT NOT NULL,
            bid_file_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            result_json TEXT,
            error_message TEXT,
            config_override TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def create_file(filename: str, file_type: str, file_path: str, file_hash: str) -> str:
    """创建文件记录"""
    file_id = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO files (file_id, filename, file_type, file_path, file_hash) VALUES (?, ?, ?, ?, ?)",
        (file_id, filename, file_type, file_path, file_hash)
    )
    
    conn.commit()
    conn.close()
    return file_id


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    """获取文件信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def create_task(tender_file_id: str, bid_file_id: str, config_override: Optional[str] = None) -> str:
    """创建分析任务"""
    task_id = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO tasks (task_id, tender_file_id, bid_file_id, config_override) VALUES (?, ?, ?, ?)",
        (task_id, tender_file_id, bid_file_id, config_override)
    )
    
    conn.commit()
    conn.close()
    return task_id


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def update_task_status(task_id: str, status: str, progress: int = 0, 
                       result_json: Optional[str] = None, error_message: Optional[str] = None):
    """更新任务状态"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """UPDATE tasks 
           SET status = ?, progress = ?, result_json = ?, error_message = ?, updated_at = ?
           WHERE task_id = ?""",
        (status, progress, result_json, error_message, datetime.now(), task_id)
    )
    
    conn.commit()
    conn.close()


def list_tasks(status: Optional[str] = None, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """查询任务列表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * page_size
    
    if status:
        cursor.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, page_size, offset)
        )
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (status,))
        total = cursor.fetchone()[0]
    else:
        cursor.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        )
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total = cursor.fetchone()[0]
    
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size
    }


def delete_task(task_id: str) -> bool:
    """删除任务"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return deleted
```

- [ ] **Step 3: 验证数据库初始化**

```bash
cd /Users/tangjinchun/Documents/biao_shu/zhaobiao
python -c "from api.database import init_database; init_database(); print('Database initialized')"
```

Expected: `Database initialized`

- [ ] **Step 4: 提交代码**

```bash
git add api/__init__.py api/database.py
git commit -m "feat: add database management module"
```

---

## Task 3: 创建Pydantic数据模型

**Files:**
- Create: `api/models.py`

- [ ] **Step 1: 创建数据模型**

```python
# api/models.py

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
    status: str  # 符合/部分符合/不符合
    severity: str  # 严重/一般/轻微
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
```

- [ ] **Step 2: 提交代码**

```bash
git add api/models.py
git commit -m "feat: add Pydantic data models"
```

---

## Task 4: 创建LLM客户端模块

**Files:**
- Create: `core/llm_client.py`

- [ ] **Step 1: 创建LLM客户端**

```python
# core/llm_client.py

import os
import json
from typing import List, Dict, Any, Optional
import anthropic
from openai import OpenAI


# 从app.py提取的模型配置
MODELS = {
    "claude": "claude-opus-4-6",
    "qwen3.5-72b": "qwen3.5-72b",
    "qwen3.5-32b": "qwen3.5-32b",
    "qwen3-max": "qwen3-max-2026-01-23",
    "qwen3-235b-a22b": "qwen3-235b-a22b",
    "qwen3-32b": "qwen3-32b",
    "qwen3-14b": "qwen3-14b",
    "qwen3-8b": "qwen3-8b",
    "qwen-max": "qwen-max",
    "qwen-plus": "qwen-plus",
    "qwen-turbo": "qwen-turbo",
}

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class LLMClient:
    """LLM客户端，支持Claude和Qwen"""
    
    def __init__(self, model_key: str = "qwen-plus"):
        self.model_key = model_key
        self._anthropic_client = None
        self._qwen_client = None
    
    @property
    def anthropic_client(self) -> anthropic.Anthropic:
        if self._anthropic_client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            kwargs = {"api_key": api_key} if api_key else {}
            base_url = os.getenv("ANTHROPIC_BASE_URL")
            if base_url:
                kwargs["base_url"] = base_url
            self._anthropic_client = anthropic.Anthropic(**kwargs)
        return self._anthropic_client
    
    @property
    def qwen_client(self) -> OpenAI:
        if self._qwen_client is None:
            api_key = os.getenv("DASHSCOPE_API_KEY", "")
            self._qwen_client = OpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
        return self._qwen_client
    
    def call(self, messages: List[Dict[str, str]], max_tokens: int = 2048) -> str:
        """同步调用LLM"""
        if self.model_key == "claude":
            return self._call_claude(messages, max_tokens)
        else:
            return self._call_qwen(messages, max_tokens)
    
    def _call_claude(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        """调用Claude模型"""
        response = self.anthropic_client.messages.create(
            model="claude-opus-4-6",
            max_tokens=max_tokens,
            messages=messages
        )
        return response.content[0].text
    
    def _call_qwen(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        """调用Qwen模型"""
        response = self.qwen_client.chat.completions.create(
            model=self.model_key,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def call_json(self, messages: List[Dict[str, str]], max_tokens: int = 2048) -> Dict[str, Any]:
        """调用LLM并解析JSON响应"""
        response_text = self.call(messages, max_tokens)
        
        # 尝试提取JSON
        try:
            # 处理可能的markdown代码块
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM返回的JSON格式无效: {e}\n原始响应: {response_text}")
```

- [ ] **Step 2: 提交代码**

```bash
git add core/llm_client.py
git commit -m "feat: add LLM client module"
```

---

## Task 5: 创建分析引擎模块

**Files:**
- Create: `core/analyzer.py`

- [ ] **Step 1: 创建分析引擎**

```python
# core/analyzer.py

import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.config import AppConfig, load_config, get_extraction_prompt, get_comparison_prompt
from core.llm_client import LLMClient
from retriever import LawRetriever
from doc_processor import process_document


class Analyzer:
    """标书对比分析引擎"""
    
    def __init__(self, config: Optional[AppConfig] = None, model_key: str = "qwen-plus"):
        self.config = config or load_config()
        self.llm = LLMClient(model_key)
        self.retriever = LawRetriever()
    
    def analyze(self, task_id: str, tender_file_path: str, bid_file_path: str, 
                progress_callback=None) -> Dict[str, Any]:
        """
        执行分析任务
        
        Args:
            task_id: 任务ID
            tender_file_path: 招标文件路径
            bid_file_path: 标书路径
            progress_callback: 进度回调函数 callback(progress: int)
        
        Returns:
            分析结果字典
        """
        # 1. 解析文档
        if progress_callback:
            progress_callback(10)
        
        tender_chunks = self._process_file(tender_file_path)
        bid_chunks = self._process_file(bid_file_path)
        
        # 2. 索引文档
        if progress_callback:
            progress_callback(20)
        
        self.retriever.index_doc(tender_chunks, doc_type="tender")
        self.retriever.index_doc(bid_chunks, doc_type="bid")
        
        # 3. 提取招标要求
        if progress_callback:
            progress_callback(30)
        
        requirements = self._extract_requirements(tender_chunks)
        
        # 4. 逐项对比分析
        if progress_callback:
            progress_callback(40)
        
        analyses = []
        total_requirements = len(requirements)
        
        for idx, req in enumerate(requirements):
            # 更新进度
            progress = 40 + int(50 * (idx + 1) / total_requirements)
            if progress_callback:
                progress_callback(progress)
            
            # 从标书中检索相关内容
            bid_response_chunks = self.retriever.retrieve(
                req["requirement"], 
                top_k=3, 
                doc_type="bid"
            )
            bid_response_text = "\n".join([chunk["text"] for chunk in bid_response_chunks])
            
            # LLM对比分析
            analysis = self._compare_requirement(req, bid_response_text)
            
            analyses.append({
                "requirement": req,
                "analysis": analysis,
                "bid_response_text": bid_response_text
            })
        
        # 5. 生成报告
        if progress_callback:
            progress_callback(95)
        
        result = self._generate_result(task_id, analyses)
        
        if progress_callback:
            progress_callback(100)
        
        return result
    
    def _process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """处理文件"""
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        filename = Path(file_path).name
        return process_document(file_bytes, filename)
    
    def _extract_requirements(self, tender_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从招标文件中提取需求"""
        # 合并招标文件内容
        tender_content = "\n\n".join([chunk["text"] for chunk in tender_chunks])
        
        # 构建提示词
        prompt = get_extraction_prompt(self.config, tender_content)
        
        # 调用LLM
        messages = [{"role": "user", "content": prompt}]
        requirements = self.llm.call_json(messages)
        
        return requirements
    
    def _compare_requirement(self, requirement: Dict[str, Any], bid_response: str) -> Dict[str, Any]:
        """对比单个需求"""
        # 构建提示词
        prompt = get_comparison_prompt(
            self.config,
            requirement["requirement"],
            bid_response
        )
        
        # 调用LLM
        messages = [{"role": "user", "content": prompt}]
        analysis = self.llm.call_json(messages)
        
        return analysis
    
    def _generate_result(self, task_id: str, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成分析结果"""
        # 计算统计信息
        issues_count = sum(
            len(a["analysis"].get("issues", []))
            for a in analyses
        )
        
        # 计算得分
        score = self._calculate_score(analyses)
        
        return {
            "task_id": task_id,
            "requirements_count": len(analyses),
            "issues_count": issues_count,
            "score": score,
            "analyses": analyses
        }
    
    def _calculate_score(self, analyses: List[Dict[str, Any]]) -> float:
        """计算得分"""
        if not analyses:
            return 100.0
        
        total_deduction = 0
        severity_weights = self.config.scoring.severity_weights
        
        for a in analyses:
            severity = a["analysis"].get("severity", "轻微")
            weight = severity_weights.get(severity, 2)
            status = a["analysis"].get("status", "符合")
            
            if status == "不符合":
                total_deduction += weight
            elif status == "部分符合":
                total_deduction += weight * 0.5
        
        score = max(0, 100 - total_deduction)
        return round(score, 2)
```

- [ ] **Step 2: 提交代码**

```bash
git add core/analyzer.py
git commit -m "feat: add analyzer engine module"
```

---

## Task 6: 创建报告生成模块

**Files:**
- Create: `core/report_generator.py`

- [ ] **Step 1: 创建报告生成器**

```python
# core/report_generator.py

import json
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


class ReportGenerator:
    """报告生成器"""
    
    def generate(self, result: Dict[str, Any], format: str = "json") -> Any:
        """生成报告"""
        if format == "json":
            return self.generate_json(result)
        elif format == "markdown":
            return self.generate_markdown(result)
        elif format == "word":
            return self.generate_word(result)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def generate_json(self, result: Dict[str, Any]) -> str:
        """生成JSON格式报告"""
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def generate_markdown(self, result: Dict[str, Any]) -> str:
        """生成Markdown格式报告"""
        lines = []
        lines.append("# 标书对比分析报告\n")
        lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**任务ID:** {result['task_id']}\n")
        
        # 概览
        lines.append("## 分析概览\n")
        lines.append(f"- **需求数量:** {result['requirements_count']}")
        lines.append(f"- **问题数量:** {result['issues_count']}")
        lines.append(f"- **综合得分:** {result['score']}分\n")
        
        # 详细分析
        lines.append("## 详细分析\n")
        
        for idx, analysis in enumerate(result['analyses'], 1):
            req = analysis['requirement']
            result_item = analysis['analysis']
            
            lines.append(f"### {idx}. {req['category']} - {req['requirement'][:50]}...\n")
            lines.append(f"**位置:** {req['location']}")
            lines.append(f"**是否强制:** {'是' if req['is_mandatory'] else '否'}\n")
            
            # 分析结果
            status = result_item.get('status', '未知')
            severity = result_item.get('severity', '未知')
            
            if status == '符合':
                lines.append(f"✅ **状态:** {status}")
            elif status == '部分符合':
                lines.append(f"⚠️ **状态:** {status}")
            else:
                lines.append(f"❌ **状态:** {status}")
            
            lines.append(f"**严重程度:** {severity}\n")
            
            # 问题
            issues = result_item.get('issues', [])
            if issues:
                lines.append("**问题:**")
                for issue in issues:
                    lines.append(f"- {issue}")
                lines.append("")
            
            # 建议
            suggestions = result_item.get('suggestions', [])
            if suggestions:
                lines.append("**修改建议:**")
                for suggestion in suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")
            
            lines.append("---\n")
        
        return "\n".join(lines)
    
    def generate_word(self, result: Dict[str, Any]) -> bytes:
        """生成Word格式报告"""
        doc = Document()
        
        # 标题
        title = doc.add_heading('标书对比分析报告', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 基本信息
        doc.add_paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"任务ID: {result['task_id']}")
        
        # 概览
        doc.add_heading('分析概览', level=1)
        doc.add_paragraph(f"需求数量: {result['requirements_count']}")
        doc.add_paragraph(f"问题数量: {result['issues_count']}")
        doc.add_paragraph(f"综合得分: {result['score']}分")
        
        # 详细分析
        doc.add_heading('详细分析', level=1)
        
        for idx, analysis in enumerate(result['analyses'], 1):
            req = analysis['requirement']
            result_item = analysis['analysis']
            
            # 需求标题
            doc.add_heading(f"{idx}. {req['category']}", level=2)
            doc.add_paragraph(f"要求: {req['requirement']}")
            doc.add_paragraph(f"位置: {req['location']}")
            doc.add_paragraph(f"是否强制: {'是' if req['is_mandatory'] else '否'}")
            
            # 分析结果
            status = result_item.get('status', '未知')
            severity = result_item.get('severity', '未知')
            
            doc.add_paragraph(f"状态: {status}")
            doc.add_paragraph(f"严重程度: {severity}")
            
            # 问题
            issues = result_item.get('issues', [])
            if issues:
                doc.add_paragraph("问题:", style='List Bullet')
                for issue in issues:
                    doc.add_paragraph(issue, style='List Bullet 2')
            
            # 建议
            suggestions = result_item.get('suggestions', [])
            if suggestions:
                doc.add_paragraph("修改建议:", style='List Bullet')
                for suggestion in suggestions:
                    doc.add_paragraph(suggestion, style='List Bullet 2')
            
            doc.add_paragraph()  # 空行
        
        # 转为bytes
        from io import BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def save_report(self, result: Dict[str, Any], format: str, output_dir: str = "tasks") -> str:
        """保存报告到文件"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        task_id = result['task_id']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == "json":
            filename = f"{task_id}_{timestamp}.json"
            filepath = Path(output_dir) / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.generate_json(result))
        
        elif format == "markdown":
            filename = f"{task_id}_{timestamp}.md"
            filepath = Path(output_dir) / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.generate_markdown(result))
        
        elif format == "word":
            filename = f"{task_id}_{timestamp}.docx"
            filepath = Path(output_dir) / filename
            with open(filepath, 'wb') as f:
                f.write(self.generate_word(result))
        
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        return str(filepath)
```

- [ ] **Step 2: 提交代码**

```bash
git add core/report_generator.py
git commit -m "feat: add report generator module"
```

---

## Task 7: 创建FastAPI路由

**Files:**
- Create: `api/routes.py`

- [ ] **Step 1: 创建路由文件**

```python
# api/routes.py

import os
import uuid
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from api.models import (
    FileType, TaskStatus, FileUploadResponse, TaskCreateRequest, 
    TaskCreateResponse, TaskStatusResponse, TaskResult, TaskListResponse,
    ErrorResponse
)
from api.database import (
    init_database, create_file, get_file, create_task, get_task,
    update_task_status, list_tasks, delete_task
)
from core.config import load_config
from core.analyzer import Analyzer
from core.report_generator import ReportGenerator


router = APIRouter(prefix="/api/v1")

# 初始化数据库
init_database()

# 上传目录
UPLOAD_DIR = "uploads"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...)
):
    """上传文件"""
    # 生成文件ID和路径
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    filename = f"{file_id}{ext}"
    filepath = Path(UPLOAD_DIR) / filename
    
    # 保存文件
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # 计算文件哈希
    from doc_processor import file_hash
    fhash = file_hash(content)
    
    # 保存到数据库
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
    """创建分析任务"""
    # 验证文件存在
    tender_file = get_file(request.tender_file_id)
    if not tender_file:
        raise HTTPException(status_code=404, detail="招标文件不存在")
    
    bid_file = get_file(request.bid_file_id)
    if not bid_file:
        raise HTTPException(status_code=404, detail="标书文件不存在")
    
    # 验证文件类型
    if tender_file['file_type'] != 'tender':
        raise HTTPException(status_code=400, detail="文件类型错误，应为招标文件")
    
    if bid_file['file_type'] != 'bid':
        raise HTTPException(status_code=400, detail="文件类型错误，应为标书文件")
    
    # 创建任务
    config_json = None
    if request.config:
        import json
        config_json = json.dumps(request.config)
    
    task_id = create_task(
        tender_file_id=request.tender_file_id,
        bid_file_id=request.bid_file_id,
        config_override=config_json
    )
    
    # 启动后台任务
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
    """运行分析任务（后台）"""
    try:
        # 更新状态为处理中
        update_task_status(task_id, "processing", progress=0)
        
        # 加载配置
        config = load_config()
        
        # 创建分析器
        analyzer = Analyzer(config=config)
        
        # 进度回调
        def progress_callback(progress: int):
            update_task_status(task_id, "processing", progress=progress)
        
        # 执行分析
        result = analyzer.analyze(
            task_id=task_id,
            tender_file_path=tender_file_path,
            bid_file_path=bid_file_path,
            progress_callback=progress_callback
        )
        
        # 生成报告
        report_generator = ReportGenerator()
        
        # 保存JSON报告
        json_path = report_generator.save_report(result, "json")
        
        # 更新任务状态
        import json
        update_task_status(
            task_id, 
            "completed", 
            progress=100,
            result_json=json.dumps(result)
        )
        
    except Exception as e:
        # 更新任务状态为失败
        update_task_status(task_id, "failed", error_message=str(e))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """查询任务状态"""
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
    """获取分析结果"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail="任务未完成")
    
    if not task['result_json']:
        raise HTTPException(status_code=500, detail="结果数据不存在")
    
    import json
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
    """下载报告文件"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail="任务未完成")
    
    import json
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
    """查询任务列表"""
    result = list_tasks(
        status=status.value if status else None,
        page=page,
        page_size=page_size
    )
    
    return TaskListResponse(**result)


@router.delete("/tasks/{task_id}")
async def delete_analysis_task(task_id: str):
    """删除任务"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    deleted = delete_task(task_id)
    if deleted:
        return {"success": True, "message": "任务已删除"}
    else:
        raise HTTPException(status_code=500, detail="删除失败")
```

- [ ] **Step 2: 提交代码**

```bash
git add api/routes.py
git commit -m "feat: add API routes"
```

---

## Task 8: 创建FastAPI主入口

**Files:**
- Create: `api/main.py`

- [ ] **Step 1: 创建FastAPI应用**

```python
# api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router


app = FastAPI(
    title="标书对比分析服务",
    description="基于RAG的标书与招标文件对比分析API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "标书对比分析服务",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

- [ ] **Step 2: 提交代码**

```bash
git add api/main.py
git commit -m "feat: add FastAPI main entry"
```

---

## Task 9: 扩展retriever支持文档类型

**Files:**
- Modify: `retriever.py`

- [ ] **Step 1: 扩展index_doc方法**

在`retriever.py`的`LawRetriever`类中，修改`index_doc`方法支持`doc_type`参数：

```python
def index_doc(self, chunks: List[Dict], doc_type: str = "bid"):
    """索引文档内容"""
    points = []
    for chunk in chunks:
        vector = self.embed(chunk["text"])
        points.append(PointStruct(
            id=self._generate_id(chunk),
            vector=vector,
            payload={
                "text": chunk["text"],
                "filename": chunk["filename"],
                "file_hash": chunk["file_hash"],
                "page": chunk["page"],
                "chunk_idx": chunk["chunk_idx"],
                "doc_type": doc_type  # 新增字段
            }
        ))
    
    self.client.upsert(
        collection_name=DOC_COLLECTION,
        points=points
    )
```

- [ ] **Step 2: 添加retrieve方法支持doc_type过滤**

```python
def retrieve(self, query: str, top_k: int = 5, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """检索文档内容"""
    vec = self.embed(query)
    
    filter_ = None
    if doc_type:
        filter_ = Filter(
            must=[
                FieldCondition(
                    key="doc_type",
                    match=MatchValue(value=doc_type)
                )
            ]
        )
    
    points = self._query(DOC_COLLECTION, vec, top_k, filter_)
    
    return [
        {
            "source": "doc",
            "filename": p.payload.get("filename", ""),
            "page": p.payload.get("page", 0),
            "text": p.payload.get("text", ""),
            "score": round(p.score, 4),
            "doc_type": p.payload.get("doc_type", "bid")
        }
        for p in points
    ]
```

- [ ] **Step 3: 提交代码**

```bash
git add retriever.py
git commit -m "feat: extend retriever with doc_type support"
```

---

## Task 10: 更新依赖和Docker配置

**Files:**
- Modify: `requirements.txt`
- Modify: `docker-compose.yml`

- [ ] **Step 1: 更新requirements.txt**

```
anthropic>=0.45.0
openai>=1.30.0
streamlit>=1.42.0
qdrant-client>=1.13.0
sentence-transformers>=3.4.0
python-dotenv>=1.0.0
pdfplumber>=0.11.0
python-docx>=1.1.0
fastapi>=0.115.0
uvicorn>=0.34.0
python-multipart>=0.0.18
pyyaml>=6.0.0
```

- [ ] **Step 2: 更新docker-compose.yml**

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  app:
    build: .
    ports:
      - "8000:8000"
      - "8501:8501"
    environment:
      - QDRANT_HOST=qdrant
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
    volumes:
      - ./uploads:/app/uploads
      - ./tasks:/app/tasks
    depends_on:
      - qdrant

volumes:
  qdrant_data:
```

- [ ] **Step 3: 更新Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建必要目录
RUN mkdir -p uploads tasks

# 启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
```

- [ ] **Step 4: 创建启动脚本**

```bash
#!/bin/bash
# start.sh

# 启动FastAPI
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# 启动Streamlit（可选）
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &

# 等待所有后台进程
wait
```

- [ ] **Step 5: 提交代码**

```bash
git add requirements.txt docker-compose.yml Dockerfile start.sh
git commit -m "feat: update dependencies and Docker configuration"
```

---

## Task 11: 创建测试文件

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_api.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: 创建测试目录init**

```python
# tests/__init__.py
```

- [ ] **Step 2: 创建API测试**

```python
# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_root():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["service"] == "标书对比分析服务"


def test_health_check():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_upload_file():
    """测试文件上传"""
    # 创建测试文件
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"test content")
        temp_path = f.name
    
    with open(temp_path, "rb") as f:
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"file_type": "tender"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == "test.pdf"
    assert data["file_type"] == "tender"


def test_create_task_with_invalid_files():
    """测试使用无效文件ID创建任务"""
    response = client.post(
        "/api/v1/tasks/create",
        json={
            "tender_file_id": "invalid-id",
            "bid_file_id": "invalid-id"
        }
    )
    assert response.status_code == 404


def test_get_nonexistent_task():
    """测试查询不存在的任务"""
    response = client.get("/api/v1/tasks/nonexistent-id")
    assert response.status_code == 404
```

- [ ] **Step 3: 创建分析器测试**

```python
# tests/test_analyzer.py

import pytest
from core.config import load_config, AppConfig


def test_load_config():
    """测试配置加载"""
    config = load_config()
    assert isinstance(config, AppConfig)
    assert len(config.dimensions) == 3
    assert "资质要求" in [d.name for d in config.dimensions]


def test_config_dimensions():
    """测试维度配置"""
    config = load_config()
    
    # 检查权重总和
    total_weight = sum(d.weight for d in config.dimensions)
    assert total_weight == 100


def test_config_prompts():
    """测试提示词配置"""
    config = load_config()
    
    # 检查提示词包含占位符
    assert "{tender_content}" in config.prompts.extract_requirements
    assert "{requirement}" in config.prompts.compare_analysis
    assert "{bid_response}" in config.prompts.compare_analysis
```

- [ ] **Step 4: 提交代码**

```bash
git add tests/
git commit -m "feat: add tests for API and analyzer"
```

---

## Task 12: 集成测试和验证

**Files:**
- None (testing only)

- [ ] **Step 1: 运行单元测试**

```bash
cd /Users/tangjinchun/Documents/biao_shu/zhaobiao
python -m pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 2: 启动服务**

```bash
# 终端1：启动Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# 终端2：启动FastAPI
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 3: 验证API文档**

访问 http://localhost:8000/docs 查看Swagger文档

- [ ] **Step 4: 测试文件上传API**

```bash
# 创建测试文件
echo "测试招标文件内容" > /tmp/test_tender.txt
echo "测试标书内容" > /tmp/test_bid.txt

# 上传招标文件
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@/tmp/test_tender.txt" \
  -F "file_type=tender"

# 上传标书
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@/tmp/test_bid.txt" \
  -F "file_type=bid"
```

- [ ] **Step 5: 提交最终代码**

```bash
git add .
git commit -m "feat: complete bid analysis service implementation"
```

---

## 实现完成

完成以上任务后，你将拥有一个完整的标书对比分析后端服务，具备：

1. ✅ 文件上传功能
2. ✅ 异步任务处理
3. ✅ 配置化的对比维度和提示词
4. ✅ 基于RAG的需求提取和对比分析
5. ✅ 多格式报告生成（JSON/Markdown/Word）
6. ✅ RESTful API接口
7. ✅ 完整的API文档

**下一步：**
- 开发前端页面调用这些API
- 添加用户认证和权限管理
- 优化性能和错误处理
