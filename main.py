import os
import logging

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from bot.database import (
    initialize_database,
    initialize_reminders_table,
)

from bot.todo import (
    add_task_command,
    tasks_command,
    done_command,
    delete_command,
)

from bot.reminders import (
    remind_command,
    reminders_command,
    cancel_reminder_command,
)


# ==================================================
# Configuration
# ==================================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# ==================================================
# Logging
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ==================================================
# General Commands
# ==================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "Welcome to Self Help Bot!\n\n"
        "I can help you manage tasks and reminders "
        "and make everyday activities easier.\n\n"
        "Use /help to see all available commands."
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🤖 Self Help Bot\n\n"

        "📌 General Commands\n"
        "/start - Start the bot\n"
        "/help - Show available commands\n\n"

        "📋 Task Commands\n"
        "/addtask <task> - Add a task\n"
        "/tasks - Show your tasks\n"
        "/done <id> - Complete a task\n"
        "/delete <id> - Delete a task\n\n"

        "⏰ Reminder Commands\n"
        "/remind <duration> <message> - Set a reminder\n"
        "/reminders - Show pending reminders\n"
        "/cancelreminder <id> - Cancel a reminder\n\n"

        "Examples:\n"
        "/addtask Complete DSA assignment\n"
        "/remind 10m Study DSA\n"
        "/remind 2h Submit project"
    )


# ==================================================
# Error Handler
# ==================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "Exception while processing an update:",
        exc_info=context.error,
    )


# ==================================================
# Main Application
# ==================================================

def main():

    # ------------------------------------------------
    # Check Telegram Bot Token
    # ------------------------------------------------

    if not TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is missing from the .env file."
        )

    # ------------------------------------------------
    # Initialize databases
    # ------------------------------------------------

    initialize_database()
    initialize_reminders_table()

    # ------------------------------------------------
    # Create Telegram Application
    # ------------------------------------------------

    app = Application.builder().token(TOKEN).build()

    # ------------------------------------------------
    # General Commands
    # ------------------------------------------------

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    # ------------------------------------------------
    # Todo Commands
    # ------------------------------------------------

    app.add_handler(
        CommandHandler("addtask", add_task_command)
    )

    app.add_handler(
        CommandHandler("tasks", tasks_command)
    )

    app.add_handler(
        CommandHandler("done", done_command)
    )

    app.add_handler(
        CommandHandler("delete", delete_command)
    )

    # ------------------------------------------------
    # Reminder Commands
    # ------------------------------------------------

    app.add_handler(
        CommandHandler("remind", remind_command)
    )

    app.add_handler(
        CommandHandler("reminders", reminders_command)
    )

    app.add_handler(
        CommandHandler(
            "cancelreminder",
            cancel_reminder_command
        )
    )

    # ------------------------------------------------
    # Error Handler
    # ------------------------------------------------

    app.add_error_handler(error_handler)

    # ------------------------------------------------
    # Start Bot
    # ------------------------------------------------

    print("Self Help Bot is running...")

    app.run_polling()


# ==================================================
# Entry Point
# ==================================================

if __name__ == "__main__":
    main()