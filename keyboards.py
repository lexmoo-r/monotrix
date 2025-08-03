from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def stop_adding_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить добавление", callback_data="stop_adding")]
    ])
    return keyboard
