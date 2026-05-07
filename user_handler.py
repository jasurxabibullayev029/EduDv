import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import RegisterStates
from keyboards import (
    main_menu_keyboard, phone_keyboard, courses_keyboard,
    course_actions_keyboard, back_to_courses_keyboard
)
from database import get_user, create_user, get_user_courses, has_active_course
from config import COURSES

logger = logging.getLogger(__name__)
user_router = Router()



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



@user_router.message(F.text == "📚 Kurslar")
async def courses_menu(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if not user:
        await msg.answer("❗ Avval ro'yxatdan o'ting. /start")
        return
    if user['is_banned']:
        await msg.answer("🚫 Akkauntingiz bloklangan.")
        return

    # Clear any payment state if user wants to go back to courses
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    await msg.answer(
        "📚 <b>Bizning kurslar:</b>\n\nQuyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=courses_keyboard()
    )


@user_router.message(F.text == "👤 Mening profilim")
async def my_profile(msg: Message):
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
async def contact_info(msg: Message):
    await msg.answer(
        "📞 <b>Bog'lanish ma'lumotlari:</b>\n\n"
        "👨‍💼 Admin: @jasurdv\n"
        "📱 Telefon: +998 95 182 22 23\n"
        "🕐 Ish vaqti: 09:00 - 22:00",
        parse_mode="HTML"
    )



@user_router.callback_query(F.data == "back_courses")
async def back_to_courses(cb: CallbackQuery):
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
        reply_markup=course_actions_keyboard(course_key, has_course)
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


@user_router.callback_query(F.data.startswith("videos_"))
async def view_course_videos(cb: CallbackQuery):
    course_key = cb.data.split("_", 1)[1]
    if course_key not in COURSES:
        await cb.answer("Kurs topilmadi!")
        return

    has_course = await has_active_course(cb.from_user.id, course_key)
    if not has_course:
        await cb.answer("Siz bu kursga yozilmagansiz!")
        return

    import json
    import aiosqlite
    async with aiosqlite.connect("edubot.db") as db:
        async with db.execute("SELECT videos FROM courses WHERE key=?", (course_key,)) as cur:
            row = await cur.fetchone()
    
    videos = json.loads(row[0] if row and row[0] else "[]")
    course_name = COURSES[course_key]['name']

    if not videos:
        await cb.message.edit_text(
            f"📚 <b>{course_name}</b>\n\n"
            "❌ Hali bu kursda videolar yo'q.",
            parse_mode="HTML",
            reply_markup=back_to_courses_keyboard()
        )
        return

    builder = InlineKeyboardBuilder()
    for i, video in enumerate(videos):
        title = video.get('title', f'Video {i+1}')
        builder.button(text=f"🎬 {title}", callback_data=f"play_{course_key}_{i}")
    builder.button(text="🔙 Orqaga", callback_data="back_courses")
    builder.adjust(1)

    total_duration = sum(v.get('duration', 0) for v in videos)
    minutes = total_duration // 60

    await cb.message.edit_text(
        f"📚 <b>{course_name}</b>\n"
        f"🎬 Jami: <b>{len(videos)} ta dars</b> ({minutes} daqiqa)\n\n"
        f"Darsni tanlang:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@user_router.callback_query(F.data.startswith("play_"))
async def play_video(cb: CallbackQuery):
    parts = cb.data.split("_")
    course_key = parts[1]
    video_index = int(parts[2])

    has_course = await has_active_course(cb.from_user.id, course_key)
    if not has_course:
        await cb.answer("Siz bu kursga yozilmagansiz!")
        return

    import json
    import aiosqlite
    async with aiosqlite.connect("edubot.db") as db:
        async with db.execute("SELECT videos FROM courses WHERE key=?", (course_key,)) as cur:
            row = await cur.fetchone()
    
    videos = json.loads(row[0] if row and row[0] else "[]")
    
    if video_index >= len(videos):
        await cb.answer("Video topilmadi!")
        return

    video = videos[video_index]
    video_title = video.get('title', f'Video {video_index + 1}')
    video_file_id = video.get('file_id')
    course_name = COURSES[course_key]['name']

    if video_file_id:
        await cb.message.answer_video(
            video_file_id,
            caption=f"📚 <b>{course_name}</b>\n🎬 <b>{video_title}</b>",
            parse_mode="HTML"
        )
    else:
        await cb.answer("Video fayli topilmadi!")
    
    await cb.answer()
