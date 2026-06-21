from datetime import date, datetime
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, distinct
from sqlalchemy.orm import selectinload
from bot.config.settings import get_settings
from bot.database.models import User, Service, Master, AvailableSlot, Appointment, Portfolio, Review
from bot.database.session import SessionLocal
from bot.handlers.states import Booking, ReviewState
from bot.keyboards.common import main_menu, back_menu
from bot.keyboards.inline import services_kb, masters_kb, dates_kb, times_kb, confirm_kb, appointments_kb, portfolio_categories, portfolio_nav
from bot.services.appointments import create_appointment, cancel_appointment, format_appointment

router = Router(); settings = get_settings()

async def show_menu(target, user_id: int):
    text = f"Привет! 💅 Добро пожаловать в {settings.salon_name}. Помогу выбрать услугу и записаться на удобное время."
    await target.answer(text, reply_markup=main_menu(user_id in settings.admin_id_set))

@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == message.from_user.id))).scalar_one_or_none()
        if not user:
            session.add(User(telegram_id=message.from_user.id, full_name=message.from_user.full_name, username=message.from_user.username)); await session.commit()
    await show_menu(message, message.from_user.id)

@router.message(Command("menu"))
async def menu_cmd(message: Message, state: FSMContext):
    await state.clear(); await show_menu(message, message.from_user.id)

@router.callback_query(F.data == "menu")
async def menu_cb(call: CallbackQuery, state: FSMContext):
    await state.clear(); await call.message.edit_text("Главное меню 🌸", reply_markup=main_menu(call.from_user.id in settings.admin_id_set)); await call.answer()

@router.callback_query(F.data == "services:list")
async def services_list(call: CallbackQuery):
    async with SessionLocal() as session:
        services = (await session.execute(select(Service).where(Service.is_active == True))).scalars().all()
    text = "💎 Услуги и цены\n\n" + ("\n\n".join(f"<b>{s.title}</b>\n{s.description}\nЦена: {s.price}₽\nДлительность: ~{s.duration_minutes} мин." for s in services) or "Пока список услуг пуст.")
    await call.message.edit_text(text, reply_markup=back_menu()); await call.answer()

@router.callback_query(F.data == "contacts")
async def contacts(call: CallbackQuery):
    text = f"📍 <b>{settings.salon_name}</b>\nАдрес: {settings.salon_address}\nТелефон: {settings.salon_phone}\nInstagram: {settings.salon_instagram}\nСайт: {settings.salon_site}\nКарта: {settings.salon_map_url}\nГрафик: {settings.salon_working_hours}"
    await call.message.edit_text(text, reply_markup=back_menu()); await call.answer()

@router.callback_query(F.data == "help")
async def help_cb(call: CallbackQuery):
    await call.message.edit_text("❔ Если нужна помощь, напишите администратору или позвоните в салон. Для записи нажмите «Записаться» 💅", reply_markup=back_menu()); await call.answer()

@router.callback_query(F.data == "book:start")
async def book_start(call: CallbackQuery, state: FSMContext):
    async with SessionLocal() as session: services = (await session.execute(select(Service).where(Service.is_active == True))).scalars().all()
    if not services: await call.message.edit_text("Пока нет доступных услуг. Попробуйте позже ✨", reply_markup=back_menu()); return
    await state.set_state(Booking.service); await call.message.edit_text("Выберите услугу 💎", reply_markup=services_kb(services)); await call.answer()

@router.callback_query(Booking.service, F.data.startswith("book:service:"))
async def pick_service(call: CallbackQuery, state: FSMContext):
    await state.update_data(service_id=int(call.data.split(":")[-1])); await state.set_state(Booking.master)
    async with SessionLocal() as session: masters = (await session.execute(select(Master).where(Master.is_active == True))).scalars().all()
    await call.message.edit_text("Выберите мастера 🌸", reply_markup=masters_kb(masters)); await call.answer()

