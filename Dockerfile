FROM python:3.12-slim

WORKDIR /app

# ========== 1. pip 全局配置阿里云镜像（一劳永逸） ==========
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set global.trusted-host mirrors.aliyun.com

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources    

# ========== 2. 系统依赖 ==========
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ========== 3. 先复制依赖文件（利用 Docker 层缓存） ==========
COPY requirements.txt .

# ========== 4. 安装 PyTorch CPU 版（阿里云镜像，分钟级） ==========
RUN pip install --no-cache-dir \
    torch==2.6.0+cpu \
    torchvision==0.21.0+cpu \
    -f https://mirrors.aliyun.com/pytorch-wheels/cpu \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/

# ========== 5. 安装其余依赖（过滤 torch，防止被覆盖 + 走阿里云镜像） ==========
RUN grep -iEvc '^(torch|torchvision|torchaudio)==' requirements.txt > /dev/null \
    && grep -iEv '^(torch|torchvision|torchaudio)[=><!]' requirements.txt \
       > /tmp/req_no_torch.txt \
    && pip install --no-cache-dir -r /tmp/req_no_torch.txt \
    || pip install --no-cache-dir -r requirements.txt

# ========== 6. 预下载 embedding 模型 ==========
ARG HF_ENDPOINT=https://hf-mirror.com
ENV HF_ENDPOINT=${HF_ENDPOINT}
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# ========== 7. 复制应用代码和数据 ==========
COPY data.py indexer.py retriever.py app.py doc_processor.py config.yaml ./
COPY data/ ./data/
COPY api/ ./api/
COPY core/ ./core/
COPY start.sh ./
RUN chmod +x start.sh

# ========== 8. Streamlit 配置 ==========
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501
EXPOSE 8000



CMD ["sh", "-c", "python indexer.py && bash start.sh"]