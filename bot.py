import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from user_handler import user_router
from admin_handler import admin_router
from payment_handler import payment_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def _healthcheck_server():
    port = int(os.getenv("PORT", "10000"))

    async def handler(reader, writer):
        try:
            await reader.read(1024)
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain; charset=utf-8\r\n"
                b"Content-Length: 2\r\n"
                b"Connection: close\r\n\r\nOK"
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handler, host="0.0.0.0", port=port)
    logger.info("Healthcheck server portda ishga tushdi: %s", port)
    return server


async def main():
    await init_db()
    health_server = await _healthcheck_server()

    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(admin_router)
    dp.include_router(payment_router)
    dp.include_router(user_router)

    logger.info("EduBot ishga tushdi! ✅")
    try:
        await asyncio.gather(
            dp.start_polling(bot, drop_pending_updates=True),
            health_server.serve_forever(),
        )
    finally:
        health_server.close()
        await health_server.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
