import asyncio, datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.states import Form
from db import async_session
from models import User, Post
from payments import create_payment
from openai_client import generate_post, generate_image
from vk import VKPoster
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    payment_id, url = create_payment(990, "Подписка AI-постер на 30 дней")
    await message.answer(
        "Чтобы активировать автопостинг, оплатите подписку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 990 ₽", url=url)]
        ])
    )

@router.message(F.text.startswith("https://vk.com/"))
async def receive_vk(message: Message, state: FSMContext):
    group_name = message.text.split("/")[-1]
    await state.update_data(group_name=group_name)
    await state.set_state(Form.waiting_theme)
    await message.answer("Отлично! Напишите кратко тематику паблика (или оставьте как есть):")

@router.message(Form.waiting_theme)
async def receive_theme(message: Message, state: FSMContext):
    await state.update_data(theme=message.text)
    await message.answer("Выберите стиль постов:", reply_markup=styles_kb())
    await state.set_state(Form.waiting_style)

@router.callback_query(F.data.startswith("style_"))
async def receive_style(callback: CallbackQuery, state: FSMContext):
    style = callback.data.split("_",1)[1]
    await state.update_data(style=style)
    await callback.message.edit_text("Сколько постов в день?", reply_markup=freq_kb())
    await state.set_state(Form.waiting_freq)

@router.callback_query(F.data.startswith("freq_"))
async def receive_freq(callback: CallbackQuery, state: FSMContext):
    freq = float(callback.data.split("_")[1])
    data = await state.get_data()
    async with async_session() as s:
        u = User(tg_id=callback.from_user.id,
                 vk_group_id=data["group_name"],
                 theme=data["theme"],
                 style=data["style"],
                 posts_per_day=freq,
                 expires_at=datetime.datetime.utcnow()+datetime.timedelta(days=30))
        s.add(u)
        await s.commit()
    await callback.message.edit_text("✅ Настройки сохранены. Посты начнут публиковаться завтра.")