@router.callback_query(Booking.master, F.data.startswith("book:master:"))
async def pick_master(call: CallbackQuery, state: FSMContext):
    master_id = int(call.data.split(":")[-1]); await state.update_data(master_id=master_id); await state.set_state(Booking.date)
    async with SessionLocal() as session:
        dates = (await session.execute(select(distinct(AvailableSlot.date)).where(AvailableSlot.master_id==master_id, AvailableSlot.date>=date.today(), AvailableSlot.is_booked==False, AvailableSlot.is_blocked==False).order_by(AvailableSlot.date))).scalars().all()
    if not dates: await call.message.edit_text("У этого мастера пока нет свободных дат ✨", reply_markup=back_menu()); return
    await call.message.edit_text("Выберите удобную дату 📅", reply_markup=dates_kb(dates)); await call.answer()

@router.callback_query(Booking.date, F.data.startswith("book:date:"))
async def pick_date(call: CallbackQuery, state: FSMContext):
    d = date.fromisoformat(call.data.split(":")[-1]); data = await state.get_data(); await state.update_data(date=d.isoformat()); await state.set_state(Booking.time)
    async with SessionLocal() as session:
        slots = (await session.execute(select(AvailableSlot).where(AvailableSlot.master_id==data["master_id"], AvailableSlot.date==d, AvailableSlot.is_booked==False, AvailableSlot.is_blocked==False).order_by(AvailableSlot.time))).scalars().all()
    slots = [s for s in slots if datetime.combine(s.date, s.time) > datetime.now()]
    if not slots: await call.message.edit_text("На эту дату свободного времени нет 💫", reply_markup=back_menu()); return
    await call.message.edit_text("Выберите время ⏰", reply_markup=times_kb(slots)); await call.answer()

@router.callback_query(Booking.time, F.data.startswith("book:slot:"))
async def pick_time(call: CallbackQuery, state: FSMContext):
    await state.update_data(slot_id=int(call.data.split(":")[-1])); await state.set_state(Booking.name)
    await call.message.edit_text("Как вас зовут? 🌷"); await call.answer()

@router.message(Booking.name)
async def name_input(message: Message, state: FSMContext):
    if len(message.text or "") < 2: await message.answer("Пожалуйста, укажите имя минимум из 2 символов."); return
    await state.update_data(name=message.text.strip()); await state.set_state(Booking.phone); await message.answer("Укажите номер телефона для связи 📞")

@router.message(Booking.phone)
async def phone_input(message: Message, state: FSMContext):
    phone = (message.text or "").strip()
    if len(phone) < 7: await message.answer("Похоже, номер слишком короткий. Попробуйте ещё раз 📞"); return
    await state.update_data(phone=phone); await state.set_state(Booking.comment); await message.answer("Комментарий к записи? Если комментария нет, напишите «нет».")

@router.message(Booking.comment)
async def comment_input(message: Message, state: FSMContext):
    comment = None if (message.text or "").lower().strip() in {"нет", "-"} else message.text.strip(); await state.update_data(comment=comment); data = await state.get_data()
    async with SessionLocal() as session:
        service = await session.get(Service, data["service_id"]); master = await session.get(Master, data["master_id"]); slot = await session.get(AvailableSlot, data["slot_id"])
    await state.set_state(Booking.confirm)
    await message.answer(f"Проверьте запись:\n\nУслуга: {service.title}\nМастер: {master.name}\nДата: {slot.date:%d.%m.%Y}\nВремя: {slot.time:%H:%M}\nИмя: {data['name']}\nТелефон: {data['phone']}\nКомментарий: {comment or '—'}", reply_markup=confirm_kb())

