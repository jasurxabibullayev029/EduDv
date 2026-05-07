import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import PaymentStates
from keyboards import back_to_courses_keyboard
from database import create_payment, get_user, has_active_course, get_course_price
from config import COURSES, CARD_NUMBER, CARD_OWNER, ADMIN_ID

logger = logging.getLogger(__name__)
payment_router = Router()


@payment_router.callback_query(F.data.startswith("buy_"))
async def buy_course(cb: CallbackQuery, state: FSMContext):
    course_key = cb.data.split("_", 1)[1]
    if course_key not in COURSES:
        await cb.answer("Kurs topilmadi!")
        return

    user = await get_user(cb.from_user.id)
    if not user:
        await cb.answer("❗ Avval ro'yxatdan o'ting!")
        return

    has_course = await has_active_course(cb.from_user.id, course_key)
    if has_course:
        await cb.answer("✅ Siz bu kursga allaqachon yozilgansiz!", show_alert=True)
        return

    course = COURSES[course_key]
    await state.update_data(course_key=course_key, course_name=course['name'])
    await state.set_state(PaymentStates.waiting_check)

    db_price = await get_course_price(course_key)
    if db_price:
        current_price = db_price.replace('/oy', '')
    else:
        description = course.get('description', '')
        current_price = "50,000 so'm"
        for line in description.split('\n'):
            if '💰 Narxi:' in line:
                current_price = line.split('💰 Narxi:')[1].strip().replace('/oy', '')
                break

    await cb.message.edit_text(
        f"💳 <b>{course['name']} — To'lov</b>\n\n"
        f"Narxi: <b>{current_price}</b>\n\n"
        f"Quyidagi karta raqamiga to'lov qiling:\n\n"
        f"🏦 Karta: <code>{CARD_NUMBER}</code>\n"
        f"👤 Egasi: <b>{CARD_OWNER}</b>\n"
        f"💵 Miqdor: <b>{current_price}</b>\n\n"
        f"✅ To'lov qilgandan so'ng <b>chek (screenshot)</b> yuboring.\n"
        f"⚠️ <b>Cheksiz to'lov qabul qilinmaydi!</b>",
        parse_mode="HTML",
        reply_markup=back_to_courses_keyboard()
    )


@payment_router.message(PaymentStates.waiting_check, F.photo)
async def receive_check(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    course_key = data.get("course_key")
    course_name = data.get("course_name", "Noma'lum")

    if not course_key:
        await msg.answer("❗ Xatolik! Qaytadan urinib ko'ring.")
        await state.clear()
        return

    photo_id = msg.photo[-1].file_id
    payment_id = await create_payment(msg.from_user.id, course_key, photo_id)

    user = await get_user(msg.from_user.id)
    username = f"@{msg.from_user.username}" if msg.from_user.username else "yo'q"

    try:
        from keyboards import admin_payment_keyboard
        db_price = await get_course_price(course_key)
        if db_price:
            current_price = db_price.replace('/oy', '')
        else:
            course = COURSES.get(course_key, {})
            description = course.get('description', '')
            current_price = "50,000 so'm"
            for line in description.split('\n'):
                if '💰 Narxi:' in line:
                    current_price = line.split('💰 Narxi:')[1].strip().replace('/oy', '')
                    break

        admin_text = (
            f"💰 <b>Yangi to'lov keldi!</b>\n\n"
            f"🔢 To'lov ID: <b>#{payment_id}</b>\n"
            f"👤 Foydalanuvchi: <b>{user['full_name'] if user else 'Noma\'lum'}</b>\n"
            f"🆔 Telegram ID: <code>{msg.from_user.id}</code>\n"
            f"📱 Username: {username}\n"
            f"📚 Kurs: <b>{course_name}</b>\n"
            f"💵 Miqdor: <b>{current_price}</b>"
        )
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=admin_text,
            parse_mode="HTML",
            reply_markup=admin_payment_keyboard(payment_id, msg.from_user.id, course_key)
        )
    except Exception as e:
        logger.error(f"Admin ga xabar yuborishda xatolik: {e}")

    await state.clear()
    await msg.answer(
        f"✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        f"📚 Kurs: <b>{course_name}</b>\n"
        f"🔢 To'lov ID: <b>#{payment_id}</b>\n\n"
        f"⏳ Admin tekshirib, tez orada kurs ochib beriladi.\n"
        f"Sabr qiling, iltimos!",
        parse_mode="HTML"
    )


@payment_router.message(PaymentStates.waiting_check)
async def wrong_check_format(msg: Message):
    await msg.answer(
        "❗ Iltimos, to'lov chekini <b>rasm (screenshot)</b> ko'rinishida yuboring!\n\n"
        "📸 To'lov ekranini suratga olib yuboring.",
        parse_mode="HTML"
    )
