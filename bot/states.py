from aiogram.fsm.state import StatesGroup, State
class Form(StatesGroup):
    waiting_vk = State()
    waiting_theme = State()
    waiting_style = State()
    waiting_freq = State()