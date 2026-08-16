import sqlite3
import json

DB_NAME = "client_tasks.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            is_done INTEGER DEFAULT 0,
            subtasks TEXT DEFAULT '[]',
            energy TEXT DEFAULT 'medium'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            ai_credits INTEGER DEFAULT 5,
            is_pro INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO profile (id, ai_credits, is_pro) VALUES (1, 5, 0)")
    conn.commit()
    conn.close()

def get_tasks(energy_filter=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if energy_filter and energy_filter != "all":
        cursor.execute("SELECT id, title, is_done, subtasks, energy FROM tasks WHERE energy = ? ORDER BY id DESC", (energy_filter,))
    else:
        cursor.execute("SELECT id, title, is_done, subtasks, energy FROM tasks ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "is_done": bool(r[2]), "subtasks": json.loads(r[3]), "energy": r[4]} for r in rows]

def add_task(title, energy="medium"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, subtasks, energy) VALUES (?, ?, ?)", (title, json.dumps([]), energy))
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

def get_profile():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT ai_credits, is_pro FROM profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return {"credits": row[0], "is_pro": bool(row[1])}

def deduct_credit():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE profile SET ai_credits = ai_credits - 1 WHERE id = 1 AND ai_credits > 0")
    conn.commit()
    conn.close()

def set_pro():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE profile SET is_pro = 1 WHERE id = 1")
    conn.commit()
    conn.close()