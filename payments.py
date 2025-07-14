import uuid, os
from yookassa import Configuration, Payment
from yookassa.domain.models.currency import Currency
Configuration.account_id = int(os.getenv("YOOKASSA_SHOP_ID"))
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

def create_payment(amount: int, description: str):
    payment = Payment.create({
        "amount": {"value": f"{amount}.00", "currency": Currency.RUB},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/YOUR_BOT"},
        "capture": True,
        "description": description,
    }, uuid.uuid4())
    return payment.id, payment.confirmation.confirmation_url