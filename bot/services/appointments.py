from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.database.models import Appointment, AvailableSlot


def format_appointment(a: Appointment) -> str:
    return (f"Запись #{a.id}\nУслуга: {a.service.title}\nМастер: {a.master.name}\n"
            f"Дата: {a.date:%d.%m.%Y}\nВремя: {a.time:%H:%M}\nКлиент: {a.client_name}\nТелефон: {a.phone}\nКомментарий: {a.comment or '—'}")

async def create_appointment(session, user_id: int, service_id: int, master_id: int, slot_id: int, name: str, phone: str, comment: str | None) -> Appointment:
    slot = await session.get(AvailableSlot, slot_id, with_for_update=True)
    if not slot or slot.is_booked or slot.is_blocked or datetime.combine(slot.date, slot.time) <= datetime.now():
        raise ValueError("Этот слот уже недоступен. Выберите другое время ✨")
    appt = Appointment(user_id=user_id, service_id=service_id, master_id=master_id, slot_id=slot.id, date=slot.date, time=slot.time, client_name=name, phone=phone, comment=comment, status="active")
    slot.is_booked = True
    session.add(appt); await session.commit(); await session.refresh(appt, ["service", "master"]); return appt

async def cancel_appointment(session, appointment_id: int, by_user_id: int | None = None) -> Appointment | None:
    q = select(Appointment).options(selectinload(Appointment.service), selectinload(Appointment.master), selectinload(Appointment.slot)).where(Appointment.id == appointment_id, Appointment.status == "active")
    if by_user_id: q = q.where(Appointment.user_id == by_user_id)
    appt = (await session.execute(q)).scalar_one_or_none()
    if not appt: return None
    appt.status = "cancelled"
    if appt.slot: appt.slot.is_booked = False
    await session.commit(); return appt
