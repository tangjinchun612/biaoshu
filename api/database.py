import os
import uuid
import pymysql
import pymysql.cursors
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "mysql"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "zhaobiao"),
        password=os.getenv("MYSQL_PASSWORD", "zhaobiao123"),
        database=os.getenv("MYSQL_DATABASE", "zhaobiao"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
    )


@contextmanager
def get_cursor():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
    finally:
        conn.close()


def init_database():
    with get_cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id VARCHAR(36) PRIMARY KEY,
                filename VARCHAR(500) NOT NULL,
                file_type VARCHAR(20) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_hash VARCHAR(64) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id VARCHAR(36) PRIMARY KEY,
                tender_file_id VARCHAR(36) NOT NULL,
                bid_file_id VARCHAR(36) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                progress INT DEFAULT 0,
                result_json LONGTEXT,
                error_message TEXT,
                config_override TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)


def create_file(filename: str, file_type: str, file_path: str, file_hash: str) -> str:
    file_id = str(uuid.uuid4())
    with get_cursor() as cursor:
        cursor.execute(
            "INSERT INTO files (file_id, filename, file_type, file_path, file_hash) VALUES (%s, %s, %s, %s, %s)",
            (file_id, filename, file_type, file_path, file_hash)
        )
    return file_id


def update_file_path(file_id: str, file_path: str):
    with get_cursor() as cursor:
        cursor.execute(
            "UPDATE files SET file_path = %s WHERE file_id = %s",
            (file_path, file_id)
        )


def get_file(file_id: str) -> Optional[Dict[str, Any]]:
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM files WHERE file_id = %s", (file_id,))
        return cursor.fetchone()


def create_task(tender_file_id: str, bid_file_id: str, config_override: Optional[str] = None) -> str:
    task_id = str(uuid.uuid4())
    with get_cursor() as cursor:
        cursor.execute(
            "INSERT INTO tasks (task_id, tender_file_id, bid_file_id, config_override) VALUES (%s, %s, %s, %s)",
            (task_id, tender_file_id, bid_file_id, config_override)
        )
    return task_id


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM tasks WHERE task_id = %s", (task_id,))
        return cursor.fetchone()


def update_task_status(task_id: str, status: str, progress: int = 0,
                       result_json: Optional[str] = None, error_message: Optional[str] = None):
    with get_cursor() as cursor:
        cursor.execute(
            """UPDATE tasks
               SET status = %s, progress = %s, result_json = %s, error_message = %s, updated_at = %s
               WHERE task_id = %s""",
            (status, progress, result_json, error_message, datetime.now(), task_id)
        )


def list_tasks(status: Optional[str] = None, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    with get_cursor() as cursor:
        if status:
            cursor.execute(
                "SELECT * FROM tasks WHERE status = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (status, page_size, offset)
            )
            tasks = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE status = %s", (status,))
            total = cursor.fetchone()["cnt"]
        else:
            cursor.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (page_size, offset)
            )
            tasks = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) AS cnt FROM tasks")
            total = cursor.fetchone()["cnt"]

    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size
    }


def delete_task(task_id: str) -> bool:
    with get_cursor() as cursor:
        cursor.execute("DELETE FROM tasks WHERE task_id = %s", (task_id,))
        return cursor.rowcount > 0
