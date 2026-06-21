from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for text, data in [
        ("💅 Записаться", "book:start"), ("🖼 Портфолио мастера", "portfolio:cats"),
        ("💎 Услуги и цены", "services:list"), ("📒 Мои записи", "my:appointments"),
        ("📍 Контакты", "contacts"), ("⭐ Отзывы / оставить отзыв", "review:start"), ("❔ Помощь", "help"),
    ]:
        kb.button(text=text, callback_data=data)
    if is_admin:
        kb.button(text="⚙️ Админ-панель", callback_data="admin:menu")
    kb.adjust(1)
    return kb.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder(); kb.button(text="⬅️ В меню", callback_data="menu"); return kb.as_markup()
