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

from states import DeleteStates

DB_NAME = "links.db"
URL_REGEX = r'https?://\S+'

router = Router()
@router.message(CommandStart())
async def cmd_start(message:Message):
    await message.answer(text = 'привет это бот помошник Джарвис')
    func_n = '''
    список команд бота джарвис
    /add_links
    /my_links
    /delete_links
    '''
    await message.answer(func_n,reply_markup= kb.kboard)

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT
        )
        """)
        await db.commit()

@router.message(Command('add_links'))
async def start_adding_link(message: Message, state: FSMContext):
    await message.answer("Введи ссылку для сохранения:")
    await state.set_state(LinkStates.waiting_for_link)

@router.message(LinkStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    user_id = message.from_user.id
    url = message.text.strip()

    if not re.match(URL_REGEX, url):
        await message.answer("Это не похоже на ссылку. Попробуй снова.")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO links (user_id, url) VALUES (?, ?)", (user_id, url))
        await db.commit()

    await message.answer("Ссылка сохранена!")
    await state.clear()
    
#-----------------------------------------------------------------------------------------------------------------------

@router.message(Command('my_links'))
async def cmd_links(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, url FROM links WHERE user_id = ?", (user_id,))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("У тебя пока нет сохранённых ссылок.")
        return

    text = "<b>Твои ссылки:</b>\n"
    for i, (link_id, url) in enumerate(rows, start=1):
        text += f"{i}. {hlink(url, url)}\n"

    await message.answer(text)
    
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


