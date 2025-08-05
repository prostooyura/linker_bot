import os
import asyncio
import random
import keyboards as kb
from aiogram import Router,Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, CommandObject
from dotenv import load_dotenv
from aiogram.enums import ChatAction
from aiogram.types import InputMediaPhoto, InputMediaVideo,Contact,Message, CallbackQuery
from datetime import datetime

import re
import aiosqlite

from aiogram.utils.markdown import hlink

from states import LinkStates
from aiogram.fsm.context import FSMContext

from states import DeleteStates, CategoryStates

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
DB_NAME = "links.db"
URL_REGEX = r'https?://\S+'

router = Router()
@router.message(Command('reset'))
async def reset_state(message: Message, state: FSMContext):
    # Очищаем текущее состояние
    await state.clear()
    
    # Можно также очистить все данные в хранилище
    # await state.storage.close()  # Полная очистка хранилища (опционально)
    
    await message.answer("Все состояния были сброшены. Вы можете начать заново.", reply_markup=kb.kboard)

@router.message(CommandStart())
async def cmd_start(message:Message):
    await message.answer(text = 'привет это бот помошник Джарвис')
    func_n = '''
Cписок команд бота джарвис
/add_links
/my_links
/delete_links
/categories
/reset
    '''
    await message.answer(func_n,reply_markup= kb.kboard)

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            category TEXT DEFAULT 'Без категории'
        )
        """)
        await db.commit()

# Добавим новые команды и обработчики
@router.message(Command('add_links'))
async def start_adding_link(message: Message, state: FSMContext):
    await message.answer("Выбери категорию или введи новую:")
    await state.set_state(LinkStates.waiting_for_category)

@router.message(LinkStates.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Теперь введи ссылку для сохранения:")
    await state.set_state(LinkStates.waiting_for_link)

@router.message(LinkStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    user_id = message.from_user.id
    url = message.text.strip()
    data = await state.get_data()
    category = data.get('category', 'Без категории')

    if not re.match(URL_REGEX, url):
        await message.answer("Это не похоже на ссылку. Попробуй снова.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO links (user_id, url, category) VALUES (?, ?, ?)", 
                        (user_id, url, category))
        await db.commit()

    await message.answer(f"Ссылка сохранена в категории '{category}'!")
    await state.clear()

@router.message(Command('my_links'))
async def cmd_links(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT category FROM links WHERE user_id = ? GROUP BY category", (user_id,))
        categories = await cursor.fetchall()

    if not categories:
        await message.answer("У тебя пока нет сохранённых ссылок.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category[0], callback_data=f"category_{category[0]}")]
        for category in categories
    ])
    
    await message.answer("Выбери категорию:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("category_"))
async def show_category_links(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, url FROM links WHERE user_id = ? AND category = ?", 
                                (user_id, category))
        rows = await cursor.fetchall()

    text = f"<b>Ссылки в категории '{category}':</b>\n"
    for i, (link_id, url) in enumerate(rows, start=1):
        text += f"{i}. {hlink(url, url)}\n"

    await callback.message.edit_text(text)
    await callback.answer()

@router.message(Command('categories'))
async def manage_categories(message: Message):
    await message.answer(
        "Управление категориями:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Создать категорию", callback_data="create_category")],
            [InlineKeyboardButton(text="Удалить категорию", callback_data="delete_category")]
        ])
    )

@router.callback_query(F.data == "create_category")
async def create_category(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи название новой категории:")
    await state.set_state(CategoryStates.waiting_for_category_name)
    await callback.answer()

@router.message(CategoryStates.waiting_for_category_name)
async def process_new_category(message: Message, state: FSMContext):
    category = message.text.strip()
    await message.answer(f"Категория '{category}' создана. Теперь можно добавлять в неё ссылки.")
    await state.clear()

@router.callback_query(F.data == "delete_category")
async def delete_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT category FROM links WHERE user_id = ? GROUP BY category", (user_id,))
        categories = await cursor.fetchall()

    if not categories:
        await callback.message.answer("У тебя пока нет категорий.")
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category[0], callback_data=f"deletecat_{category[0]}")]
        for category in categories
    ])
    
    await callback.message.answer("Выбери категорию для удаления:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("deletecat_"))
async def confirm_delete_category(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    await callback.message.answer(
        f"Ты уверен, что хочешь удалить категорию '{category}' и все ссылки в ней?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data=f"confirm_delete_{category}")],
            [InlineKeyboardButton(text="Нет", callback_data="cancel_delete")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def process_delete_category(callback: CallbackQuery):
    category = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM links WHERE user_id = ? AND category = ?", 
                        (user_id, category))
        await db.commit()
    
    await callback.message.answer(f"Категория '{category}' и все ссылки в ней удалены.")
    await callback.answer()

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.answer("Удаление отменено.")
    await callback.answer()
#-----------------------------------------------------------------------------------------------------------------------

@router.message(Command('delete_links'))
async def start_delete_link(message: Message, state: FSMContext):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, url FROM links WHERE user_id = ?", (user_id,))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("У тебя пока нет сохранённых ссылок.")
        return

    # Сохраняем список ID во временное состояние
    await state.update_data(links=rows)

    text = "<b>Выбери номер ссылки для удаления:</b>\n"
    for i, (_, url) in enumerate(rows, start=1):
        text += f"{i}. {hlink(url, url)}\n"

    await message.answer(text, parse_mode="HTML")
    await message.answer("Введи номер ссылки, которую хочешь удалить:")
    await state.set_state(DeleteStates.waiting_for_index)

@router.message(DeleteStates.waiting_for_index)
async def process_delete_index(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи число.")
        return

    index = int(message.text) - 1
    data = await state.get_data()
    links = data.get("links", [])

    if index < 0 or index >= len(links):
        await message.answer("Некорректный номер.")
        return

    link_id = links[index][0]  # ID из БД

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM links WHERE id = ?", (link_id,))
        await db.commit()

    await message.answer("Ссылка удалена.")
    await state.clear()


