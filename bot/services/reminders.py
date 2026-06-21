from datetime import datetime, timedelta
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.database.models import Appointment
from bot.database.session import SessionLocal
from bot.services.appointments import format_appointment

async def send_due_reminders(bot: Bot) -> None:
    now = datetime.now()
    async with SessionLocal() as session:
        q = select(Appointment).options(selectinload(Appointment.service), selectinload(Appointment.master)).where(Appointment.status == "active")
        for a in (await session.execute(q)).scalars():
            dt = datetime.combine(a.date, a.time)
            if not a.reminded_24h and now <= dt - timedelta(hours=24) <= now + timedelta(minutes=1):
                await bot.send_message(a.user_id, "💅 Напоминаем: до вашей записи осталось 24 часа!\n\n" + format_appointment(a)); a.reminded_24h = True
            if not a.reminded_2h and now <= dt - timedelta(hours=2) <= now + timedelta(minutes=1):
                await bot.send_message(a.user_id, "✨ Ждём вас через 2 часа!\n\n" + format_appointment(a)); a.reminded_2h = True
        await session.commit()

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(send_due_reminders, "interval", minutes=1, args=[bot], id="appointment_reminders")
    scheduler.start(); return scheduler
