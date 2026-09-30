"""
database.py
------------
Lightweight SQLite persistence layer for the AI-BI-Copilot project.

Tables
------
users     : id, username, email, password_hash, salt, security_answer_hash, created_at
reports   : id, user_id, filename, original_name, uploaded_at, rows, cols
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "app_data.db")


def init_db():
    """Create tables if they do not already exist. Safe to call on every app start."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                security_question TEXT,
                security_answer_hash TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                rows INTEGER,
                cols INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def create_user(username, email, password_hash, salt, security_question, security_answer_hash):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, salt,
                                security_question, security_answer_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, salt, security_question,
             security_answer_hash, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def get_user_by_username(username):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_by_email(email):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_password(user_id, new_hash, new_salt):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (new_hash, new_salt, user_id),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def save_report_record(user_id, filename, original_name, rows, cols):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reports (user_id, filename, original_name, uploaded_at, rows, cols)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, filename, original_name, datetime.utcnow().isoformat(), rows, cols),
        )
        conn.commit()
        return cur.lastrowid


def get_reports_for_user(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM reports WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,)
        )
        return [dict(row) for row in cur.fetchall()]
