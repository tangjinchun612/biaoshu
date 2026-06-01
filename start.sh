#!/bin/bash

# 启动FastAPI
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# 启动Streamlit
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &

# 等待所有后台进程
wait
