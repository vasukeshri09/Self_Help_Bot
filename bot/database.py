import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

DATABASE_DIR = "data"
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE = os.path.join(DATABASE_DIR, "self_help_bot.db")
LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                due_at TEXT,
                created_at TEXT
            )
        """)
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(tasks)").fetchall()
        }
        if "due_at" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN due_at TEXT")
        if "created_at" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT")

        # Existing tasks receive the migration time, so they are not immediately
        # considered 90 days old when their original creation dates are unknown.
        migration_time = datetime.now(LOCAL_TZ).isoformat()
        cursor.execute(
            "UPDATE tasks SET created_at = ? WHERE created_at IS NULL OR created_at = ''",
            (migration_time,),
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")


def add_task(user_id, task, due_at=None):
    created_at = datetime.now(LOCAL_TZ).isoformat()
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (user_id, task, due_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, task, due_at, created_at),
        )
        return cursor.lastrowid


def get_tasks(user_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, task, completed, due_at
            FROM tasks
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,),
        )
        return cursor.fetchall()


def complete_task(user_id, task_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE tasks SET completed = 1 WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        updated = cursor.rowcount
        if updated:
            cursor.execute(
                "DELETE FROM reminders WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            )
        return updated


def delete_task(user_id, task_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM reminders WHERE task_id = ? AND user_id = ?",
            (task_id, user_id),
        )
        cursor.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        return cursor.rowcount


def cleanup_old_tasks(cutoff_iso, now_iso):
    """Delete old tasks except those with future deadlines.

    Returns (deleted_task_count, deleted_reminder_ids).
    """
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, user_id
            FROM tasks
            WHERE created_at < ?
              AND (due_at IS NULL OR due_at <= ?)
            """,
            (cutoff_iso, now_iso),
        )
        eligible_tasks = cursor.fetchall()
        if not eligible_tasks:
            return 0, []

        reminder_ids = []
        for task_id, user_id in eligible_tasks:
            cursor.execute(
                "SELECT id FROM reminders WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            )
            reminder_ids.extend(row[0] for row in cursor.fetchall())
            cursor.execute(
                "DELETE FROM reminders WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            )
            cursor.execute(
                "DELETE FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id),
            )
        return len(eligible_tasks), reminder_ids


def initialize_reminders_table():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                reminder_text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                task_id INTEGER
            )
        """)
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(reminders)").fetchall()
        }
        if "task_id" not in columns:
            cursor.execute("ALTER TABLE reminders ADD COLUMN task_id INTEGER")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reminders_task_id ON reminders(task_id)"
        )


def get_task_reminder_id(user_id, task_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id FROM reminders WHERE user_id = ? AND task_id = ?",
            (user_id, task_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def add_reminder(user_id, chat_id, reminder_text, remind_at, task_id=None):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO reminders (user_id, chat_id, reminder_text, remind_at, task_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, chat_id, reminder_text, remind_at, task_id),
        )
        return cursor.lastrowid


def get_pending_reminders():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, user_id, chat_id, reminder_text, remind_at, task_id
            FROM reminders
            ORDER BY remind_at
            """
        )
        return cursor.fetchall()


def get_user_reminders(user_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, reminder_text, remind_at
            FROM reminders
            WHERE user_id = ? AND task_id IS NULL
            ORDER BY remind_at
            """,
            (user_id,),
        )
        return cursor.fetchall()


def delete_reminder(reminder_id, user_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM reminders
            WHERE id = ? AND user_id = ? AND task_id IS NULL
            """,
            (reminder_id, user_id),
        )
        return cursor.rowcount


def delete_reminder_record(reminder_id, user_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
        )
        return cursor.rowcount
