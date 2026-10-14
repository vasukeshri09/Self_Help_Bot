from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import (
    add_task,
    get_tasks,
    complete_task,
    delete_task,
    add_reminder,
    get_task_reminder_id,
)
from bot.reminders import schedule_reminder

LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def cancel_task_reminder(context, user_id, task_id):
    """Cancel the scheduled job for a task's deadline reminder."""
    reminder_id = get_task_reminder_id(user_id, task_id)

    if reminder_id is not None and context.job_queue is not None:
        for job in context.job_queue.get_jobs_by_name(
            f"reminder_{reminder_id}"
        ):
            job.schedule_removal()


async def add_task_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/addtask <task> | DD/MM/YY HH:MM\n\n"
            "Examples:\n"
            "/addtask Complete DSA assignment | 20/10/26 18:30\n"
            "/addtask Study DSA | 18:30\n\n"
            "For a deadline, use DD/MM/YY HH:MM or just HH:MM "
            "(which uses today's date in India).\n"
            "You can also add a task without a deadline."
        )
        return

    raw_text = " ".join(context.args)
    task = raw_text
    due_at = None

    if "|" in raw_text:
        task, deadline_text = raw_text.rsplit("|", 1)
        task = task.strip()
        deadline_text = deadline_text.strip()

        try:
            now = datetime.now(LOCAL_TZ)

            if " " in deadline_text:
                # Full date and time: DD/MM/YY HH:MM
                due_at = datetime.strptime(
                    deadline_text, "%d/%m/%y %H:%M"
                ).replace(tzinfo=LOCAL_TZ)
            else:
                # Time only: use today's date in India.
                selected_time = datetime.strptime(
                    deadline_text, "%H:%M"
                ).time()

                due_at = now.replace(
                    hour=selected_time.hour,
                    minute=selected_time.minute,
                    second=0,
                    microsecond=0,
                )

            if due_at <= now:
                await update.message.reply_text(
                    "❌ The deadline must be in the future. "
                    "For a time-only deadline, enter a future time today."
                )
                return

        except ValueError:
            await update.message.reply_text(
                "❌ Invalid deadline format.\n\n"
                "Use DD/MM/YY HH:MM, e.g. 20/10/26 18:30,\n"
                "or just HH:MM, e.g. 18:30."
            )
            return

    if not task:
        await update.message.reply_text(
            "Please provide a task description."
        )
        return

    user = update.effective_user
    chat = update.effective_chat

    task_id = add_task(
        user.id,
        task,
        due_at.isoformat() if due_at else None,
    )

    reply = (
        "✅ Task added!\n\n"
        f"ID: {task_id}\n"
        f"Task: {task}"
    )

    if due_at:
        reminder_text = f"Task deadline: {task}"
        remind_at = due_at.isoformat()

        reminder_id = add_reminder(
            user.id,
            chat.id,
            reminder_text,
            remind_at,
            task_id=task_id,
        )

        schedule_reminder(
            context.application,
            (
                reminder_id,
                user.id,
                chat.id,
                reminder_text,
                remind_at,
                task_id,
            ),
        )

        reply += (
            f"\n📅 Deadline: {due_at.strftime('%d/%m/%y %H:%M')}"
            "\n🔔 A reminder has been scheduled."
        )

    await update.message.reply_text(reply)


async def tasks_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    tasks = get_tasks(update.effective_user.id)

    if not tasks:
        await update.message.reply_text(
            "📋 You don't have any tasks yet."
        )
        return

    message = "📋 Your Tasks\n\n"

    for task_id, task, completed, due_at in tasks:
        status = "✅" if completed else "⏳"
        message += f"{task_id}. {status} {task}"

        if due_at:
            try:
                deadline = datetime.fromisoformat(due_at)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=LOCAL_TZ)
                else:
                    deadline = deadline.astimezone(LOCAL_TZ)

                message += (
                    f"\n   📅 {deadline.strftime('%d/%m/%y %H:%M')}"
                )
            except ValueError:
                message += f"\n   📅 {due_at}"

        message += "\n\n"

    await update.message.reply_text(message)


async def done_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text("Usage: /done <task_id>")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Task ID must be a number."
        )
        return

    user_id = update.effective_user.id

    # Read the reminder ID before complete_task deletes its database row.
    reminder_id = get_task_reminder_id(user_id, task_id)
    updated = complete_task(user_id, task_id)

    if not updated:
        await update.message.reply_text("❌ Task not found.")
        return

    if reminder_id is not None and context.job_queue is not None:
        for job in context.job_queue.get_jobs_by_name(
            f"reminder_{reminder_id}"
        ):
            job.schedule_removal()

    await update.message.reply_text(
        f"✅ Task {task_id} completed. Its deadline reminder was cancelled."
    )


async def delete_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text("Usage: /delete <task_id>")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Task ID must be a number."
        )
        return

    user_id = update.effective_user.id

    # Read the reminder ID before delete_task removes its database row.
    reminder_id = get_task_reminder_id(user_id, task_id)
    deleted = delete_task(user_id, task_id)

    if not deleted:
        await update.message.reply_text("❌ Task not found.")
        return

    if reminder_id is not None and context.job_queue is not None:
        for job in context.job_queue.get_jobs_by_name(
            f"reminder_{reminder_id}"
        ):
            job.schedule_removal()

    await update.message.reply_text(
        f"🗑️ Task {task_id} deleted. Its deadline reminder was cancelled."
    )
