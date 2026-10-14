import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.database import cleanup_old_tasks

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
RETENTION_DAYS = 90


def clean_old_tasks(application=None):
    """Delete tasks older than 90 days unless they have a future deadline."""
    now = datetime.now(LOCAL_TZ)
    cutoff = now - timedelta(days=RETENTION_DAYS)
    deleted_count, reminder_ids = cleanup_old_tasks(
        cutoff.isoformat(),
        now.isoformat(),
    )

    if application is not None and application.job_queue is not None:
        for reminder_id in reminder_ids:
            for job in application.job_queue.get_jobs_by_name(f"reminder_{reminder_id}"):
                job.schedule_removal()

    if deleted_count:
        logger.info(
            "Automatic cleanup removed %s task(s) older than %s days and %s associated reminder(s).",
            deleted_count, RETENTION_DAYS, len(reminder_ids),
        )
    else:
        logger.info("Automatic task cleanup completed; no eligible old tasks found.")
    return deleted_count


async def scheduled_cleanup(context):
    try:
        clean_old_tasks(context.application)
    except Exception:
        logger.exception("Automatic task cleanup failed.")


def register_task_cleaner(application):
    """Clean at startup and then daily at 03:00 Asia/Kolkata."""
    clean_old_tasks(application)
    if application.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable. Install python-telegram-bot with the job-queue extra."
        )
    application.job_queue.run_daily(
        scheduled_cleanup,
        time=datetime.strptime("03:00", "%H:%M").time().replace(tzinfo=LOCAL_TZ),
        name="daily_task_cleanup",
    )
    logger.info("Automatic task cleanup registered for 03:00 Asia/Kolkata daily.")
