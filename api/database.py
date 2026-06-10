import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


DATABASE_PATH = "tasks/tasks.db"


def get_connection() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
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


def update_file_path(file_id: str, file_path: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE files SET file_path = ? WHERE file_id = ?",
        (file_path, file_id)
    )
    conn.commit()
    conn.close()


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def create_task(tender_file_id: str, bid_file_id: str, config_override: Optional[str] = None) -> str:
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
    conn = get_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * page_size
    
    if status:
        cursor.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, page_size, offset)
        )
        tasks = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (status,))
        total = cursor.fetchone()[0]
    else:
        cursor.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        )
        tasks = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total = cursor.fetchone()[0]
    conn.close()
    
    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size
    }


def delete_task(task_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return deleted
