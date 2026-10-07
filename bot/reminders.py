import re
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import (
    add_reminder,
    get_user_reminders,
    delete_reminder,
)


DURATION_PATTERN = re.compile(
    r"^(\d+)(s|m|h|d)$",
    re.IGNORECASE,
)


def parse_duration(duration):
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


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data

    reminder_id = job_data["reminder_id"]
    chat_id = job_data["chat_id"]
    reminder_text = job_data["reminder_text"]

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "⏰ Reminder!\n\n"
            f"{reminder_text}"
        ),
    )

    # Remove reminder after sending it
    delete_reminder(
        reminder_id,
        job_data["user_id"],
    )


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
    reminder_text = " ".join(context.args[1:])

    duration = parse_duration(duration_text)

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

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    remind_at = datetime.now(timezone.utc) + duration

    reminder_id = add_reminder(
        user_id,
        chat_id,
        reminder_text,
        remind_at.isoformat(),
    )

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


async def reminders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id

    reminders = get_user_reminders(user_id)

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

    await update.message.reply_text(message)


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
        reminder_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Reminder ID must be a number."
        )
        return

    user_id = update.effective_user.id

    deleted = delete_reminder(
        reminder_id,
        user_id,
    )

    if not deleted:
        await update.message.reply_text(
            "❌ Reminder not found."
        )
        return

    # Remove scheduled job
    current_jobs = context.job_queue.get_jobs_by_name(
        f"reminder_{reminder_id}"
    )

    for job in current_jobs:
        job.schedule_removal()

    await update.message.reply_text(
        f"🗑️ Reminder {reminder_id} cancelled."
    )