import asyncio, logging, os
from aiogram import Bot, Dispatcher
from bot.handlers import router
from db import create_tables

async def main():
    await create_tables()
    bot = Bot(os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())