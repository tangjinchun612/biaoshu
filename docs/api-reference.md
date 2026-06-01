# 标书对比分析服务 API 接口文档

## 基础信息

| 项目 | 说明 |
|------|------|
| 服务名称 | 标书对比分析服务 |
| 版本 | 1.0.0 |
| 基础URL | `http://localhost:8000` |
| API前缀 | `/api/v1` |
| 数据格式 | JSON |
| 认证方式 | 暂无（后续可扩展） |

## 交互流程

```
1. 上传招标文件 → 获取 tender_file_id
2. 上传标书 → 获取 bid_file_id
3. 创建分析任务 → 获取 task_id
4. 轮询任务状态 → 等待 status = completed
5. 获取分析结果 / 下载报告
```

---

## 接口列表

### 1. 健康检查

检查服务是否正常运行。

**请求**
```
GET /health
```

**响应**
```json
{
  "status": "healthy"
}
```

---

### 2. 上传文件

上传招标文件或标书文件。

**请求**
```
POST /api/v1/files/upload
Content-Type: multipart/form-data
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 文件内容（支持 PDF/DOC/DOCX） |
| file_type | String | 是 | 文件类型：`tender`（招标文件）或 `bid`（标书） |

**响应**
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "招标文件.pdf",
  "file_type": "tender",
  "uploaded_at": "2026-05-30T10:00:00"
}
```

**错误码**

| 状态码 | 说明 |
|--------|------|
| 422 | 参数验证失败（文件缺失或类型错误） |

**示例**
```bash
# 上传招标文件
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@tender.pdf" \
  -F "file_type=tender"

# 上传标书
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@bid.docx" \
  -F "file_type=bid"
```

---

### 3. 创建分析任务

创建标书对比分析任务，系统将异步处理。

**请求**
```
POST /api/v1/tasks/create
Content-Type: application/json
```

**请求体**
```json
{
  "tender_file_id": "550e8400-e29b-41d4-a716-446655440000",
  "bid_file_id": "660e8400-e29b-41d4-a716-446655440001",
  "config": null
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tender_file_id | String | 是 | 招标文件ID（上传接口返回） |
| bid_file_id | String | 是 | 标书ID（上传接口返回） |
| config | Object | 否 | 配置覆盖（可选，覆盖默认配置） |

**响应**
```json
{
  "task_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "pending",
  "created_at": "2026-05-30T10:05:00"
}
```

**错误码**

| 状态码 | 说明 |
|--------|------|
| 400 | 文件类型错误 |
| 404 | 文件不存在 |

**示例**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "tender_file_id": "550e8400-e29b-41d4-a716-446655440000",
    "bid_file_id": "660e8400-e29b-41d4-a716-446655440001"
  }'
```

---

### 4. 查询任务状态

查询分析任务的当前状态和进度。

**请求**
```
GET /api/v1/tasks/{task_id}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | String | 任务ID |

**响应**
```json
{
  "task_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "processing",
  "progress": 60,
  "created_at": "2026-05-30T10:05:00",
  "updated_at": "2026-05-30T10:08:00"
}
```

**状态说明**

| 状态 | 说明 |
|------|------|
| pending | 等待处理 |
| processing | 处理中（progress 0-100） |
| completed | 处理完成 |
| failed | 处理失败 |

**错误码**

| 状态码 | 说明 |
|--------|------|
| 404 | 任务不存在 |

**示例**
```bash
curl http://localhost:8000/api/v1/tasks/770e8400-e29b-41d4-a716-446655440002
```

---

### 5. 获取分析结果

获取已完成任务的分析结果。

**请求**
```
GET /api/v1/tasks/{task_id}/result?format={format}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | String | 是 | 任务ID（路径参数） |
| format | String | 否 | 返回格式：`json`（默认）、`markdown`、`word` |

