from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
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

# ---------- /start ----------
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    text = (
        "👋 Привет! Я AI-автопостер.\n\n"
        "Я буду:\n"
        "• анализировать вашу группу ВК,\n"
        "• генерировать посты,\n"
        "• публиковать их по расписанию.\n\n"
        "Нажмите кнопку ниже, чтобы купить подписку 👇"
    )
    payment_id, url = create_payment(990, "Подписка AI-постер", message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 990 ₽", url=url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_{payment_id}")]
    ])
    await message.answer(text, reply_markup=kb)

# ---------- Купить ----------
def create_payment(amount: int, description: str, tg_id: int):
    payment = Payment.create({
        "amount": {"value": f"{amount}.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/YOUR_BOT"
        },
        "capture": True,
        "description": description,
        "metadata": {"tg_id": str(tg_id)}
    })
    # возвращаем именно id и url
    return payment.id, payment.confirmation.confirmation_url

# ---------- Проверка ----------
@router.callback_query(F.data.startswith("check_"))
async def check_payment(callback: CallbackQuery, state: FSMContext):
    payment_id = callback.data.split("_", 1)[1]
    payment = Payment.find_one(payment_id)

    if payment.status == "succeeded":
        async with async_session() as s:
            u = User(
                tg_id=callback.from_user.id,
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True,
            )
            s.add(u)
            await s.commit()

        await callback.message.edit_text(
            "✅ Оплата прошла! Теперь пришлите ссылку на вашу группу ВК:"
        )
        await state.set_state(Form.waiting_vk)
    else:
        await callback.answer(
            "⏳ Платёж ещё не подтверждён. Попробуйте позже.",
            show_alert=True,
        )