import sqlite3
import json
import hashlib
import os

DB_NAME = "client_tasks.db"
SALT = "smarttask_secure_salt_2026"  # Соль для защиты паролей

def hash_password(password: str) -> str:
    """Безопасное хеширование пароля с солью (SHA-256)"""
    return hashlib.sha256((password + SALT).encode('utf-8')).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            ai_credits INTEGER DEFAULT 5,
            is_pro INTEGER DEFAULT 0
        )
    """)
    
    # 2. Таблица задач с привязкой к user_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            is_done INTEGER DEFAULT 0,
            subtasks TEXT DEFAULT '[]',
            energy TEXT DEFAULT 'medium',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

# --- АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ ---

def register_user(username, password):
    """Регистрация нового пользователя"""
    if len(username.strip()) < 3:
        return False, "Username must be at least 3 characters"
    if len(password.strip()) < 8:
        return False, "Password must be at least 8 characters"
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, ai_credits, is_pro) VALUES (?, ?, 5, 0)",
            (username.strip().lower(), hash_password(password))
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return True, user_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username already exists! Choose another."

def login_user(username, password):
    """Проверка логина и пароля"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, ai_credits, is_pro FROM users WHERE username = ? AND password_hash = ?",
        (username.strip().lower(), hash_password(password))
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "credits": row[2], "is_pro": bool(row[3])}
    return None

def get_user_profile(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT ai_credits, is_pro FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return {"credits": row[0], "is_pro": bool(row[1])} if row else {"credits": 0, "is_pro": False}

def deduct_credit(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET ai_credits = ai_credits - 1 WHERE id = ? AND ai_credits > 0", (user_id,))
    conn.commit()
    conn.close()

def set_pro(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_pro = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- ОПЕРАЦИИ С ЗАДАЧАМИ ---

def get_tasks(user_id, energy_filter=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if energy_filter and energy_filter != "all":
        cursor.execute("SELECT id, title, is_done, subtasks, energy FROM tasks WHERE user_id = ? AND energy = ? ORDER BY id DESC", (user_id, energy_filter))
    else:
        cursor.execute("SELECT id, title, is_done, subtasks, energy FROM tasks WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "is_done": bool(r[2]), "subtasks": json.loads(r[3]), "energy": r[4]} for r in rows]

def add_task(user_id, title, energy="medium"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, title, subtasks, energy) VALUES (?, ?, ?, ?)", (user_id, title, json.dumps([]), energy))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def toggle_task(task_id, is_done):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET is_done = ? WHERE id = ?", (1 if is_done else 0, task_id))
    conn.commit()
    conn.close()

def save_subtasks(task_id, subtasks):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET subtasks = ? WHERE id = ?", (json.dumps(subtasks), task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()