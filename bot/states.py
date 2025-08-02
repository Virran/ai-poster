# bot/states.py
from aiogram.fsm.state import StatesGroup, State  # Верно для aiogram 3.x

class Form(StatesGroup):
    waiting_vk = State()
    waiting_style = State()
    waiting_freq = State()
    waiting_keywords = State()
   # добавьте следующую строку
    waiting_access_token = State()