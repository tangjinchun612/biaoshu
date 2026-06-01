# 标书对比分析服务设计文档

## 1. 项目概述

### 1.1 背景
当前项目是一个基于RAG的招标文件合规审查工具，主要用于将标书与《招标投标法》进行比对。现需要扩展功能，支持标书与招标文件的对比分析，并对外提供API接口。

### 1.2 目标
- 支持上传标书和招标文件
- 自动对比分析标书是否符合招标要求
- 生成结构化分析报告（JSON/Markdown/Word）
- 对外提供RESTful API接口
- 支持异步任务处理

### 1.3 核心需求
1. **文件上传**：支持PDF/Word格式的标书和招标文件
2. **对比分析**：根据配置的对比维度，自动分析标书问题
3. **报告生成**：支持JSON、Markdown、Word三种格式
4. **异步处理**：上传后返回任务ID，后台处理，前端轮询获取结果
5. **配置灵活**：对比维度、提示词、评分规则均可配置

---

## 2. 系统架构

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    标书对比分析服务                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │  FastAPI     │    │  任务调度    │    │    分析引擎      │ │
│  │  (API层)     │───▶│  (异步处理)  │───▶│                 │ │
│  └─────────────┘    └─────────────┘    │  ┌───────────┐  │ │
│         │                  │            │  │ 文档解析   │  │ │
│         ▼                  ▼            │  └─────┬─────┘  │ │
│  ┌─────────────┐    ┌─────────────┐    │        ▼        │ │
│  │  文件存储    │    │  SQLite     │    │  ┌───────────┐  │ │
│  │  (uploads/)  │    │  (任务状态)  │    │  │ 向量检索   │  │ │
│  └─────────────┘    └─────────────┘    │  └─────┬─────┘  │ │
│                                        │        ▼        │ │
│                                        │  ┌───────────┐  │ │
│                                        │  │ LLM分析    │  │ │
│                                        │  │(Claude/Qwen)│ │ │
│                                        │  └─────┬─────┘  │ │
│                                        │        ▼        │ │
│                                        │  ┌───────────┐  │ │
│                                        │  │ 报告生成   │  │ │
│                                        │  └───────────┘  │ │
│                                        └─────────────────┘ │
│                                                             │
│  ┌─────────────┐    ┌─────────────────────────────────┐   │
│  │  Qdrant     │    │           配置层                  │   │
│  │  (向量数据库) │    │  config.yaml (对比维度/评分/模板) │   │
│  └─────────────┘    └─────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 职责 | 技术选型 |
|------|------|----------|
| FastAPI | API网关，接收请求，返回结果 | FastAPI + Uvicorn |
| 任务调度 | 异步任务管理，状态跟踪 | asyncio + SQLite |
| 分析引擎 | 文档解析、向量检索、LLM分析 | 现有retriever + doc_processor |
| 文件存储 | 上传文件的临时存储 | 本地文件系统 (uploads/) |
| 配置管理 | 读取和验证配置文件 | PyYAML |

---

## 3. 分析流程

### 3.1 核心流程（方案B：需求提取 + 逐项核查）

```
招标文件 + 标书
      │
      ▼
  文档解析 (doc_processor)
      │
      ▼
  向量索引 (写入Qdrant)
      │
      ▼
  需求提取 (LLM + 可配置提示词)
      │
      ▼
  逐项对比 (向量检索 + LLM分析)
      │
      ▼
  报告生成 (JSON/Markdown/Word)
```

### 3.2 详细流程

1. **文件上传阶段**
   - 用户上传招标文件和标书
   - 系统解析文档，提取文本内容
   - 将文本分块并索引到Qdrant

2. **需求提取阶段**
   - 读取config.yaml中的提示词配置
   - 调用LLM分析招标文件，提取结构化需求清单
   - 需求包含：类别、具体内容、位置、是否强制

3. **逐项对比阶段**
   - 遍历需求清单
   - 针对每个需求，从标书中检索相关片段
   - 调用LLM对比分析，输出评估结果

4. **报告生成阶段**
   - 汇总所有评估结果
   - 根据配置生成JSON/Markdown/Word格式报告
   - 存储到tasks目录

---

## 4. 配置文件设计

### 4.1 配置文件结构 (config.yaml)

```yaml
# 对比维度配置
dimensions:
  - name: "资质要求"
    description: "企业资质、人员证书、业绩要求等"
    weight: 30  # 权重（用于评分）
    
  - name: "技术规范"
    description: "技术参数、方案要求、工期等"
    weight: 40
    
  - name: "商务条款"
    description: "报价、付款方式、违约责任等"
    weight: 30

# 提示词配置
prompts:
  # 招标文件需求提取提示词
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
    
  # 标书对比分析提示词
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
  pass_threshold: 80  # 及格分数线

# 输出配置
output:
  formats: ["json", "markdown", "word"]
  default_format: "json"
  include_original_text: true  # 是否在报告中包含原文引用
```

---

## 5. API接口设计

### 5.1 接口列表

