from telegram import Update
from telegram.ext import ContextTypes

from bot.database import (
    add_task,
    get_tasks,
    complete_task,
    delete_task,
)


async def add_task_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n/addtask <task>\n\n"
            "Example:\n/addtask Complete DSA assignment"
        )
        return

    task = " ".join(context.args)
    user_id = update.effective_user.id

    task_id = add_task(user_id, task)

    await update.message.reply_text(
        f"✅ Task added!\n\n"
        f"ID: {task_id}\n"
        f"Task: {task}"
    )


async def tasks_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id
    tasks = get_tasks(user_id)

    if not tasks:
        await update.message.reply_text(
            "📋 You don't have any tasks yet."
        )
        return

    message = "📋 Your Tasks\n\n"

    for task_id, task, completed in tasks:
        status = "✅" if completed else "⏳"
        message += f"{task_id}. {status} {task}\n"

    await update.message.reply_text(message)


async def done_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n/done <task_id>\n\n"
            "Example:\n/done 1"
        )
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Task ID must be a number."
        )
        return

    user_id = update.effective_user.id

    updated = complete_task(user_id, task_id)

    if updated:
        await update.message.reply_text(
            f"✅ Task {task_id} completed!"
        )
    else:
        await update.message.reply_text(
            "❌ Task not found."
        )


async def delete_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "Usage:\n/delete <task_id>\n\n"
            "Example:\n/delete 1"
        )
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Task ID must be a number."
        )
        return

    user_id = update.effective_user.id

    deleted = delete_task(user_id, task_id)

    if deleted:
        await update.message.reply_text(
            f"🗑️ Task {task_id} deleted."
        )
    else:
        await update.message.reply_text(
            "❌ Task not found."
        )