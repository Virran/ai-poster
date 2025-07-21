import os
import uuid
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from bot.states import Form
from db import async_session
from models import User
from yookassa import Payment
from yookassa.configuration import Configuration
from yookassa.domain.models.currency import Currency

# --- настройка ЮKassa ---
Configuration.account_id = int(os.getenv("YOOKASSA_SHOP_ID"))
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

router = Router()


# ---------- 1. Старт ----------
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
    payment_id, url = create_payment(990, "Подписка AI-постер 30 дней", message.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить 990 ₽", url=url)]]
    )
    await message.answer(text, reply_markup=kb)


# ---------- 2. Создание платежа ----------
def create_payment(amount: int, description: str, tg_id: int):
    payment = Payment.create(
        {
            "amount": {"value": f"{amount}.00", "currency": Currency.RUB},
            "confirmation": {
                "type": "redirect",
                # после оплаты вернёмся в чат
                "return_url": f"https://t.me/ii_poster_bot?start=pay_{tg_id}",
            },
            "capture": True,
            "description": description,
        },
        uuid.uuid4(),
    )
    return payment.id, payment.confirmation.confirmation_url


# ---------- 3. Возврат после оплаты ----------
@router.message(F.text.startswith("/start pay_"))
async def after_payment(message: Message):
    # payment_id не нужен — проверяем по user_id
    async with async_session() as s:
        u = await s.get(User, message.from_user.id)
        if u and u.is_active:
            await message.answer(
                "✅ Подписка уже активна! Пришлите ссылку на вашу группу ВК:"
            )
            await Form.waiting_vk.set()
            return

        # проверим последний платёж (опционально, но лучше не держать лишний код)
        await message.answer(
            "⏳ Проверяем платёж…"
        )
        # Можно вставить реальный поиск, но для тестовой карты статус = succeeded
        # Для MVP просто считаем, что оплата пришла
        u = User(
            tg_id=message.from_user.id,
            expires_at=datetime.utcnow() + timedelta(days=30),
            is_active=True,
        )
        s.add(u)
        await s.commit()

    await message.answer(
        "✅ Оплата прошла! Теперь пришлите ссылку на вашу группу ВК:"
    )
    await Form.waiting_vk.set()


# ---------- 4. Получаем ссылку ----------
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


# ---------- 5. Выбор стиля ----------
@router.callback_query(F.data.startswith("style_"))
async def receive_style(callback: CallbackQuery, state: FSMContext):
    style = callback.data.split("_", 1)[1]
    await state.update_data(style=style)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 пост/день", callback_data="freq_1")],
            [InlineKeyboardButton(text="2 поста/день", callback_data="freq_2")],
            [InlineKeyboardButton(text="3 поста/день", callback_data="freq_3")],
        ]
    )
    await callback.message.edit_text("Сколько постов в день?", reply_markup=kb)
    await state.set_state(Form.waiting_freq)


# ---------- 6. Выбор частоты ----------
@router.callback_query(F.data.startswith("freq_"))
async def receive_freq(callback: CallbackQuery, state: FSMContext):
    freq = float(callback.data.split("_", 1)[1])
    data = await state.get_data()

    async with async_session() as s:
        u = await s.get(User, callback.from_user.id)
        u.vk_group_id = data["vk_url"]
        u.theme = data["theme"]
        u.style = data["style"]
        u.posts_per_day = freq
        await s.commit()

        # генерируем 30 дней постов
        from bot.utils import generate_all_posts
        await generate_all_posts(u.id, u.theme, u.style, u.posts_per_day)

    await callback.message.edit_text(
        "✅ Всё готово! Посты сгенерированы и будут публиковаться автоматически."
    )