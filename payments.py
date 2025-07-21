from yookassa import Configuration, Payment
from yookassa.domain.models.currency import Currency
import uuid

Configuration.account_id = int(os.getenv("YOOKASSA_SHOP_ID"))
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

def create_payment(amount: int, description: str, tg_id: int):
    """
    Возвращает (payment_id, confirmation_url)
    confirmation_url уже ведёт обратно в бота
    """
    payment = Payment.create({
        "amount":     {"value": f"{amount}.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            # клиент после оплаты вернётся в чат бота
            "return_url": f"https://t.me/ii_poster_bot?start=pay_{tg_id}"
        },
        "capture": True,
        "description": description,
        "metadata": {"tg_id": str(tg_id)}   # пригодится для webhook (опц.)
    }, uuid.uuid4())
    return payment.id, payment.confirmation.confirmation_url