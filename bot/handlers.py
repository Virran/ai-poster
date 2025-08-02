from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import os
import requests
from yookassa import Payment
from yookassa.configuration import Configuration

# Фиксированный токен VK API для теста
VK_API_TOKEN = "vk1.a.cByhC3scVxdfbznjG1qJ_0xXfVJ8ckIMNqjxvzBNcHO3LVqnduPMDqGsWzT9oHgi_m2b7AEdI9JTmvfVOVJmatYqyApRGsECGjtta0iIfxEDwNpD3_dg8IAmyINlVxFwQgsDU2ozVv0wcNvCIZ76-4qiiOJgzHBy0daVSn-PhX8GSiDGbL7vQcCXVRa81PeAk2xs252zelQBALYBCWAtFw"

# Фиксированный ID группы VK для теста (должен начинаться с -)
VK_GROUP_ID = "-231921005"  # Замените на реальный ID вашей группы

Configuration.account_id = int(os.getenv("YOOKASSA_SHOP_ID"))
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

router = Router()

# /start
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    text = (
        "👋 Привет! Я тестовый бот для публикации в VK.\n"
        "После оплаты я сделаю тестовый пост в указанную группу."
    )
    payment_id, url = create_payment(1, "Тестовая оплата", message.from_user.id)  # Сумма 1 рубль для теста
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 1 ₽ (тест)", url=url)],
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
        # Используем фиксированные данные для теста
        post_text = f"Тест бота {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ID: {callback.from_user.id}"
        
        # Публикуем пост в VK
        post_result = post_to_vk(VK_GROUP_ID, VK_API_TOKEN, post_text)
        
        if post_result.get("response"):
            await callback.message.edit_text(
                f"✅ Оплата прошла! Тестовый пост опубликован:\n"
                f"Текст: {post_text}\n"
                f"Группа: vk.com/public{VK_GROUP_ID[1:]}"
            )
        else:
            error_msg = post_result.get("error", {}).get("error_msg", "Неизвестная ошибка")
            await callback.message.edit_text(
                f"❌ Не удалось опубликовать пост:\n{error_msg}"
            )
    else:
        await callback.answer(
            "⏳ Платёж ещё не подтверждён. Попробуйте позже.",
            show_alert=True,
        )

def post_to_vk(group_id: str, access_token: str, post_text: str):
    url = "https://api.vk.com/method/wall.post"
    params = {
        "access_token": access_token,
        "v": "5.131",
        "owner_id": group_id,
        "message": post_text,
        "from_group": 1
    }
    try:
        response = requests.post(url, params=params)
        return response.json()
    except Exception as e:
        return {"error": {"error_msg": str(e)}}