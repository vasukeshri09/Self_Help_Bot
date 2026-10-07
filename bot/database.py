import sqlite3

DATABASE = "self_help_bot.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )
    """)

    connection.commit()
    connection.close()


def add_task(user_id, task):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO tasks (user_id, task) VALUES (?, ?)",
        (user_id, task)
    )

    connection.commit()
    task_id = cursor.lastrowid
    connection.close()

    return task_id


def get_tasks(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, task, completed
        FROM tasks
        WHERE user_id = ?
        ORDER BY id
        """,
        (user_id,)
    )

    tasks = cursor.fetchall()
    connection.close()

    return tasks


def complete_task(user_id, task_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET completed = 1
        WHERE id = ? AND user_id = ?
        """,
        (task_id, user_id)
    )

    updated = cursor.rowcount

    connection.commit()
    connection.close()

    return updated


def delete_task(user_id, task_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM tasks
        WHERE id = ? AND user_id = ?
        """,
        (task_id, user_id)
    )

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted

def initialize_reminders_table():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            reminder_text TEXT NOT NULL,
            remind_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def add_reminder(user_id, chat_id, reminder_text, remind_at):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO reminders
        (user_id, chat_id, reminder_text, remind_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, chat_id, reminder_text, remind_at)
    )

    connection.commit()
    reminder_id = cursor.lastrowid

    connection.close()

    return reminder_id


def get_pending_reminders():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, user_id, chat_id, reminder_text, remind_at
        FROM reminders
        ORDER BY remind_at
        """
    )

    reminders = cursor.fetchall()
    connection.close()

    return reminders


def get_user_reminders(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, reminder_text, remind_at
        FROM reminders
        WHERE user_id = ?
        ORDER BY remind_at
        """,
        (user_id,)
    )

    reminders = cursor.fetchall()
    connection.close()

    return reminders


def delete_reminder(reminder_id, user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM reminders
        WHERE id = ? AND user_id = ?
        """,
        (reminder_id, user_id)
    )

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted