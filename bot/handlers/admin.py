from datetime import date, datetime, time
from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.config.settings import get_settings
from bot.database.models import Appointment, Service, Master, AvailableSlot, Portfolio, Review
from bot.database.session import SessionLocal
from bot.handlers.states import AdminState
from bot.keyboards.common import back_menu
from bot.services.appointments import cancel_appointment, format_appointment

router = Router(); settings = get_settings()

def is_admin(uid: int) -> bool: return uid in settings.admin_id_set

def admin_kb():
    kb = InlineKeyboardBuilder()
    for text, data in [("📋 Все записи", "admin:all"),("📅 Сегодня", "admin:today"),("🔎 Записи по дате", "admin:date"),("➕ Услуга", "admin:add_service"),("➖ Удалить услугу", "admin:del_service"),("➕ Мастер", "admin:add_master"),("➖ Удалить мастера", "admin:del_master"),("⏰ Добавить слот", "admin:add_slot"),("🚫 Блокировать время", "admin:block_slot"),("🖼 Добавить портфолио", "admin:add_portfolio"),("⭐ Отзывы", "admin:reviews"),("❌ Отменить запись", "admin:cancel")]:
        kb.button(text=text, callback_data=data)
    kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(2); return kb.as_markup()

@router.callback_query(F.data == "admin:menu")
async def admin_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id): await call.answer("Недоступно", show_alert=True); return
    await call.message.edit_text("⚙️ Админ-панель", reply_markup=admin_kb()); await call.answer()

async def send_appointments(call: CallbackQuery, only_today=False):
    q = select(Appointment).options(selectinload(Appointment.service), selectinload(Appointment.master)).order_by(Appointment.date, Appointment.time)
    if only_today: q = q.where(Appointment.date == date.today())
    async with SessionLocal() as session: items = (await session.execute(q)).scalars().all()
    text = "Записей нет." if not items else "\n\n".join(format_appointment(a)+f"\nСтатус: {a.status}" for a in items[:30])
    await call.message.edit_text(text, reply_markup=admin_kb())

