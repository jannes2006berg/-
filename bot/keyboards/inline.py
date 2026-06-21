from datetime import date, time
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.database.models import Service, Master, Appointment, AvailableSlot


def services_kb(services: list[Service], prefix="book:service") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in services: kb.button(text=f"{s.title} — {s.price}₽", callback_data=f"{prefix}:{s.id}")
    kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(1); return kb.as_markup()

def masters_kb(masters: list[Master]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in masters: kb.button(text=m.name, callback_data=f"book:master:{m.id}")
    kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(1); return kb.as_markup()

def dates_kb(dates: list[date]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in dates: kb.button(text=d.strftime("%d.%m.%Y"), callback_data=f"book:date:{d.isoformat()}")
    kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(2); return kb.as_markup()

def times_kb(slots: list[AvailableSlot]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in slots: kb.button(text=s.time.strftime("%H:%M"), callback_data=f"book:slot:{s.id}")
    kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(3); return kb.as_markup()

def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder(); kb.button(text="✅ Подтвердить", callback_data="book:confirm"); kb.button(text="❌ Отменить", callback_data="menu"); kb.adjust(1); return kb.as_markup()

def appointments_kb(items: list[Appointment]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for a in items:
        kb.button(text=f"{a.date:%d.%m} {a.time:%H:%M} — отменить", callback_data=f"appt:cancel:{a.id}")
        kb.button(text=f"🔁 Детали #{a.id}", callback_data=f"appt:details:{a.id}")
    kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(1); return kb.as_markup()

def portfolio_categories() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for cat in ["Маникюр", "Наращивание", "Дизайн", "Френч", "Педикюр"]: kb.button(text=cat, callback_data=f"portfolio:cat:{cat}")
    kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(1); return kb.as_markup()

def portfolio_nav(category: str, index: int, total: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if total > 1:
        kb.button(text="⬅️ Назад", callback_data=f"portfolio:show:{category}:{max(index-1,0)}")
        kb.button(text="Далее ➡️", callback_data=f"portfolio:show:{category}:{min(index+1,total-1)}")
    kb.button(text="📂 Категории", callback_data="portfolio:cats"); kb.button(text="⬅️ В меню", callback_data="menu"); kb.adjust(2,1,1); return kb.as_markup()
