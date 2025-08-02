# bot/states.py
from aiogram.fsm.states import StatesGroup, State

class Form(StatesGroup):
    waiting_vk = State()
    waiting_style = State()
    waiting_freq = State()
    waiting_keywords = State()
   # добавьте следующую строку
    waiting_access_token = State()