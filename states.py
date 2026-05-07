from aiogram.fsm.state import State, StatesGroup


class RegisterStates(StatesGroup):
    waiting_name = State()
    waiting_surname = State()
    waiting_age = State()
    waiting_phone = State()


class PaymentStates(StatesGroup):
    waiting_check = State()


class AdminStates(StatesGroup):
    waiting_password = State()
    waiting_new_password = State()
    waiting_new_password_confirm = State()
    waiting_video_title = State()
    waiting_video = State()
    waiting_video_course = State()
    waiting_course_key = State()
    waiting_course_name = State()
    waiting_course_description = State()
    waiting_course_price = State()
    waiting_new_course_price = State()