from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 📱 Обычная клавиатура (ReplyKeyboard)
kboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/add_links"), KeyboardButton(text="/my_links")],
        [KeyboardButton(text="/delete_links")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите команду"
)