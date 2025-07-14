from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def styles_kb():
    styles = ["Деловой", "Экспертный", "Дружелюбный", "Ироничный"]
    kb = [[InlineKeyboardButton(text=s, callback_data=f"style_{s}")] for s in styles]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def freq_kb():
    kb = [[InlineKeyboardButton(text=f"{i} постов/день", callback_data=f"freq_{i}")] for i in (1,2,3,4)]
    return InlineKeyboardMarkup(inline_keyboard=kb)