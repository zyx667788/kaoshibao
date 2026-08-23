"""PostgreSQL 存储层 - 将爬取的题目保存到数据库"""

from __future__ import annotations

import os
import json
import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger("kaoshibao.db")

PG_HOST = os.environ.get('PG_HOST', 'localhost')
PG_PORT = int(os.environ.get('PG_PORT', '5432'))
PG_DATABASE = os.environ.get('PG_DATABASE', 'kaoshibao')
PG_USER = os.environ.get('PG_USER', 'postgres')
PG_PASSWORD = os.environ.get('PG_PASSWORD', '')

_pool: SimpleConnectionPool | None = None


def _get_pool() -> SimpleConnectionPool:
    """获取连接池（懒初始化）"""
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(
            minconn=1, maxconn=5,
            host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE,
            user=PG_USER, password=PG_PASSWORD
        )
    return _pool


def get_connection():
    """从连接池获取连接"""
    return _get_pool().getconn()


def put_connection(conn):
    """归还连接到连接池"""
    _get_pool().putconn(conn)


def init_db() -> bool:
    """初始化数据库表结构，返回是否成功"""
    try:
        pool = _get_pool()
        conn = pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS questions (
                            id SERIAL PRIMARY KEY,
                            paper_id VARCHAR(64) NOT NULL,
                            sequence INTEGER NOT NULL,
                            question_type VARCHAR(32),
                            question TEXT NOT NULL,
                            options JSONB,
                            answer TEXT,
                            analysis TEXT,
                            mode VARCHAR(16) DEFAULT 'ocr',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(paper_id, sequence)
                        )
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS papers (
                            paper_id VARCHAR(64) PRIMARY KEY,
                            title VARCHAR(256),
                            total_questions INTEGER DEFAULT 0,
                            total_with_answer INTEGER DEFAULT 0,
                            last_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_questions_paper_id ON questions(paper_id)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_questions_paper_seq ON questions(paper_id, sequence)")
        finally:
            pool.putconn(conn)
        logger.info("数据库表结构初始化完成")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def save_questions_to_db(paper_id: str, questions: list[dict[str, Any]], mode: str = 'ocr') -> int:
    """保存题目列表到数据库（批量插入），返回新增数量"""
    if not questions:
        return 0
    try:
        pool = _get_pool()
        conn = pool.getconn()
        added = 0
        try:
            with conn:
                with conn.cursor() as cur:
                    rows = [(
                        paper_id, q.get('序号', 0), q.get('题目类型', ''),
                        q.get('题目', ''), json.dumps(q.get('选项', []), ensure_ascii=False),
                        q.get('正确答案', ''), q.get('解析', ''), mode
                    ) for q in questions]
                    execute_values(cur, """
                        INSERT INTO questions (paper_id, sequence, question_type, question, options, answer, analysis, mode)
                        VALUES %s
                        ON CONFLICT (paper_id, sequence) DO UPDATE SET
                          question_type=EXCLUDED.question_type,
                          question=EXCLUDED.question,
                          options=EXCLUDED.options,
                          answer=EXCLUDED.answer,
                          analysis=EXCLUDED.analysis
                    """, rows)
                    added = len(rows)
                    total_with_ans = sum(1 for q in questions if q.get('正确答案'))
                    cur.execute("""
                        INSERT INTO papers (paper_id, total_questions, total_with_answer, last_scraped_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (paper_id) DO UPDATE SET
                          total_questions=EXCLUDED.total_questions,
                          total_with_answer=EXCLUDED.total_with_answer,
                          last_scraped_at=CURRENT_TIMESTAMP
                    """, (paper_id, len(questions), total_with_ans))
        finally:
            pool.putconn(conn)
        logger.info(f"保存 {added} 题到数据库(paper_id={paper_id})")
    except Exception as e:
        logger.error(f"保存到数据库失败: {e}")
    return added


def get_papers_from_db() -> list[dict[str, Any]]:
    """从数据库获取所有题库列表"""
    try:
        pool = _get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM papers ORDER BY last_scraped_at DESC")
                return [dict(row) for row in cur.fetchall()]
        finally:
            pool.putconn(conn)
    except Exception as e:
        logger.error(f"查询题库列表失败: {e}")
        return []


def get_questions_from_db(paper_id: str) -> list[dict[str, Any]]:
    """从数据库获取指定题库的所有题目"""
    try:
        pool = _get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM questions WHERE paper_id=%s ORDER BY sequence", (paper_id,))
                rows = cur.fetchall()
                result = []
                for row in rows:
                    item = dict(row)
                    if isinstance(item.get('options'), str):
                        item['options'] = json.loads(item['options'])
                    result.append(item)
                return result
        finally:
            pool.putconn(conn)
    except Exception as e:
        logger.error(f"查询题目失败: {e}")
        return []


def is_db_configured() -> bool:
    """检查数据库是否已配置（密码非空）"""
    return bool(PG_PASSWORD)
