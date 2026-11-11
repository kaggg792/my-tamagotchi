import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

import database as db_api

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не найдена! Добавьте её в настройки Render (Environment).")

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://onrender.com")


class InitPetRequest(BaseModel):
    userId: int
    name: str
    type: str


class ActionRequest(BaseModel):
    userId: int
    action: str


bot = Bot(token=9237944530:AAH0e9rpzZZOkDdgG6eTtpcAJQE9tSJRSNo)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Войти в Тамагочи", web_app=types.WebAppInfo(url=WEBAPP_URL))
    await message.answer(
        "Привет! Нажми на кнопку ниже, чтобы запустить игру и создать питомца!",
        reply_markup=builder.as_markup()
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_api.init_db()
    # Удаляем старый вебхук перед запуском polling, чтобы избежать конфликтов при перезапуске
    await bot.delete_webhook(drop_pending_updates=True)
    bot_task = asyncio.create_task(dp.start_polling(bot))
    yield
    bot_task.cancel()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.get("/api/get_pet/{user_id}")
async def get_pet_status(user_id: int):
    pet = await db_api.calculate_ticks(user_id)
    return {"status": "ok", "pet": pet}


@app.post("/api/create_pet")
async def create_new_pet(data: InitPetRequest):
    pet = await db_api.create_pet(data.userId, data.name, data.type)
    return {"status": "ok", "pet": pet}


@app.post("/api/action")
async def handle_action(data: ActionRequest):
    pet = await db_api.process_action(data.userId, data.action)
    return {"status": "ok", "pet": pet}


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
