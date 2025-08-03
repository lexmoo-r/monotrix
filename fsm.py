from aiogram.fsm.state import StatesGroup, State

class AddFant(StatesGroup):
    waiting_for_fant = State()
