import os
import logging

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.database import initialize_database, initialize_reminders_table
from bot.todo import add_task_command, tasks_command, done_command, delete_command
from bot.reminders import (
    get_remind_conversation_handler,
    reminders_command,
    cancel_reminder_command,
    schedule_pending_reminders,
)
from bot.cleaner import register_task_cleaner

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "Welcome to Self Help Bot!\n\n"
        "Manage tasks with deadlines and schedule reminders "
        "for important events.\n\n"
        "Use /help to see all available commands."
    )



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 SELF HELP BOT — HELP\n\n"

        "📋 TASK MANAGEMENT\n"
        "/addtask <task> - Add a task without a deadline\n"
        "/tasks - View all your tasks and deadlines\n"
        "/done <id> - Mark a task as completed\n"
        "/delete <id> - Delete a task manually\n\n"

        "📅 ADD TASKS WITH DEADLINES\n"
        "Format: /addtask <task> | DD/MM/YY HH:MM\n"
        "Example: /addtask Submit assignment | 20/10/26 18:30\n\n"
        "For today's deadline, you can enter just a time:\n"
        "/addtask Study DSA | 18:30\n"
        "Times use India Standard Time (IST).\n\n"

        "⏰ REMINDERS\n"
        "/remind - Create a reminder step by step\n"
        "/reminders - View pending standalone reminders\n"
        "/cancelreminder <id> - Cancel a standalone reminder\n"
        "/cancel - Cancel reminder setup\n\n"
        "When prompted by /remind, enter:\n"
        "1. Reminder message\n"
        "2. Date in DD/MM/YY format, or 'today'\n"
        "3. Time in 24-hour HH:MM format\n\n"

        "ℹ️ GENERAL\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"

        "⚠️ AUTOMATIC TASK CLEANUP\n"
        "Tasks older than 90 days are automatically deleted. "
        "This includes completed tasks and incomplete tasks without "
        "a future deadline.\n\n"
        "✅ Tasks with future deadlines are kept, even if they are "
        "older than 90 days.\n\n"
        "🗑️ Deletion is permanent and cannot be undone by the bot. "
        "Save or copy important tasks before the 90-day limit.\n\n"
        "Task cleanup also deletes reminders associated with removed "
        "tasks. Standalone reminders are not affected."
    )

    await update.message.reply_text(help_text)



async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while processing an update:", exc_info=context.error)


def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing from the .env file.")

    initialize_database()
    initialize_reminders_table()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addtask", add_task_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(get_remind_conversation_handler())
    app.add_handler(CommandHandler("reminders", reminders_command))
    app.add_handler(CommandHandler("cancelreminder", cancel_reminder_command))
    app.add_error_handler(error_handler)

    # Clean before restoring reminders, so deleted task reminders aren't restored.
    register_task_cleaner(app)
    schedule_pending_reminders(app)

    logger.info("Pending reminders restored.")
    logger.info("Self Help Bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
