from aiogram.fsm.state import State, StatesGroup

class Booking(StatesGroup):
    service = State(); master = State(); date = State(); time = State(); name = State(); phone = State(); comment = State(); confirm = State()

class ReviewState(StatesGroup):
    text = State()

class AdminState(StatesGroup):
    date = State(); add_service = State(); add_master = State(); add_slot = State(); portfolio_photo = State(); cancel_appointment = State()