**响应（JSON格式）**
```json
{
  "task_id": "770e8400-e29b-41d4-a716-446655440002",
  "requirements_count": 15,
  "issues_count": 3,
  "score": 85.5,
  "analyses": [
    {
      "requirement": {
        "category": "资质要求",
        "requirement": "投标人须具备建筑工程施工总承包一级资质",
        "location": "第二章 投标人须知 第3.1条",
        "is_mandatory": true
      },
      "analysis": {
        "status": "符合",
        "severity": "轻微",
        "issues": [],
        "suggestions": ["建议在投标文件中附上资质证书复印件"]
      },
      "bid_response_text": "我公司具备建筑工程施工总承包一级资质..."
    }
  ]
}
```

**响应（Markdown格式）**
```json
{
  "markdown": "# 标书对比分析报告\n\n**生成时间:** 2026-05-30 10:10:00\n..."
}
```

**响应（Word格式）**
```json
{
  "word_base64": "UEsDBBQABgAIAAAAIQ..."
}
```

**错误码**

| 状态码 | 说明 |
|--------|------|
| 400 | 任务未完成 |
| 404 | 任务不存在 |
| 500 | 结果数据不存在 |

**示例**
```bash
# 获取JSON格式结果
curl http://localhost:8000/api/v1/tasks/770e8400-e29b-41d4-a716-446655440002/result?format=json

# 获取Markdown格式结果
curl http://localhost:8000/api/v1/tasks/770e8400-e29b-41d4-a716-446655440002/result?format=markdown
```

---

### 6. 下载报告文件

下载分析报告文件。

**请求**
```
GET /api/v1/tasks/{task_id}/download?format={format}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | String | 是 | 任务ID（路径参数） |
| format | String | 否 | 文件格式：`markdown`（默认）、`word` |

**响应**

返回文件流，Content-Type 为 `application/octet-stream`。

**错误码**

| 状态码 | 说明 |
|--------|------|
| 400 | 任务未完成 |
| 404 | 任务不存在 |

**示例**
```bash
# 下载Markdown报告
curl -O -J http://localhost:8000/api/v1/tasks/770e8400-e29b-41d4-a716-446655440002/download?format=markdown

# 下载Word报告
curl -O -J http://localhost:8000/api/v1/tasks/770e8400-e29b-41d4-a716-446655440002/download?format=word
```

---

### 7. 查询任务列表

分页查询任务列表。

**请求**
```
GET /api/v1/tasks?page={page}&page_size={page_size}&status={status}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | Integer | 否 | 页码（默认1） |
| page_size | Integer | 否 | 每页数量（默认10） |
| status | String | 否 | 状态过滤：`pending`、`processing`、`completed`、`failed` |

**响应**
```json
{
  "tasks": [
    {
      "task_id": "770e8400-e29b-41d4-a716-446655440002",
      "status": "completed",
      "progress": 100,
      "created_at": "2026-05-30T10:05:00",
      "updated_at": "2026-05-30T10:10:00"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 10
}
```

**示例**
```bash
# 查询所有任务
curl http://localhost:8000/api/v1/tasks

# 查询已完成的任务
curl http://localhost:8000/api/v1/tasks?status=completed

# 分页查询
curl http://localhost:8000/api/v1/tasks?page=2&page_size=5
```

---

### 8. 删除任务

删除指定任务及其结果。

