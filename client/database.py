import sqlite3
import json
import hashlib
import time

DB_NAME = "client_tasks.db"
SALT = "smarttask_secure_salt_2026"

def hash_password(password: str) -> str:
    return hashlib.sha256((password + SALT).encode('utf-8')).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Пользователи
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            ai_credits INTEGER DEFAULT 5,
            is_pro INTEGER DEFAULT 0,
            focus_seconds INTEGER DEFAULT 0
        )
    """)
    
    # 2. Задачи
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            is_done INTEGER DEFAULT 0,
            subtasks TEXT DEFAULT '[]',
            energy TEXT DEFAULT 'medium',
            created_at REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # 3. Заметки и конспекты с картинками
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT,
            created_at REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

# --- AUTH ---
def register_user(username, password):
    if len(username.strip()) < 3: return False, "Username too short"
    if len(password.strip()) < 4: return False, "Password too short"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username.strip().lower(), hash_password(password)))
        uid = cursor.lastrowid
        conn.commit()
        conn.close()
        return True, uid
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username already exists!"

def login_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, ai_credits, is_pro, focus_seconds FROM users WHERE username = ? AND password_hash = ?", (username.strip().lower(), hash_password(password)))
    row = cursor.fetchone()
    conn.close()
    if row: return {"id": row[0], "username": row[1], "credits": row[2], "is_pro": bool(row[3]), "focus_seconds": row[4]}
    return None

def get_user_profile(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT ai_credits, is_pro, focus_seconds FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return {"credits": row[0], "is_pro": bool(row[1]), "focus_seconds": row[2]} if row else {"credits": 0, "is_pro": False, "focus_seconds": 0}

def add_focus_time(user_id, seconds):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET focus_seconds = focus_seconds + ? WHERE id = ?", (seconds, user_id))
    conn.commit()
    conn.close()

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

# --- TASKS ---
def get_tasks(user_id, filter_type="all"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if filter_type == "completed":
        cursor.execute("SELECT id, title, is_done, subtasks, energy FROM tasks WHERE user_id = ? AND is_done = 1 ORDER BY id DESC", (user_id,))
    elif filter_type in ["high", "medium", "zombie"]:
        cursor.execute("SELECT id, title, is_done, subtasks, energy FROM tasks WHERE user_id = ? AND energy = ? ORDER BY id DESC", (user_id, filter_type))
    else:
        cursor.execute("SELECT id, title, is_done, subtasks, energy FROM tasks WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "is_done": bool(r[2]), "subtasks": json.loads(r[3]), "energy": r[4]} for r in rows]

def add_task(user_id, title, energy="medium"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, title, subtasks, energy, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, title, json.dumps([]), energy, time.time()))
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

# --- NOTES WITH IMAGES ---
def add_note(user_id, title, content, image_path=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (user_id, title, content, image_path, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, title, content, image_path, time.time()))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id

def get_notes(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, content, image_path FROM notes WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "content": r[2], "image_path": r[3]} for r in rows]

def delete_note(note_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

def update_note(note_id, title, content, image_path=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE notes SET title = ?, content = ?, image_path = ? WHERE id = ?", (title, content, image_path, note_id))
    conn.commit()
    conn.close()