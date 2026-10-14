import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.database import (
    add_reminder,
    get_pending_reminders,
    get_user_reminders,
    delete_reminder,
    delete_reminder_record,
)

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Kolkata")

ASK_MESSAGE, ASK_DATE, ASK_TIME = range(3)


def schedule_reminder(application, reminder):
    """Schedule one saved reminder using its database record."""
    reminder_id, user_id, chat_id, reminder_text, remind_at = reminder[:5]

    remind_datetime = datetime.fromisoformat(remind_at)
    if remind_datetime.tzinfo is None:
        remind_datetime = remind_datetime.replace(tzinfo=LOCAL_TZ)

    delay = max(
        1,
        (remind_datetime - datetime.now(LOCAL_TZ)).total_seconds(),
    )

    if application.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable. Install python-telegram-bot with the job-queue extra."
        )

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


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send a due reminder and remove its database record after successful delivery."""
    data = context.job.data

    try:
        await context.bot.send_message(
            chat_id=data["chat_id"],
            text=f"⏰ Reminder!\n\n{data['reminder_text']}",
        )
    except Exception:
        logger.exception("Failed to send reminder %s.", data["reminder_id"])
        return

    delete_reminder_record(data["reminder_id"], data["user_id"])
    logger.info("Reminder %s sent and removed.", data["reminder_id"])


async def remind_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop("new_reminder", None)
    await update.message.reply_text(
        "What would you like to be reminded about?"
    )
    return ASK_MESSAGE


async def receive_reminder_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.message.text.strip()

    if not message:
        await update.message.reply_text("Please enter a reminder message.")
        return ASK_MESSAGE

    context.user_data["new_reminder"] = {"message": message}

    await update.message.reply_text(
        "Enter the date in DD/MM/YY format, or type 'today' for a same-day reminder.\n"
        "Example: 20/10/26"
    )
    return ASK_DATE


async def receive_reminder_date(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    date_text = update.message.text.strip().lower()

    try:
        if date_text == "today":
            selected_date = datetime.now(LOCAL_TZ).date()
        else:
            selected_date = datetime.strptime(date_text, "%d/%m/%y").date()

        if selected_date < datetime.now(LOCAL_TZ).date():
            raise ValueError

    except ValueError:
        await update.message.reply_text(
            "Invalid date or date is in the past.\n"
            "Use DD/MM/YY, for example 20/10/26, or type 'today'."
        )
        return ASK_DATE

    context.user_data["new_reminder"]["date"] = selected_date.isoformat()

    await update.message.reply_text(
        "Enter the time in 24-hour HH:MM format.\n"
        "Example: 18:30 for 6:30 PM"
    )
    return ASK_TIME


async def receive_reminder_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        selected_time = datetime.strptime(
            update.message.text.strip(), "%H:%M"
        ).time()

        details = context.user_data["new_reminder"]
        remind_at = datetime.fromisoformat(
            details["date"]
        ).replace(
            hour=selected_time.hour,
            minute=selected_time.minute,
            second=0,
            microsecond=0,
            tzinfo=LOCAL_TZ,
        )

        if remind_at <= datetime.now(LOCAL_TZ):
            await update.message.reply_text(
                "That date and time has already passed. Enter a future time."
            )
            return ASK_TIME

    except ValueError:
        await update.message.reply_text(
            "Invalid time. Please use HH:MM, for example 18:30."
        )
        return ASK_TIME

    user = update.effective_user
    chat = update.effective_chat
    message = details["message"]
    remind_at_text = remind_at.isoformat()

    reminder_id = add_reminder(
        user.id,
        chat.id,
        message,
        remind_at_text,
    )

    try:
        schedule_reminder(
            context.application,
            (
                reminder_id,
                user.id,
                chat.id,
                message,
                remind_at_text,
            ),
        )
    except Exception:
        # Keep the database record so it can be restored on the next startup.
        logger.exception("Reminder %s was saved but could not be scheduled.", reminder_id)
        await update.message.reply_text(
            "⚠️ The reminder was saved, but could not be scheduled right now. "
            "It may be restored when the bot restarts."
        )
        context.user_data.pop("new_reminder", None)
        return ConversationHandler.END

    context.user_data.pop("new_reminder", None)

    await update.message.reply_text(
        "✅ Reminder scheduled!\n\n"
        f"ID: {reminder_id}\n"
        f"Message: {message}\n"
        f"Date: {remind_at.strftime('%d/%m/%y')}\n"
        f"Time: {remind_at.strftime('%H:%M')}"
    )
    return ConversationHandler.END


async def cancel_reminder_setup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop("new_reminder", None)
    await update.message.reply_text("Reminder setup cancelled.")
    return ConversationHandler.END


def get_remind_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("remind", remind_start)],
        states={
            ASK_MESSAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_reminder_message,
                )
            ],
            ASK_DATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_reminder_date,
                )
            ],
            ASK_TIME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_reminder_time,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_reminder_setup)],
        allow_reentry=True,
    )


async def reminders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    reminders = get_user_reminders(update.effective_user.id)

    if not reminders:
        await update.message.reply_text(
            "⏰ You have no standalone reminders pending."
        )
        return

    message = "⏰ Your Reminders\n\n"

    for reminder_id, reminder_text, remind_at in reminders:
        try:
            reminder_datetime = datetime.fromisoformat(remind_at)
            if reminder_datetime.tzinfo is None:
                reminder_datetime = reminder_datetime.replace(tzinfo=LOCAL_TZ)
            else:
                reminder_datetime = reminder_datetime.astimezone(LOCAL_TZ)
            when = reminder_datetime.strftime("%d/%m/%y %H:%M")
        except ValueError:
            when = remind_at

        message += f"{reminder_id}. {reminder_text}\n   {when}\n\n"

    await update.message.reply_text(message)


async def cancel_reminder_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "Usage: /cancelreminder <id>"
        )
        return

    try:
        reminder_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Reminder ID must be a number.")
        return

    user_id = update.effective_user.id
    deleted = delete_reminder(reminder_id, user_id)

    if not deleted:
        await update.message.reply_text(
            "Reminder not found, or it is a task deadline reminder."
        )
        return

    if context.job_queue is not None:
        for job in context.job_queue.get_jobs_by_name(
            f"reminder_{reminder_id}"
        ):
            job.schedule_removal()

    await update.message.reply_text(
        f"🗑️ Reminder {reminder_id} cancelled."
    )


def schedule_pending_reminders(application):
    """Restore saved reminders after bot startup."""
    for reminder in get_pending_reminders():
        try:
            schedule_reminder(application, reminder)
            logger.info("Restored reminder %s.", reminder[0])
        except Exception:
            logger.exception("Could not restore reminder %s.", reminder[0])
