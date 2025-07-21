import os
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
from payments import create_payment
from yookassa import Payment  # pip install yookassa

router = Router()

# ---------- 1. /start ----------
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
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Купить подписку 990 ₽", callback_data="buy")]
        ]
    )
    await message.answer(text, reply_markup=kb)


# ---------- 2. Кнопка «Купить» ----------
@router.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    payment_id, url = create_payment(990, "Подписка AI-постер")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=url)],
            [
                InlineKeyboardButton(
                    text="✅ Проверить оплату", callback_data=f"check_{payment_id}"
                )
            ],
        ]
    )
    await callback.message.edit_text(
        "Для продолжения оплатите подписку 👇", reply_markup=kb
    )


# ---------- 3. Проверка оплаты ----------
@router.callback_query(F.data.startswith("check_"))
async def check_payment(callback: CallbackQuery, state: FSMContext):
    payment_id = callback.data.split("_", 1)[1]
    payment = Payment.find_one(payment_id)

    if payment.status == "succeeded":
        # сохраняем пользователя
        async with async_session() as s:
            u = User(
                tg_id=callback.from_user.id,
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True,
            )
            s.add(u)
            await s.commit()

        await callback.message.edit_text(
            "✅ Оплата прошла! Теперь пришлите ссылку на вашу группу ВК:",
            reply_markup=None,
        )
        await state.set_state(Form.waiting_vk)
    else:
        await callback.answer(
            "⏳ Платёж ещё не подтверждён. Попробуйте позже.",
            show_alert=True,
        )


# ---------- 4. Получаем ссылку на VK ----------
@router.message(Form.waiting_vk)
async def receive_vk(message: Message, state: FSMContext):
    await state.update_data(vk_url=message.text)
    await message.answer(
        "Отлично! Теперь укажите тематику паблика (или просто нажмите «Далее»):"
    )
    await state.set_state(Form.waiting_theme)

# --- продолжение после receive_vk ---
@router.message(Form.waiting_theme)
async def receive_theme(message: Message, state: FSMContext):
    await state.update_data(theme=message.text)
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
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 пост/день", callback_data="freq_1")],
            [InlineKeyboardButton(text="2 поста/день", callback_data="freq_2")],
            [InlineKeyboardButton(text="3 поста/день", callback_data="freq_3")],
        ]
    )
    await callback.message.edit_text("Сколько постов в день?", reply_markup=kb)
    await state.set_state(Form.waiting_freq)


@router.callback_query(F.data.startswith("freq_"))
async def receive_freq(callback: CallbackQuery, state: FSMContext):
    freq = float(callback.data.split("_", 1)[1])
    data = await state.get_data()

    # сохраняем пользователя
    async with async_session() as s:
        u = await s.get(User, callback.from_user.id)
        u.theme = data["theme"]
        u.style = style = data["style"]
        u.posts_per_day = freq
        await s.commit()

    # генерируем 30 дней постов
    await generate_all_posts(u.id, u.theme, u.style, freq)

    await callback.message.edit_text(
        "✅ Всё готово! Посты сгенерированы и будут публиковаться автоматически."
    )

    