**请求**
```
DELETE /api/v1/tasks/{task_id}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | String | 任务ID |

**响应**
```json
{
  "success": true,
  "message": "任务已删除"
}
```

**错误码**

| 状态码 | 说明 |
|--------|------|
| 404 | 任务不存在 |
| 500 | 删除失败 |

**示例**
```bash
curl -X DELETE http://localhost:8000/api/v1/tasks/770e8400-e29b-41d4-a716-446655440002
```

---

## 数据模型

### FileType（文件类型）

| 值 | 说明 |
|------|------|
| tender | 招标文件 |
| bid | 标书 |

### TaskStatus（任务状态）

| 值 | 说明 |
|------|------|
| pending | 等待处理 |
| processing | 处理中 |
| completed | 已完成 |
| failed | 失败 |

### RequirementItem（需求项）

| 字段 | 类型 | 说明 |
|------|------|------|
| category | String | 所属类别（资质要求/技术规范/商务条款） |
| requirement | String | 具体要求内容 |
| location | String | 在文档中的位置 |
| is_mandatory | Boolean | 是否为强制性要求 |

### AnalysisResult（分析结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| status | String | 状态：符合/部分符合/不符合 |
| severity | String | 严重程度：严重/一般/轻微 |
| issues | Array[String] | 问题列表 |
| suggestions | Array[String] | 修改建议列表 |

---

## 配置说明

### 配置文件结构

配置文件 `config.yaml` 支持自定义以下内容：

#### 对比维度配置
```yaml
dimensions:
  - name: "资质要求"
    description: "企业资质、人员证书、业绩要求等"
    weight: 30
```

#### 提示词配置
```yaml
prompts:
  extract_requirements: |
    # 招标文件需求提取提示词
    # 变量：{tender_content}
    
  compare_analysis: |
    # 标书对比分析提示词
    # 变量：{requirement}, {bid_response}
```

#### 评分规则配置
```yaml
scoring:
  severity_weights:
    "严重": 10
    "一般": 5
    "轻微": 2
  pass_threshold: 80
```

#### 输出配置
```yaml
output:
  formats: ["json", "markdown", "word"]
  default_format: "json"
  include_original_text: true
```

### 运行时覆盖配置

创建任务时可通过 `config` 参数覆盖默认配置：

```json
{
  "tender_file_id": "...",
  "bid_file_id": "...",
  "config": {
    "dimensions": [
      {"name": "技术参数", "description": "...", "weight": 50}
    ]
  }
}
```

---

## 错误处理

### 错误响应格式
```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 422 | 参数验证失败 |
| 500 | 服务器内部错误 |

---

## 使用流程示例

### 完整流程

```bash
# 1. 上传招标文件
TENDER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@tender.pdf" \
  -F "file_type=tender")
TENDER_FILE_ID=$(echo $TENDER_RESPONSE | jq -r '.file_id')
echo "招标文件ID: $TENDER_FILE_ID"

# 2. 上传标书
BID_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@bid.pdf" \
  -F "file_type=bid")
BID_FILE_ID=$(echo $BID_RESPONSE | jq -r '.file_id')
echo "标书ID: $BID_FILE_ID"

# 3. 创建分析任务
TASK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/tasks/create \
  -H "Content-Type: application/json" \
  -d "{\"tender_file_id\": \"$TENDER_FILE_ID\", \"bid_file_id\": \"$BID_FILE_ID\"}")
TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
echo "任务ID: $TASK_ID"

# 4. 轮询任务状态
while true; do
  STATUS_RESPONSE=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID)
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
  PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')
  echo "状态: $STATUS, 进度: $PROGRESS%"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done

# 5. 获取结果
if [ "$STATUS" = "completed" ]; then
  # 获取JSON结果
  curl http://localhost:8000/api/v1/tasks/$TASK_ID/result?format=json | jq .
  
  # 下载Markdown报告
  curl -O -J http://localhost:8000/api/v1/tasks/$TASK_ID/download?format=markdown
  
  # 下载Word报告
  curl -O -J http://localhost:8000/api/v1/tasks/$TASK_ID/download?format=word
fi
```

---

## 注意事项

1. **文件格式**：支持 PDF、DOC、DOCX 格式
2. **文件大小**：建议单个文件不超过 50MB
3. **处理时间**：根据文档页数和复杂度，处理时间约 1-10 分钟
4. **并发限制**：当前版本为单任务处理，多个任务将排队执行
5. **结果存储**：任务结果默认保存在 `tasks/` 目录

---

## Swagger文档

启动服务后，访问以下地址查看交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 更新日志

### v1.0.0 (2026-05-30)
- 初始版本发布
- 支持文件上传
- 支持异步任务处理
- 支持JSON/Markdown/Word三种报告格式