#### 5.1.1 上传文件
```
POST /api/v1/files/upload
Content-Type: multipart/form-data

参数：
- file: 文件内容
- file_type: 文件类型 (tender/bid)

返回：
{
  "file_id": "uuid",
  "filename": "招标文件.pdf",
  "file_type": "tender",
  "uploaded_at": "2026-05-30T10:00:00"
}
```

#### 5.1.2 创建分析任务
```
POST /api/v1/tasks/create
Content-Type: application/json

参数：
{
  "tender_file_id": "uuid",
  "bid_file_id": "uuid",
  "config": {}  // 可选，覆盖默认配置
}

返回：
{
  "task_id": "uuid",
  "status": "pending",
  "created_at": "2026-05-30T10:00:00"
}
```

#### 5.1.3 查询任务状态
```
GET /api/v1/tasks/{task_id}

返回：
{
  "task_id": "uuid",
  "status": "processing",
  "progress": 60,
  "created_at": "2026-05-30T10:00:00",
  "updated_at": "2026-05-30T10:05:00"
}
```

#### 5.1.4 获取分析结果
```
GET /api/v1/tasks/{task_id}/result
参数：format (json/markdown/word)

返回：分析结果（根据format返回不同格式）
```

#### 5.1.5 下载报告文件
```
GET /api/v1/tasks/{task_id}/download
参数：format (markdown/word)

返回：文件流
```

#### 5.1.6 查询任务列表
```
GET /api/v1/tasks
参数：status, page, page_size

返回：
{
  "tasks": [...],
  "total": 100,
  "page": 1,
  "page_size": 10
}
```

#### 5.1.7 删除任务
```
DELETE /api/v1/tasks/{task_id}

返回：
{
  "success": true
}
```

### 5.2 状态流转

```
pending → processing → completed
                   ↘ failed
```

---

## 6. 数据库设计

### 6.1 任务表 (tasks)

```sql
CREATE TABLE tasks (
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
);
```

### 6.2 文件表 (files)

```sql
CREATE TABLE files (
    file_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. 项目结构

```
zhaobiao/
├── app.py                 # 现有Streamlit应用（保留）
├── retriever.py           # 现有检索模块（扩展）
├── doc_processor.py       # 现有文档处理（保留）
├── indexer.py             # 现有索引模块（保留）
├── data.py                # 现有数据模块（保留）
│
├── api/                   # 新增：API服务
│   ├── __init__.py
│   ├── main.py           # FastAPI入口
│   ├── routes.py         # API路由定义
│   ├── models.py         # 数据模型（Pydantic）
│   └── database.py       # SQLite任务管理
│
├── core/                  # 新增：核心业务逻辑
│   ├── __init__.py
│   ├── analyzer.py       # 分析引擎（调用retriever + LLM）
│   ├── llm_client.py     # LLM客户端（从app.py提取）
│   ├── report_generator.py # 报告生成（JSON/MD/Word）
│   └── config.py         # 配置管理
│
├── config.yaml           # 新增：配置文件
├── uploads/              # 新增：上传文件存储
├── tasks/                # 新增：任务结果存储
│
├── requirements.txt      # 更新依赖
└── docker-compose.yml    # 更新部署配置
```

---

## 8. 现有代码复用

| 现有模块 | 复用方式 | 扩展内容 |
|---------|---------|---------|
| `doc_processor.py` | 直接复用 | 无需修改 |
| `retriever.py` | 扩展复用 | 新增招标文件collection |
| `indexer.py` | 复用逻辑 | 适配新的文档类型 |
| `data.py` | 直接复用 | 法律条文数据加载 |
| `app.py` 中的LLM调用 | 提取复用 | 提取为独立模块 |

---

## 9. 技术栈总结

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| API框架 | FastAPI | 现代异步框架，自动生成文档 |
| 任务存储 | SQLite | 轻量级，无需额外服务 |
| 向量数据库 | Qdrant | 复用现有 |
| Embedding | BAAI/bge-small-zh-v1.5 | 复用现有 |
| LLM | Claude/Qwen | 复用现有 |
| 文档解析 | pdfplumber + python-docx | 复用现有 |
| 报告生成 | python-docx (Word) | 新增 |
| 配置管理 | PyYAML | 新增 |

---

## 10. 部署方案

### 10.1 Docker Compose配置

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
      - "8000:8000"  # FastAPI
      - "8501:8501"  # Streamlit
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

### 10.2 启动命令

```bash
# 启动服务
docker compose up --build

# 或本地开发
# 终端1：启动Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# 终端2：启动FastAPI
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 终端3：启动Streamlit（可选，用于调试）
streamlit run app.py
```

---

## 11. 后续扩展

1. **前端页面**：开发Vue/React前端，调用API接口
2. **批量处理**：支持多个标书同时分析
3. **历史记录**：查询历史分析任务
4. **模板管理**：管理不同类型的招标项目模板
5. **权限控制**：添加用户认证和权限管理

---

## 12. 免责声明

本工具仅供参考，不构成正式法律意见。实际法律事务请咨询专业律师。
