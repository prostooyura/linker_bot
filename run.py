import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import router, init_db  # импорт инициализации БД и роутера
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def main():
    load_dotenv()

    bot = Bot(
        token=os.getenv('TOKEN'),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)  # ← правильно
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    await init_db()
    dp.include_router(router)

    print('Бот запущен')
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except aiohttp.ClientError as e:
        print(f'Ошибка подключения: {e}')
    except KeyboardInterrupt:
        print('Бот выключен')
