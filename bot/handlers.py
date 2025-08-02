from aiogram import Router, F
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
import uuid
import os

from bot.states import Form
from db import async_session
from models import User
from yookassa import Payment
from yookassa.configuration import Configuration

Configuration.account_id = int(os.getenv("YOOKASSA_SHOP_ID"))
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

router = Router()

# /start
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    text = (
        "👋 Привет! Я AI-автопостер.\n"
        "Я буду:\n"
        "• анализировать вашу группу ВК,\n"
        "• генерировать посты,\n"
        "• публиковать их по расписанию.\n"
        "Нажмите кнопку ниже, чтобы купить подписку 👇"
    )
    payment_id, url = create_payment(990, "Подписка AI-постер", message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 990 ₽", url=url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_{payment_id}")]
    ])
    await message.answer(text, reply_markup=kb)

def create_payment(amount: int, description: str, tg_id: int):
    payment = Payment.create({
        "amount": {"value": f"{amount}.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://t.me/ii_poster_bot?start=pay_{tg_id}"
        },
        "capture": True,
        "description": description,
        "metadata": {"tg_id": str(tg_id)}
    })
    return payment.id, payment.confirmation.confirmation_url

# Check Payment
@router.callback_query(F.data.startswith("check_"))
async def check_payment(callback: CallbackQuery):
    payment_id = callback.data.split("_", 1)[1]
    payment = Payment.find_one(payment_id)

    if payment.status == "succeeded":
        await callback.message.edit_text(
            "✅ Оплата прошла! Теперь пришлите ключ API вашего сообщества ВК:"
        )
    else:
        await callback.answer(
            "⏳ Платёж ещё не подтверждён. Попробуйте поже.",
            show_alert=True,
        )

@router.message(Form.waiting_access_token)
async def receive_access_token(message: Message, state: FSMContext):
    access_token = message.text
    await state.update_data(access_token=access_token)
    await message.answer("Ключ доступа получен. Теперь пришлите ключ API вашего сообщества ВК:")

@router.message(Form.waiting_vk)
async def receive_vk(message: Message, state: FSMContext):
    await state.update_data(vk_url=message.text)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Деловой", callback_data="style_деловой")],
            [InlineKeyboardButton(text="Экспертный", callback_data="style_экспертный")],
            [InlineKeyboardButton(text="Дружелюбный", callback_data="style_дружелюбный")],
        ]
    )
    await message.answer("Выберите стиль постов:", reply_markup=kb)
    await state.set_state(Form.waiting_style)

@router.callback_query(F.data.startswith("style_"))
async def receive_style(callback: CallbackQuery, state: FSMContext):
    style = callback.data.split("_", 1)[1]
    await state.update_data(style=style)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 пост/день", callback_data="freq_1")],
        [InlineKeyboardButton(text="2 поста/день", callback_data="freq_2")],
        [InlineKeyboardButton(text="3 поста/день", callback_data="freq_3")],
    ])
    await callback.message.edit_text("Выберите количество постов в день:", reply_markup=kb)
    await state.set_state(Form.waiting_freq)

@router.callback_query(F.data.startswith("freq_"))
async def receive_freq(callback: CallbackQuery, state: FSMContext):
    freq = float(callback.data.split("_", 1)[1])
    await state.update_data(posts_per_day=freq)
    await state.set_state(Form.waiting_keywords)

@router.message(Form.waiting_keywords)
async def receive_keywords(message: Message, state: FSMContext):
    keywords = message.text.split()
    post_text = await generate_post(keywords)
    group_id = state.data["vk_url"].split("/")[-2]  # Извлека "vk.com/-12345678" → 12345678
    access_token = state.data["access_token"]
    
    post_result = post_to_vk(group_id, access_token, post_text)
    if post_result.get("response"):
        await message.answer("Пост опубликован.")
    else:
        await message.answer("Не удалось опубликовать пост.")
    await state.finish()

async def generate_post(keywords: list) -> str:
    post_text = " ".join(keywords)
    return post_text[:300]  # Убеди, что пост не превышествует 300 символов

def post_to_vk(group_id: int, access_token: str, post_text: str):
    url = "https://api.vk.com/method/wall.post"
    params = {
        "access_token": access_token,
        "v": 5.101,
        "owner_id": group_id,
        "message": f"Тест бота {post_text} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} | {os.getenv('VK_USER_NAME')}"
    }
    response = requests.post(url, params=params)
    return response.json()