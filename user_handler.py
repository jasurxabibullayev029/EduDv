import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from states import RegisterStates
from keyboards import (
    main_menu_keyboard, phone_keyboard, courses_keyboard,
    course_actions_keyboard, back_to_courses_keyboard
)
from database import get_user, create_user, get_user_courses, has_active_course, get_course_videos
from config import COURSES

logger = logging.getLogger(__name__)
user_router = Router()


# ─── /start ───────────────────────────────────────────────────────────────────

@user_router.message(CommandStart())
async def start_handler(msg: Message, state: FSMContext):
    await state.clear()
    user = await get_user(msg.from_user.id)

    if user and not user['is_banned']:
        await msg.answer(
            f"👋 Salom, <b>{user['full_name']}</b>!\n\n"
            f"🎓 <b>EduDv</b> online darslarga xush kelibsiz!\n\n"
            f"Quyidagi bo'limlardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )
    elif user and user['is_banned']:
        await msg.answer("🚫 Sizning akkauntingiz bloklangan. Admin bilan bog'laning.")
    else:
        await msg.answer(
            "👋 Salom!\n\n"
            "🎓 <b>EduDv</b> online darslarga xush kelibsiz!\n\n"
            "Botdan foydalanish uchun avval ro'yxatdan o'tishingiz kerak.\n\n"
            "📝 Ism va familyangizni kiriting (masalan: <i>Jasur Abdullayev</i>):",
            parse_mode="HTML"
        )
        await state.set_state(RegisterStates.waiting_name)


# ─── REGISTRATION ─────────────────────────────────────────────────────────────

@user_router.message(RegisterStates.waiting_name)
async def reg_name(msg: Message, state: FSMContext):
    text = msg.text.strip()
    parts = text.split()
    if len(parts) < 2:
        await msg.answer("❗ Iltimos, ism va familyangizni to'liq kiriting.\nMasalan: <b>Jasur Abdullayev</b>", parse_mode="HTML")
        return
    await state.update_data(full_name=text)
    await msg.answer("📅 Yoshingizni kiriting (masalan: <b>20</b>):", parse_mode="HTML")
    await state.set_state(RegisterStates.waiting_age)


@user_router.message(RegisterStates.waiting_age)
async def reg_age(msg: Message, state: FSMContext):
    if not msg.text.isdigit() or not (10 <= int(msg.text) <= 80):
        await msg.answer("❗ Iltimos, to'g'ri yosh kiriting (10-80 oralig'ida):")
        return
    await state.update_data(age=int(msg.text))
    await msg.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard()
    )
    await state.set_state(RegisterStates.waiting_phone)


@user_router.message(RegisterStates.waiting_phone, F.contact)
async def reg_phone(msg: Message, state: FSMContext):
    phone = msg.contact.phone_number
    data = await state.get_data()

    await create_user(
        user_id=msg.from_user.id,
        username=msg.from_user.username,
        full_name=data['full_name'],
        age=data['age'],
        phone=phone
    )
    await state.clear()

    await msg.answer(
        f"✅ <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n"
        f"👤 Ism: <b>{data['full_name']}</b>\n"
        f"📅 Yosh: <b>{data['age']}</b>\n"
        f"📱 Telefon: <b>{phone}</b>\n\n"
        f"🎓 Endi kurslarimizni ko'rishingiz mumkin!",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )


@user_router.message(RegisterStates.waiting_phone)
async def reg_phone_text(msg: Message):
    await msg.answer("❗ Iltimos, tugmani bosib telefon raqamingizni yuboring:", reply_markup=phone_keyboard())


# ─── MAIN MENU ────────────────────────────────────────────────────────────────

@user_router.message(F.text == "📚 Kurslar")
async def courses_menu(msg: Message, state: FSMContext):
    await state.clear()
    user = await get_user(msg.from_user.id)
    if not user:
        await msg.answer("❗ Avval ro'yxatdan o'ting. /start")
        return
    if user['is_banned']:
        await msg.answer("🚫 Akkauntingiz bloklangan.")
        return

    await msg.answer(
        "📚 <b>Bizning kurslar:</b>\n\nQuyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=courses_keyboard()
    )


