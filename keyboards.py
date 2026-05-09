from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import COURSES


def main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📚 Kurslar")
    builder.button(text="👤 Mening profilim")
    builder.button(text="📞 Bog'lanish")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def phone_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Telefon raqamni yuborish", request_contact=True)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def courses_keyboard():
    builder = InlineKeyboardBuilder()
    for key, course in COURSES.items():
        builder.button(text=course["name"], callback_data=f"course_{key}")
    builder.adjust(1)
    return builder.as_markup()


def course_actions_keyboard(course_key: str, has_course: bool = False):
    builder = InlineKeyboardBuilder()
    if has_course:
        builder.button(text="🎬 Darslarni ko'rish", callback_data=f"watch_{course_key}")
    else:
        builder.button(text="💳 Kurs sotib olish", callback_data=f"buy_{course_key}")
    builder.button(text="❓ Nima bu kurs?", callback_data=f"info_{course_key}")
    builder.button(text="🔙 Orqaga", callback_data="back_courses")
    builder.adjust(1)
    return builder.as_markup()


def back_to_courses_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Kurslarga qaytish", callback_data="back_courses")
    return builder.as_markup()


def course_videos_keyboard(course_key: str, videos: list):
    builder = InlineKeyboardBuilder()
    for idx, _ in enumerate(videos, start=1):
        builder.button(text=f"📺 {idx}-qism", callback_data=f"watchpart_{course_key}_{idx-1}")
    builder.button(text="🔙 Orqaga", callback_data=f"course_{course_key}")
    builder.adjust(2)
    return builder.as_markup()


def cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Bekor qilish")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ─── ADMIN KEYBOARDS ──────────────────────────────────────────────────────────

def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Foydalanuvchilar", callback_data="admin_users")
    builder.button(text="📊 Statistika", callback_data="admin_stats")
    builder.button(text="💰 Kutayotgan to'lovlar", callback_data="admin_payments")
    builder.button(text="📚 Kurslarni boshqarish", callback_data="admin_courses")
    builder.button(text="🗄 DB fileni yuklash", callback_data="admin_db_backup")
    builder.button(text="🔐 Parolni o'zgartirish", callback_data="admin_change_pass")
    builder.adjust(2, 1, 1, 1, 1)
    return builder.as_markup()


def admin_payment_keyboard(payment_id: int, user_id: int, course_key: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ To'lovni qabul qilish",
        callback_data=f"approve_{payment_id}_{user_id}_{course_key}"
    )
    builder.button(
        text="❌ Rad etish",
        callback_data=f"reject_{payment_id}_{user_id}_{course_key}"
    )
    builder.adjust(1)
    return builder.as_markup()


def admin_users_keyboard(users):
    builder = InlineKeyboardBuilder()
    for user in users[:20]:  # Max 20 ta ko'rsatamiz
        name = user['full_name'] or f"ID:{user['user_id']}"
        builder.button(text=f"👤 {name}", callback_data=f"auser_{user['user_id']}")
    builder.button(text="🔙 Admin panel", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def admin_user_actions_keyboard(user_id: int, is_banned: int):
    builder = InlineKeyboardBuilder()
    if is_banned:
        builder.button(text="✅ Banlni olib tashlash", callback_data=f"unban_{user_id}")
    else:
        builder.button(text="🚫 Banlash", callback_data=f"ban_{user_id}")
    builder.button(text="🗑 O'chirish", callback_data=f"deluser_{user_id}")
    builder.button(text="📚 Kurslarini boshqarish", callback_data=f"usercourses_{user_id}")
    builder.button(text="🔙 Orqaga", callback_data="admin_users")
    builder.adjust(1)
    return builder.as_markup()


def admin_user_courses_keyboard(user_id: int, user_courses: list):
    builder = InlineKeyboardBuilder()
    active_keys = [uc['course_key'] for uc in user_courses]
    for key, course in COURSES.items():
        status = "✅" if key in active_keys else "❌"
        builder.button(
            text=f"{status} {course['name']}",
            callback_data=f"togglecourse_{user_id}_{key}"
        )
    builder.button(text="🔙 Orqaga", callback_data=f"auser_{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def admin_courses_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi kurs qo'shish", callback_data="admin_add_course")
    for key, course in COURSES.items():
        builder.button(text=course["name"], callback_data=f"admincourse_{key}")
    builder.button(text="🔙 Admin panel", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def admin_course_manage_keyboard(course_key: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Narxni o'zgartirish", callback_data=f"courseprice_{course_key}")
    builder.button(text="🎬 Video qo'shish", callback_data=f"addvideo_{course_key}")
    builder.button(text="📋 Videolarni boshqarish", callback_data=f"listvideos_{course_key}")
    builder.button(text="🗑 Kursni o'chirish", callback_data=f"delcourse_{course_key}")
    builder.button(text="🔙 Orqaga", callback_data="admin_courses")
    builder.adjust(1)
    return builder.as_markup()


def admin_videos_list_keyboard(course_key: str, videos: list):
    """Har bir video uchun nomi + o'chirish tugmasi"""
    builder = InlineKeyboardBuilder()
    for i, v in enumerate(videos):
        title = v.get('title', f'Video {i+1}')
        date = v.get('added_at', '')
        # Video nomini ko'rsatish (truncate if long)
        display = f"🎬 {i+1}. {title[:25]}" + (f" ({date})" if date else "")
        builder.button(text=display, callback_data=f"vidinfo_{course_key}_{i}")
        builder.button(text="🗑 O'chirish", callback_data=f"delvideo_{course_key}_{i}")
    builder.button(text="➕ Video qo'shish", callback_data=f"addvideo_{course_key}")
    builder.button(text="🔙 Orqaga", callback_data=f"admincourse_{course_key}")
    builder.adjust(2)  # har qator: [video nomi] [o'chirish]
    # oxirgi 2 tugma alohida qator
    return builder.as_markup()


def admin_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Admin panel", callback_data="admin_back")
    return builder.as_markup()