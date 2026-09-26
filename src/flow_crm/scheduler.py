import asyncio
import logging
from datetime import datetime, timezone
from typing import NoReturn

from .backup import create_backup, rotate_old_backups
from .config import get_settings

logger = logging.getLogger("flow_crm.scheduler")

_scheduler_task: asyncio.Task | None = None
_last_backup_date: str | None = None


async def _backup_loop() -> NoReturn:
    global _last_backup_date
    logger.info("Loop do agendador de backup diário iniciado.")
    while True:
        try:
            settings = get_settings()
            if settings.backup_enabled:
                now = datetime.now(timezone.utc)
                today_str = now.strftime("%Y-%m-%d")

                if (
                    now.hour == settings.backup_schedule_hour
                    and now.minute >= settings.backup_schedule_minute
                    and _last_backup_date != today_str
                ):
                    logger.info("Executando backup diário agendado para %s...", today_str)
                    create_backup(label="daily")
                    rotate_old_backups(retention_days=settings.backup_retention_days)
                    _last_backup_date = today_str
        except asyncio.CancelledError:
            logger.info("Loop do agendador de backup cancelado.")
            break
        except Exception as e:
            logger.error("Erro na rotina de agendamento de backup: %s", e)

        await asyncio.sleep(60)


def start_backup_scheduler() -> None:
    global _scheduler_task
    settings = get_settings()
    if settings.backup_enabled and (_scheduler_task is None or _scheduler_task.done()):
        _scheduler_task = asyncio.create_task(_backup_loop())
        logger.info("Agendador de backups diários iniciado.")


def stop_backup_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Agendador de backups diários parado.")