@router.callback_query(Booking.confirm, F.data == "book:confirm")
async def confirm_booking(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    try:
        async with SessionLocal() as session: appt = await create_appointment(session, call.from_user.id, data["service_id"], data["master_id"], data["slot_id"], data["name"], data["phone"], data.get("comment"))
    except ValueError as e:
        await call.message.edit_text(str(e), reply_markup=back_menu()); await state.clear(); return
    await state.clear(); text = "✅ Вы записаны!\n\n" + format_appointment(appt)
    await call.message.edit_text(text, reply_markup=back_menu())
    for admin_id in settings.admin_id_set: await bot.send_message(admin_id, "Новая запись:\n" + format_appointment(appt))
    await call.answer()

@router.callback_query(F.data == "my:appointments")
async def my_appointments(call: CallbackQuery):
    async with SessionLocal() as session:
        items = (await session.execute(select(Appointment).options(selectinload(Appointment.service), selectinload(Appointment.master)).where(Appointment.user_id==call.from_user.id, Appointment.status=="active").order_by(Appointment.date, Appointment.time))).scalars().all()
    if not items: await call.message.edit_text("У вас пока нет активных записей 💅", reply_markup=back_menu())
    else: await call.message.edit_text("📒 Ваши активные записи:", reply_markup=appointments_kb(items))
    await call.answer()

@router.callback_query(F.data.startswith("appt:details:"))
async def appt_details(call: CallbackQuery):
    appt_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session: a = (await session.execute(select(Appointment).options(selectinload(Appointment.service), selectinload(Appointment.master)).where(Appointment.id==appt_id, Appointment.user_id==call.from_user.id))).scalar_one_or_none()
    await call.message.answer(format_appointment(a) if a else "Запись не найдена."); await call.answer()

@router.callback_query(F.data.startswith("appt:cancel:"))
async def appt_cancel(call: CallbackQuery, bot: Bot):
    async with SessionLocal() as session: a = await cancel_appointment(session, int(call.data.split(":")[-1]), call.from_user.id)
    if not a: await call.answer("Запись не найдена или уже отменена", show_alert=True); return
    await call.message.edit_text("Запись отменена. Слот снова свободен 🌿", reply_markup=back_menu())
    for admin_id in settings.admin_id_set: await bot.send_message(admin_id, "Клиент отменил запись:\n" + format_appointment(a))
    await call.answer()

@router.callback_query(F.data == "portfolio:cats")
async def portfolio_cats(call: CallbackQuery):
    await call.message.edit_text("Выберите категорию портфолио 🖼", reply_markup=portfolio_categories()); await call.answer()

@router.callback_query(F.data.startswith("portfolio:cat:"))
async def portfolio_cat(call: CallbackQuery):
    category = call.data.split(":", 2)[-1]; await show_portfolio(call, category, 0)

@router.callback_query(F.data.startswith("portfolio:show:"))
async def portfolio_show(call: CallbackQuery):
    _, _, category, index = call.data.split(":", 3); await show_portfolio(call, category, int(index))

async def show_portfolio(call: CallbackQuery, category: str, index: int):
    async with SessionLocal() as session: items = (await session.execute(select(Portfolio).where(Portfolio.category==category))).scalars().all()
    if not items: await call.message.edit_text("В этой категории пока нет фото ✨", reply_markup=portfolio_categories()); return
    item = items[max(0, min(index, len(items)-1))]; caption = f"{category} ({index+1}/{len(items)})\n{item.caption or ''}"
    await call.message.answer_photo(item.file_id or item.url, caption=caption, reply_markup=portfolio_nav(category, index, len(items))); await call.answer()

@router.callback_query(F.data == "review:start")
async def review_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ReviewState.text); await call.message.edit_text("Будем благодарны за отзыв ⭐ Напишите, что вам понравилось или что можно улучшить."); await call.answer()

@router.message(ReviewState.text)
async def review_text(message: Message, state: FSMContext, bot: Bot):
    if len(message.text or "") < 5: await message.answer("Отзыв слишком короткий. Напишите пару слов подробнее ✨"); return
    async with SessionLocal() as session: session.add(Review(user_id=message.from_user.id, text=message.text.strip())); await session.commit()
    await state.clear(); await message.answer("Спасибо за отзыв! Нам очень приятно 💖", reply_markup=main_menu(message.from_user.id in settings.admin_id_set))
    for admin_id in settings.admin_id_set: await bot.send_message(admin_id, f"Новый отзыв от {message.from_user.full_name}:\n{message.text}")