@router.callback_query(F.data.in_({"admin:all", "admin:today"}))
async def admin_lists(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await send_appointments(call, call.data == "admin:today"); await call.answer()

@router.callback_query(F.data == "admin:date")
async def ask_date(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminState.date); await call.message.edit_text("Введите дату в формате ДД.ММ.ГГГГ"); await call.answer()

@router.message(AdminState.date)
async def by_date(message: Message, state: FSMContext):
    try: d = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError: await message.answer("Неверный формат. Пример: 25.12.2026"); return
    async with SessionLocal() as session: items = (await session.execute(select(Appointment).options(selectinload(Appointment.service), selectinload(Appointment.master)).where(Appointment.date==d))).scalars().all()
    await state.clear(); await message.answer("Записей нет." if not items else "\n\n".join(format_appointment(a) for a in items), reply_markup=admin_kb())

@router.callback_query(F.data == "admin:add_service")
async def add_service_ask(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.add_service); await call.message.edit_text("Введите услугу: Название | описание | цена | длительность_мин"); await call.answer()

@router.message(AdminState.add_service)
async def add_service(message: Message, state: FSMContext):
    try:
        title, desc, price, dur = [p.strip() for p in message.text.split("|", 3)]
        async with SessionLocal() as session: session.add(Service(title=title, description=desc, price=int(price), duration_minutes=int(dur))); await session.commit()
    except Exception: await message.answer("Не получилось. Формат: Название | описание | 2500 | 120"); return
    await state.clear(); await message.answer("Услуга добавлена ✅", reply_markup=admin_kb())

@router.callback_query(F.data == "admin:add_master")
async def add_master_ask(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.add_master); await call.message.edit_text("Введите мастера: Имя | описание"); await call.answer()

@router.message(AdminState.add_master)
async def add_master(message: Message, state: FSMContext):
    name, _, desc = message.text.partition("|")
    async with SessionLocal() as session: session.add(Master(name=name.strip(), description=desc.strip())); await session.commit()
    await state.clear(); await message.answer("Мастер добавлен ✅", reply_markup=admin_kb())

@router.callback_query(F.data == "admin:add_slot")
async def add_slot_ask(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.add_slot); await call.message.edit_text("Введите слот: master_id | ДД.ММ.ГГГГ | ЧЧ:ММ"); await call.answer()

@router.message(AdminState.add_slot)
async def add_slot(message: Message, state: FSMContext):
    try:
        mid, d, t = [p.strip() for p in message.text.split("|")]
        async with SessionLocal() as session: session.add(AvailableSlot(master_id=int(mid), date=datetime.strptime(d, "%d.%m.%Y").date(), time=datetime.strptime(t, "%H:%M").time())); await session.commit()
    except Exception: await message.answer("Ошибка. Пример: 1 | 25.12.2026 | 14:00"); return
    await state.clear(); await message.answer("Слот добавлен ✅", reply_markup=admin_kb())

@router.callback_query(F.data == "admin:del_service")
async def del_service_list(call: CallbackQuery):
    async with SessionLocal() as session:
        items = (await session.execute(select(Service).where(Service.is_active == True))).scalars().all()
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(text=f"Удалить: {item.title}", callback_data=f"admin:del_service_id:{item.id}")
    kb.button(text="⬅️ Админ-панель", callback_data="admin:menu"); kb.adjust(1)
    await call.message.edit_text("Выберите услугу для скрытия:", reply_markup=kb.as_markup()); await call.answer()

@router.callback_query(F.data.startswith("admin:del_service_id:"))
async def del_service_do(call: CallbackQuery):
    service_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        item = await session.get(Service, service_id)
        if item: item.is_active = False; await session.commit()
    await call.message.edit_text("Услуга скрыта ✅", reply_markup=admin_kb()); await call.answer()

@router.callback_query(F.data == "admin:del_master")
async def del_master_list(call: CallbackQuery):
    async with SessionLocal() as session:
        items = (await session.execute(select(Master).where(Master.is_active == True))).scalars().all()
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(text=f"Удалить: {item.name}", callback_data=f"admin:del_master_id:{item.id}")
    kb.button(text="⬅️ Админ-панель", callback_data="admin:menu"); kb.adjust(1)
    await call.message.edit_text("Выберите мастера для скрытия:", reply_markup=kb.as_markup()); await call.answer()

@router.callback_query(F.data.startswith("admin:del_master_id:"))
async def del_master_do(call: CallbackQuery):
    master_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        item = await session.get(Master, master_id)
        if item: item.is_active = False; await session.commit()
    await call.message.edit_text("Мастер скрыт ✅", reply_markup=admin_kb()); await call.answer()

@router.callback_query(F.data == "admin:block_slot")
async def block_slot_list(call: CallbackQuery):
    async with SessionLocal() as session:
        items = (await session.execute(select(AvailableSlot).options(selectinload(AvailableSlot.master)).where(AvailableSlot.date >= date.today(), AvailableSlot.is_booked == False, AvailableSlot.is_blocked == False).order_by(AvailableSlot.date, AvailableSlot.time).limit(30))).scalars().all()
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(text=f"{item.date:%d.%m} {item.time:%H:%M} {item.master.name}", callback_data=f"admin:block_slot_id:{item.id}")
    kb.button(text="⬅️ Админ-панель", callback_data="admin:menu"); kb.adjust(1)
    await call.message.edit_text("Выберите время для блокировки:" if items else "Нет доступных слотов для блокировки.", reply_markup=kb.as_markup()); await call.answer()

@router.callback_query(F.data.startswith("admin:block_slot_id:"))
async def block_slot_do(call: CallbackQuery):
    slot_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        slot = await session.get(AvailableSlot, slot_id)
        if slot and not slot.is_booked: slot.is_blocked = True; await session.commit()
    await call.message.edit_text("Слот заблокирован ✅", reply_markup=admin_kb()); await call.answer()

@router.callback_query(F.data == "admin:add_portfolio")
async def portfolio_ask(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.portfolio_photo); await call.message.edit_text("Отправьте: Категория | file_id или URL | подпись"); await call.answer()

@router.message(AdminState.portfolio_photo)
async def portfolio_add(message: Message, state: FSMContext):
    try:
        cat, src, cap = [p.strip() for p in message.text.split("|", 2)]
        async with SessionLocal() as session: session.add(Portfolio(category=cat, file_id=None if src.startswith("http") else src, url=src if src.startswith("http") else None, caption=cap)); await session.commit()
    except Exception: await message.answer("Формат: Маникюр | https://... | Нежный нюд"); return
    await state.clear(); await message.answer("Фото добавлено ✅", reply_markup=admin_kb())

@router.callback_query(F.data == "admin:reviews")
async def reviews(call: CallbackQuery):
    async with SessionLocal() as session: items = (await session.execute(select(Review).order_by(Review.created_at.desc()).limit(20))).scalars().all()
    await call.message.edit_text("Отзывов нет." if not items else "\n\n".join(f"#{r.id} от {r.user_id}: {r.text}" for r in items), reply_markup=admin_kb()); await call.answer()

@router.callback_query(F.data == "admin:cancel")
async def cancel_ask(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.cancel_appointment); await call.message.edit_text("Введите ID записи для отмены"); await call.answer()

@router.message(AdminState.cancel_appointment)
async def admin_cancel(message: Message, state: FSMContext, bot: Bot):
    async with SessionLocal() as session: a = await cancel_appointment(session, int(message.text.strip()))
    await state.clear()
    if not a: await message.answer("Активная запись не найдена.", reply_markup=admin_kb()); return
    await bot.send_message(a.user_id, "Ваша запись отменена администратором. Свяжитесь с салоном для уточнения 💅")
    await message.answer("Запись отменена ✅", reply_markup=admin_kb())