@user_router.message(F.text == "👤 Mening profilim")
async def my_profile(msg: Message, state: FSMContext):
    await state.clear()
    user = await get_user(msg.from_user.id)
    if not user:
        await msg.answer("❗ Avval ro'yxatdan o'ting. /start")
        return

    user_courses = await get_user_courses(msg.from_user.id)
    course_names = [COURSES[uc['course_key']]['name'] for uc in user_courses if uc['course_key'] in COURSES]

    courses_text = "\n".join([f"  • {name}" for name in course_names]) if course_names else "  Hali yo'q"

    await msg.answer(
        f"👤 <b>Mening profilim</b>\n\n"
        f"📛 Ism: <b>{user['full_name']}</b>\n"
        f"📅 Yosh: <b>{user['age']}</b>\n"
        f"📱 Telefon: <b>{user['phone']}</b>\n"
        f"📅 Ro'yxatdan o'tgan: <b>{user['registered_at'][:10]}</b>\n\n"
        f"📚 <b>Mening kurslarim:</b>\n{courses_text}",
        parse_mode="HTML"
    )


@user_router.message(F.text == "📞 Bog'lanish")
async def contact_info(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "📞 <b>Bog'lanish ma'lumotlari:</b>\n\n"
        "👨‍💼 Admin: @jasurdv\n"
        "📱 Telefon: +998 95 182 22 23\n"
        "🕐 Ish vaqti: 09:00 - 22:00",
        parse_mode="HTML"
    )


# ─── COURSE CALLBACKS ─────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "back_courses")
async def back_to_courses(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "📚 <b>Bizning kurslar:</b>\n\nQuyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=courses_keyboard()
    )


@user_router.callback_query(F.data.startswith("course_"))
async def course_selected(cb: CallbackQuery):
    course_key = cb.data.split("_", 1)[1]
    if course_key not in COURSES:
        await cb.answer("Kurs topilmadi!")
        return

    course = COURSES[course_key]
    has_course = await has_active_course(cb.from_user.id, course_key)

    status_text = "\n\n✅ <b>Siz bu kursga yozilgansiz!</b>" if has_course else ""

    await cb.message.edit_text(
        f"{course['name']}\n\n{status_text}",
        parse_mode="HTML",
        reply_markup=course_actions_keyboard(course_key, has_course=has_course)
    )


@user_router.callback_query(F.data.startswith("info_"))
async def course_info(cb: CallbackQuery):
    course_key = cb.data.split("_", 1)[1]
    if course_key not in COURSES:
        await cb.answer("Kurs topilmadi!")
        return

    course = COURSES[course_key]
    await cb.message.edit_text(
        f"<b>{course['name']}</b>\n\n{course['description']}",
        parse_mode="HTML",
        reply_markup=back_to_courses_keyboard()
    )


@user_router.callback_query(F.data.startswith("watch_"))
async def watch_course_videos(cb: CallbackQuery):
    course_key = cb.data.split("_", 1)[1]
    if course_key not in COURSES:
        await cb.answer("Kurs topilmadi!")
        return

    if not await has_active_course(cb.from_user.id, course_key):
        await cb.answer("❗ Avval kursni sotib oling.", show_alert=True)
        return

    videos = await get_course_videos(course_key)
    if not videos:
        await cb.answer("Hozircha videolar qo'shilmagan.", show_alert=True)
        return

    await cb.message.answer(
        f"🎬 <b>{COURSES[course_key]['name']}</b>\n"
        f"Jami darslar: <b>{len(videos)} ta</b>\n\n"
        f"Videolar yuborilmoqda...",
        parse_mode="HTML"
    )

    for idx, video in enumerate(videos, start=1):
        file_id = video.get("file_id")
        if not file_id:
            continue
        title = video.get("title", f"Dars {idx}")
        await cb.message.answer_video(
            video=file_id,
            caption=f"📘 <b>{title}</b>\nDars {idx}/{len(videos)}",
            parse_mode="HTML"
        )
