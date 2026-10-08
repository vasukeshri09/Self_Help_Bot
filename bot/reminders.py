import re
import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import (
    add_reminder,
    get_pending_reminders,
    get_user_reminders,
    delete_reminder,
)


# ==================================================
# Logging
# ==================================================

logger = logging.getLogger(__name__)


# ==================================================
# Duration Parser
# ==================================================

DURATION_PATTERN = re.compile(
    r"^(\d+)(s|m|h|d)$",
    re.IGNORECASE,
)


def parse_duration(duration):
    """
    Convert a duration string such as:
    10s, 10m, 2h, 1d
    into a timedelta object.
    """

    match = DURATION_PATTERN.match(duration)

    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2).lower()

    if unit == "s":
        return timedelta(seconds=value)

    if unit == "m":
        return timedelta(minutes=value)

    if unit == "h":
        return timedelta(hours=value)

    if unit == "d":
        return timedelta(days=value)

    return None


# ==================================================
# Send Reminder
# ==================================================

async def send_reminder(
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Send a reminder message and remove it from
    the database after successful delivery.
    """

    job_data = context.job.data

    reminder_id = job_data["reminder_id"]
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]
    reminder_text = job_data["reminder_text"]

    try:

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⏰ Reminder!\n\n"
                f"{reminder_text}"
            ),
        )

        # Delete reminder after successful delivery
        delete_reminder(
            reminder_id,
            user_id,
        )

        logger.info(
            f"Reminder {reminder_id} sent successfully."
        )

    except Exception:
        logger.exception(
            f"Failed to send reminder {reminder_id}."
        )


# ==================================================
# /remind Command
# ==================================================

async def remind_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if len(context.args) < 2:

        await update.message.reply_text(
            "Usage:\n"
            "/remind <duration> <message>\n\n"

            "Examples:\n"
            "/remind 10m Complete DSA assignment\n"
            "/remind 2h Submit project\n"
            "/remind 1d Call home"
        )

        return

    duration_text = context.args[0]

    reminder_text = " ".join(
        context.args[1:]
    )

    duration = parse_duration(
        duration_text
    )

    if duration is None:

        await update.message.reply_text(
            "❌ Invalid duration.\n\n"

            "Use formats like:\n"
            "10s = 10 seconds\n"
            "10m = 10 minutes\n"
            "2h = 2 hours\n"
            "1d = 1 day"
        )

        return

    if duration.total_seconds() <= 0:

        await update.message.reply_text(
            "❌ Duration must be greater than zero."
        )

        return

    # User and chat information
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Calculate reminder time in UTC
    remind_at = (
        datetime.now(timezone.utc)
        + duration
    )

    # Save reminder in SQLite
    reminder_id = add_reminder(
        user_id,
        chat_id,
        reminder_text,
        remind_at.isoformat(),
    )

    # Schedule Telegram JobQueue task
    context.job_queue.run_once(
        send_reminder,
        when=duration.total_seconds(),
        data={
            "reminder_id": reminder_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "reminder_text": reminder_text,
        },
        name=f"reminder_{reminder_id}",
    )

    await update.message.reply_text(
        "⏰ Reminder set!\n\n"

        f"ID: {reminder_id}\n"
        f"Message: {reminder_text}\n"
        f"After: {duration_text}"
    )

    logger.info(
        f"Reminder {reminder_id} created "
        f"for user {user_id}."
    )


# ==================================================
# /reminders Command
# ==================================================

async def reminders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    reminders = get_user_reminders(
        user_id
    )

    if not reminders:

        await update.message.reply_text(
            "⏰ You don't have any pending reminders."
        )

        return

    message = "⏰ Your Reminders\n\n"

    for reminder_id, text, remind_at in reminders:

        message += (
            f"{reminder_id}. {text}\n"
            f"   🕐 {remind_at}\n\n"
        )

    await update.message.reply_text(
        message
    )


# ==================================================
# /cancelreminder Command
# ==================================================

async def cancel_reminder_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            "Usage:\n"
            "/cancelreminder <id>\n\n"

            "Example:\n"
            "/cancelreminder 1"
        )

        return

    try:

        reminder_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Reminder ID must be a number."
        )

        return

    user_id = update.effective_user.id

    # Delete from database
    deleted = delete_reminder(
        reminder_id,
        user_id,
    )

    if not deleted:

        await update.message.reply_text(
            "❌ Reminder not found."
        )

        return

    # Remove scheduled JobQueue job
    current_jobs = (
        context.job_queue.get_jobs_by_name(
            f"reminder_{reminder_id}"
        )
    )

    for job in current_jobs:

        job.schedule_removal()

    await update.message.reply_text(
        f"🗑️ Reminder {reminder_id} cancelled."
    )

    logger.info(
        f"Reminder {reminder_id} cancelled "
        f"by user {user_id}."
    )


# ==================================================
# Restore Pending Reminders
# ==================================================

def schedule_pending_reminders(
    application
):
    """
    Restore reminders from SQLite when the bot starts.

    This is important for deployment because the Telegram
    JobQueue exists only in memory. If the bot/server restarts,
    scheduled jobs disappear.

    The reminders themselves remain in SQLite, so this function
    recreates the missing JobQueue jobs.
    """

    pending_reminders = (
        get_pending_reminders()
    )

    if not pending_reminders:

        logger.info(
            "No pending reminders to restore."
        )

        return

    restored_count = 0

    for reminder in pending_reminders:

        try:

            # get_pending_reminders() returns:
            #
            # id,
            # user_id,
            # chat_id,
            # reminder_text,
            # remind_at

            reminder_id = reminder[0]
            user_id = reminder[1]
            chat_id = reminder[2]
            reminder_text = reminder[3]
            remind_at = reminder[4]

            # Convert ISO timestamp back to datetime
            remind_datetime = (
                datetime.fromisoformat(
                    remind_at
                )
            )

            # Ensure UTC timezone
            if remind_datetime.tzinfo is None:

                remind_datetime = (
                    remind_datetime.replace(
                        tzinfo=timezone.utc
                    )
                )

            # Calculate remaining time
            delay = (
                remind_datetime
                - datetime.now(timezone.utc)
            ).total_seconds()

            # If the bot was offline when the reminder
            # should have fired, send it shortly after startup.
            if delay <= 0:

                delay = 1

                logger.info(
                    f"Reminder {reminder_id} "
                    "was missed while bot was offline. "
                    "Scheduling immediately."
                )

            # Recreate JobQueue job
            application.job_queue.run_once(
                send_reminder,
                when=delay,
                data={
                    "reminder_id": reminder_id,
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "reminder_text": reminder_text,
                },
                name=f"reminder_{reminder_id}",
            )

            restored_count += 1

            logger.info(
                f"Restored reminder {reminder_id} "
                f"(delay: {delay:.2f} seconds)"
            )

        except Exception:

            logger.exception(
                f"Failed to restore reminder: "
                f"{reminder}"
            )

    logger.info(
        f"Restored {restored_count} "
        f"pending reminder(s)."
    )