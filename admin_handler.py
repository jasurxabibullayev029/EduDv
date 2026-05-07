import logging
import json
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import AdminStates
from keyboards import (
    admin_main_keyboard, admin_users_keyboard, admin_user_actions_keyboard,
    admin_user_courses_keyboard, admin_courses_keyboard,
    admin_course_manage_keyboard, admin_back_keyboard
)
from database import (
    get_admin_state, update_admin_password, set_admin_ban,
    increment_wrong_attempts, reset_wrong_attempts,
    get_all_users, get_user, delete_user, ban_user, unban_user,
    get_user_courses, activate_user_course, deactivate_user_course,
    get_payment, update_payment_status, activate_user_course,
    get_pending_payments, get_today_revenue, get_monthly_revenue, get_total_users,
    update_course_price, get_course_price, create_course, delete_course, get_all_courses_from_db
)
from config import COURSES, ADMIN_ID

logger = logging.getLogger(__name__)
admin_router = Router()

password_change_attempts = {}



@admin_router.message(Command("jasur"))
async def admin_enter(msg: Message, state: FSMContext):
    admin_state = await get_admin_state()

    if admin_state['ban_until']:
        ban_time = datetime.fromisoformat(admin_state['ban_until'])
        if datetime.now() < ban_time:
            remaining = ban_time - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            await msg.answer(
                f"🚫 <b>Kirish bloklangan!</b>\n\n"
                f"⏰ Qolgan vaqt: {hours}s {mins}d\n\n"
                f"Noto'g'ri parol ko'p marta kiritildi.",
                parse_mode="HTML"
            )
            return
        else:
            await reset_wrong_attempts()

    await msg.answer(
        "🔐 <b>Admin Panel</b>\n\n"
        "Kirish uchun parolni kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_password)


@admin_router.message(AdminStates.waiting_password)
async def check_admin_password(msg: Message, state: FSMContext):
    admin_state = await get_admin_state()
    entered = msg.text.strip()

    if entered == admin_state['password']:
        await reset_wrong_attempts()
        await state.set_state(None)
        await msg.answer(
            "✅ <b>Admin panelga xush kelibsiz!</b>\n\n"
            "👇 Quyidagi bo'limlardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=admin_main_keyboard()
        )
    else:
        attempts = admin_state['wrong_attempts'] + 1
        await increment_wrong_attempts()

        if attempts >= 2:
            ban_until = (datetime.now() + timedelta(hours=24)).isoformat()
            await set_admin_ban(ban_until)
            await state.clear()
            await msg.answer(
                "🚫 <b>24 soatlik ban!</b>\n\n"
                "Noto'g'ri parol 2 marta kiritildi.\n"
                "24 soatdan so'ng urinib ko'ring.",
                parse_mode="HTML"
            )
        else:
            remaining = 2 - attempts
            await msg.answer(
                f"❌ Noto'g'ri parol!\n\n"
                f"⚠️ Qolgan urinish: <b>{remaining}</b>\n"
                f"Yana bir bor kiriting:",
                parse_mode="HTML"
            )



@admin_router.callback_query(F.data == "admin_back")
async def admin_back(cb: CallbackQuery):
    await cb.message.edit_text(
        "🏠 <b>Admin Panel</b>\n\nBo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard()
    )



@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(cb: CallbackQuery):
    total_users = await get_total_users()
    today_rev = await get_today_revenue()
    monthly_rev = await get_monthly_revenue()
    pending = await get_pending_payments()

    await cb.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n\n"
        f"💰 <b>Daromad:</b>\n"
        f"  📅 Bugun: <b>{today_rev:,} so'm</b>\n"
        f"  📆 Bu oy: <b>{monthly_rev:,} so'm</b>\n\n"
        f"⏳ Kutayotgan to'lovlar: <b>{len(pending)}</b>",
        parse_mode="HTML",
        reply_markup=admin_back_keyboard()
    )



@admin_router.callback_query(F.data == "admin_users")
async def admin_users(cb: CallbackQuery):
    users = await get_all_users()
    if not users:
        await cb.message.edit_text(
            "👥 Hali foydalanuvchi yo'q.",
            reply_markup=admin_back_keyboard()
        )
        return

    await cb.message.edit_text(
        f"👥 <b>Foydalanuvchilar</b> ({len(users)} ta)\n\nBirini tanlang:",
        parse_mode="HTML",
        reply_markup=admin_users_keyboard(users)
    )


@admin_router.callback_query(F.data.startswith("auser_"))
async def admin_user_detail(cb: CallbackQuery):
    user_id = int(cb.data.split("_")[1])
    user = await get_user(user_id)
    if not user:
        await cb.answer("Foydalanuvchi topilmadi!")
        return

    user_courses = await get_user_courses(user_id)
    course_names = [COURSES.get(uc['course_key'], {}).get('name', uc['course_key']) for uc in user_courses]
    courses_text = ", ".join(course_names) if course_names else "Yo'q"
    ban_status = "🚫 Banlangan" if user['is_banned'] else "✅ Faol"

    await cb.message.edit_text(
        f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
        f"📛 Ism: <b>{user['full_name']}</b>\n"
        f"📅 Yosh: <b>{user['age']}</b>\n"
        f"📱 Telefon: <b>{user['phone']}</b>\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"📅 Ro'yxat: <b>{user['registered_at'][:10]}</b>\n"
        f"📊 Holat: {ban_status}\n"
        f"📚 Kurslar: <b>{courses_text}</b>",
        parse_mode="HTML",
        reply_markup=admin_user_actions_keyboard(user_id, user['is_banned'])
    )


@admin_router.callback_query(F.data.startswith("ban_"))
async def admin_ban_user(cb: CallbackQuery, bot: Bot):
    user_id = int(cb.data.split("_")[1])
    await ban_user(user_id)
    await cb.answer("✅ Foydalanuvchi banlandi!")
    try:
        await bot.send_message(user_id, "🚫 Akkauntingiz bloklandi. Admin bilan bog'laning.")
    except:
        pass
    # Refresh
    user = await get_user(user_id)
    await cb.message.edit_reply_markup(
        reply_markup=admin_user_actions_keyboard(user_id, user['is_banned'])
    )


@admin_router.callback_query(F.data.startswith("unban_"))
async def admin_unban_user(cb: CallbackQuery, bot: Bot):
    user_id = int(cb.data.split("_")[1])
    await unban_user(user_id)
    await cb.answer("✅ Ban olib tashlandi!")
    try:
        await bot.send_message(user_id, "✅ Akkauntingizdan ban olib tashlandi!")
    except:
        pass
    user = await get_user(user_id)
    await cb.message.edit_reply_markup(
        reply_markup=admin_user_actions_keyboard(user_id, user['is_banned'])
    )


@admin_router.callback_query(F.data.startswith("deluser_"))
async def admin_delete_user(cb: CallbackQuery):
    user_id = int(cb.data.split("_")[1])
    await delete_user(user_id)
    await cb.answer("🗑 Foydalanuvchi o'chirildi!")
    users = await get_all_users()
    await cb.message.edit_text(
        f"👥 <b>Foydalanuvchilar</b> ({len(users)} ta)\n\nBirini tanlang:",
        parse_mode="HTML",
        reply_markup=admin_users_keyboard(users)
    )


@admin_router.callback_query(F.data.startswith("usercourses_"))
async def admin_user_courses(cb: CallbackQuery):
    user_id = int(cb.data.split("_")[1])
    user = await get_user(user_id)
    user_courses = await get_user_courses(user_id)
    await cb.message.edit_text(
        f"📚 <b>{user['full_name'] if user else user_id}</b> — Kurslar boshqaruvi\n\n"
        f"✅ = faol | ❌ = nofaol\nBosib holat o'zgartiring:",
        parse_mode="HTML",
        reply_markup=admin_user_courses_keyboard(user_id, user_courses)
    )


@admin_router.callback_query(F.data.startswith("togglecourse_"))
async def toggle_user_course(cb: CallbackQuery, bot: Bot):
    parts = cb.data.split("_")
    user_id = int(parts[1])
    course_key = parts[2]

    from database import has_active_course
    is_active = await has_active_course(user_id, course_key)

    if is_active:
        await deactivate_user_course(user_id, course_key)
        await cb.answer(f"❌ Kurs o'chirildi")
        try:
            course_name = COURSES.get(course_key, {}).get('name', course_key)
            await bot.send_message(user_id, f"❌ <b>{course_name}</b> kursi o'chirildi.", parse_mode="HTML")
        except:
            pass
    else:
        await activate_user_course(user_id, course_key)
        await cb.answer(f"✅ Kurs faollashtirildi")
        try:
            course_name = COURSES.get(course_key, {}).get('name', course_key)
            await bot.send_message(user_id, f"✅ <b>{course_name}</b> kursi faollashtirildi! O'qishingizni boshlashingiz mumkin.", parse_mode="HTML")
        except:
            pass

    user_courses = await get_user_courses(user_id)
    user = await get_user(user_id)
    await cb.message.edit_reply_markup(
        reply_markup=admin_user_courses_keyboard(user_id, user_courses)
    )



@admin_router.callback_query(F.data == "admin_payments")
async def admin_payments_list(cb: CallbackQuery):
    payments = await get_pending_payments()
    if not payments:
        await cb.message.edit_text(
            "💰 Hozircha kutayotgan to'lovlar yo'q.",
            reply_markup=admin_back_keyboard()
        )
        return

    text = f"⏳ <b>Kutayotgan to'lovlar ({len(payments)} ta):</b>\n\n"
    for p in payments[:10]:
        text += f"#{p['id']} — Kurs: {COURSES.get(p['course_key'], {}).get('name', p['course_key'])} | User: {p['user_id']}\n"

    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_keyboard())


@admin_router.callback_query(F.data.startswith("approve_"))
async def approve_payment(cb: CallbackQuery, bot: Bot):
    parts = cb.data.split("_")
    payment_id = int(parts[1])
    user_id = int(parts[2])
    course_key = parts[3]

    await update_payment_status(payment_id, "approved")
    await activate_user_course(user_id, course_key)

    course_name = COURSES.get(course_key, {}).get('name', course_key)

    await cb.answer("✅ To'lov qabul qilindi!")
    await cb.message.edit_caption(
        caption=cb.message.caption + f"\n\n✅ <b>TO'LOV QABUL QILINDI</b> — Admin: {cb.from_user.full_name}",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            user_id,
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"✅ To'lovingiz qabul qilindi!\n"
            f"📚 <b>{course_name}</b> kursi faollashtirildi!\n\n"
            f"O'qishingizni boshlashingiz mumkin. Omad! 💪",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"User ga xabar yuborishda xatolik: {e}")


@admin_router.callback_query(F.data.startswith("reject_"))
async def reject_payment(cb: CallbackQuery, bot: Bot):
    parts = cb.data.split("_")
    payment_id = int(parts[1])
    user_id = int(parts[2])
    course_key = parts[3]

    await update_payment_status(payment_id, "rejected")

    await cb.answer("❌ To'lov rad etildi!")
    await cb.message.edit_caption(
        caption=cb.message.caption + f"\n\n❌ <b>TO'LOV RAD ETILDI</b> — Admin: {cb.from_user.full_name}",
        parse_mode="HTML"
    )

    try:
        course_name = COURSES.get(course_key, {}).get('name', course_key)
        await bot.send_message(
            user_id,
            f"❌ <b>To'lovda xatolik!</b>\n\n"
            f"📚 Kurs: <b>{course_name}</b>\n\n"
            f"To'lovingiz qabul qilinmadi. Admin bilan bog'laning.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"User ga xabar yuborishda xatolik: {e}")



@admin_router.callback_query(F.data == "admin_courses")
async def admin_courses(cb: CallbackQuery):
    await cb.message.edit_text(
        "📚 <b>Kurslar boshqaruvi</b>\n\nKursni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_courses_keyboard()
    )


@admin_router.callback_query(F.data.startswith("admincourse_"))
async def admin_course_detail(cb: CallbackQuery):
    course_key = cb.data.split("_", 1)[1]
    course = COURSES.get(course_key)
    if not course:
        await cb.answer("Kurs topilmadi!")
        return

    db_price = await get_course_price(course_key)
    if db_price:
        current_price = db_price
    else:
        description = course.get('description', '')
        current_price = "50,000 so'm/oy" 
        for line in description.split('\n'):
            if '💰 Narxi:' in line:
                current_price = line.split('💰 Narxi:')[1].strip()
                break

    await cb.message.edit_text(
        f"📚 <b>{course['name']}</b>\n\n"
        f"💰 Joriy narx: <b>{current_price}</b>\n\n"
        f"Nima qilmoqchisiz?",
        parse_mode="HTML",
        reply_markup=admin_course_manage_keyboard(course_key)
    )


async def _get_course_videos(course_key: str) -> list:
    """DB dan kurs videolarini olish"""
    import aiosqlite
    async with aiosqlite.connect("edubot.db") as db:
        async with db.execute("SELECT videos FROM courses WHERE key=?", (course_key,)) as cur:
            row = await cur.fetchone()
    return json.loads(row[0] if row and row[0] else "[]")


async def _save_course_videos(course_key: str, videos: list):
    """DB ga kurs videolarini saqlash"""
    import aiosqlite
    async with aiosqlite.connect("edubot.db") as db:
        async with db.execute("SELECT key FROM courses WHERE key=?", (course_key,)) as cur:
            exists = await cur.fetchone()
        if exists:
            await db.execute("UPDATE courses SET videos=? WHERE key=?", (json.dumps(videos), course_key))
        else:
            await db.execute(
                "INSERT INTO courses (key, name, videos) VALUES (?,?,?)",
                (course_key, COURSES.get(course_key, {}).get('name', course_key), json.dumps(videos))
            )
        await db.commit()



@admin_router.callback_query(F.data.startswith("editprice_"))
async def edit_price_start(cb: CallbackQuery, state: FSMContext):
    course_key = cb.data.split("_", 1)[1]
    await state.update_data(price_course_key=course_key)
    await state.set_state(AdminStates.waiting_new_price)
    course = COURSES.get(course_key, {})
    
    description = course.get('description', '')
    current_price = "50,000 so'm/oy" 
    for line in description.split('\n'):
        if '💰 Narxi:' in line:
            current_price = line.split('💰 Narxi:')[1].strip()
            break
    
    await cb.message.edit_text(
        f"💰 <b>{course.get('name', course_key)}</b> — Narxni tahrirlash\n\n"
        f"Joriy narx: <b>{current_price}</b>\n\n"
        f"<b>Yangi narxni kiriting:</b>\n"
        f"<i>(masalan: 450,000 so'm/oy)</i>",
        parse_mode="HTML"
    )


@admin_router.callback_query(F.data.startswith("addvideo_"))
async def add_video_start(cb: CallbackQuery, state: FSMContext):
    course_key = cb.data.split("_", 1)[1]
    await state.update_data(video_course_key=course_key)
    await state.set_state(AdminStates.waiting_video_title)
    course = COURSES.get(course_key, {})
    await cb.message.edit_text(
        f"🎬 <b>{course.get('name', course_key)}</b> — Video qo'shish\n\n"
        f"<b>1-qadam:</b> Dars nomini yozing:\n"
        f"<i>(masalan: Dars 1 — HTML asoslari)</i>",
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.waiting_new_price)
async def receive_new_price(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=admin_main_keyboard())
        return
    
    new_price = msg.text.strip()
    if not new_price:
        await msg.answer("❌ Iltimos, narxni kiriting!")
        return
    
    data = await state.get_data()
    course_key = data.get("price_course_key")
    
    if not course_key:
        await msg.answer("❌ Xatolik! Qaytadan urinib ko'ring.")
        await state.clear()
        return
    
    course = COURSES.get(course_key)
    if not course:
        await msg.answer("❌ Kurs topilmadi!")
        await state.clear()
        return
    

    await update_course_price(course_key, new_price)
    
    old_description = course.get('description', '')
    lines = old_description.split('\n')
    new_description = []
    
    for line in lines:
        if '💰 Narxi:' in line:
            new_description.append(f"💰 Narxi: {new_price}")
        else:
            new_description.append(line)
    
    course['description'] = '\n'.join(new_description)
    
    await state.clear()
    course_name = course.get('name', course_key)
    await msg.answer(
        f"✅ <b>Narx muvaffaqiyatli o'zgartirildi!</b>\n\n"
        f"📚 Kurs: <b>{course_name}</b>\n"
        f"💰 Yangi narx: <b>{new_price}</b>",
        parse_mode="HTML",
        reply_markup=admin_back_keyboard()
    )


@admin_router.message(AdminStates.waiting_video_title)
async def receive_video_title(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=admin_main_keyboard())
        return
    if not msg.text:
        await msg.answer("❌ Iltimos, faqat matn yuboring!")
        return
    await state.update_data(video_title=msg.text.strip())
    await msg.answer(
        f"✅ Nom: <b>{msg.text.strip()}</b>\n\n"
        f"<b>2-qadam:</b> Endi video faylni yuboring:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_video)


@admin_router.message(AdminStates.waiting_video, F.video)
async def receive_admin_video(msg: Message, state: FSMContext):
    data = await state.get_data()
    course_key = data.get("video_course_key")
    title = data.get("video_title", f"Dars {msg.message_id}")

    video_data = {
        "file_id": msg.video.file_id,
        "title": title,
        "duration": msg.video.duration,
        "added_at": datetime.now().isoformat()[:10]
    }

    videos = await _get_course_videos(course_key)
    videos.append(video_data)
    await _save_course_videos(course_key, videos)

    await state.clear()
    course_name = COURSES.get(course_key, {}).get('name', course_key)
    await msg.answer(
        f"✅ <b>Video muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📚 Kurs: <b>{course_name}</b>\n"
        f"🎬 Dars: <b>{title}</b>\n"
        f"📊 Jami videolar: <b>{len(videos)} ta</b>",
        parse_mode="HTML",
        reply_markup=admin_back_keyboard()
    )


@admin_router.message(AdminStates.waiting_video)
async def wrong_video_format(msg: Message):
    await msg.answer("❗ Iltimos, <b>video fayl</b> yuboring (mp4, avi va h.k.):", parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("listvideos_"))
async def list_videos(cb: CallbackQuery):
    from keyboards import admin_videos_list_keyboard
    course_key = cb.data.split("_", 1)[1]
    course_name = COURSES.get(course_key, {}).get('name', course_key)
    videos = await _get_course_videos(course_key)

    if not videos:
        from keyboards import admin_course_manage_keyboard as cmk
        await cb.message.edit_text(
            f"📚 <b>{course_name}</b>\n\n"
            f"🎬 Hali video qo'shilmagan.\n\n"
            f"Video qo'shish uchun tugmani bosing:",
            parse_mode="HTML",
            reply_markup=cmk(course_key)
        )
        return

    total_dur = sum(v.get('duration', 0) for v in videos)
    mins = total_dur // 60

    await cb.message.edit_text(
        f"📚 <b>{course_name}</b>\n"
        f"🎬 Jami: <b>{len(videos)} ta video</b> ({mins} daqiqa)\n\n"
        f"Video tanlang yoki o'chiring:",
        parse_mode="HTML",
        reply_markup=admin_videos_list_keyboard(course_key, videos)
    )


@admin_router.callback_query(F.data.startswith("vidinfo_"))
async def video_info(cb: CallbackQuery):
    parts = cb.data.split("_")
    course_key = parts[1]
    idx = int(parts[2])
    videos = await _get_course_videos(course_key)

    if idx >= len(videos):
        await cb.answer("Video topilmadi!")
        return

    v = videos[idx]
    dur = v.get('duration', 0)
    await cb.answer(
        f"🎬 {v.get('title', 'Video')}\n"
        f"📅 {v.get('added_at', '')}\n"
        f"⏱ {dur//60}:{dur%60:02d}",
        show_alert=True
    )


@admin_router.callback_query(F.data.startswith("delvideo_"))
async def delete_video(cb: CallbackQuery):
    from keyboards import admin_videos_list_keyboard
    parts = cb.data.split("_")
    course_key = parts[1]
    idx = int(parts[2])

    videos = await _get_course_videos(course_key)
    if idx >= len(videos):
        await cb.answer("Video topilmadi!")
        return

    deleted_title = videos[idx].get('title', 'Video')
    videos.pop(idx)
    await _save_course_videos(course_key, videos)

    await cb.answer(f"🗑 '{deleted_title}' o'chirildi!")

    course_name = COURSES.get(course_key, {}).get('name', course_key)
    if not videos:
        from keyboards import admin_course_manage_keyboard as cmk
        await cb.message.edit_text(
            f"📚 <b>{course_name}</b>\n\n"
            f"🎬 Barcha videolar o'chirildi.\n\n"
            f"Yangi video qo'shish uchun tugmani bosing:",
            parse_mode="HTML",
            reply_markup=cmk(course_key)
        )
    else:
        total_dur = sum(v.get('duration', 0) for v in videos)
        mins = total_dur // 60
        await cb.message.edit_text(
            f"📚 <b>{course_name}</b>\n"
            f"🎬 Jami: <b>{len(videos)} ta video</b> ({mins} daqiqa)\n\n"
            f"Video tanlang yoki o'chiring:",
            parse_mode="HTML",
            reply_markup=admin_videos_list_keyboard(course_key, videos)
        )



@admin_router.callback_query(F.data == "admin_change_pass")
async def change_pass_start(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    if user_id not in password_change_attempts:
        password_change_attempts[user_id] = 0

    if password_change_attempts[user_id] >= 3:
        await cb.message.edit_text(
            "🚫 <b>Parol o'zgartirish imkoniyati tugadi!</b>\n\n"
            "3 marta urinish limiti oshib ketdi.",
            parse_mode="HTML",
            reply_markup=admin_back_keyboard()
        )
        return

    remaining = 3 - password_change_attempts[user_id]
    await cb.message.edit_text(
        f"🔐 <b>Parolni o'zgartirish</b>\n\n"
        f"⚠️ Qolgan urinish: <b>{remaining}/3</b>\n\n"
        f"Yangi parolni kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_new_password)


@admin_router.message(AdminStates.waiting_new_password)
async def receive_new_password(msg: Message, state: FSMContext):
    new_pass = msg.text.strip()
    if len(new_pass) < 4:
        await msg.answer("❗ Parol kamida 4 ta belgi bo'lishi kerak. Qaytadan kiriting:")
        return

    await state.update_data(new_password=new_pass)
    await msg.answer("🔁 Yangi parolni tasdiqlash uchun qaytadan kiriting:")
    await state.set_state(AdminStates.waiting_new_password_confirm)


@admin_router.callback_query(F.data == "admin_add_course")
async def add_course_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_course_name)
    await cb.message.edit_text(
        "➕ <b>Yangi kurs qo'shish</b>\n\n"
        f"<b>1-qadam:</b> Kurs kalit nomini kiriting (inglizcha):\n"
        f"<i>(masalan: mobile_dev, python_basic)</i>",
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.waiting_course_name)
async def receive_course_name(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=admin_main_keyboard())
        return
    
    course_key = msg.text.strip().lower().replace(" ", "_")
    if not course_key or len(course_key) < 3:
        await msg.answer("❌ Iltimos, kamida 3 ta belgidan iborat kalit nomi kiriting:")
        return
    
    if course_key in COURSES:
        await msg.answer(f"❌ '{course_key}' kaliti allaqachon mavjud! Boshqa nom tanlang:")
        return
    
    await state.update_data(course_key=course_key)
    await state.set_state(AdminStates.waiting_course_description)
    await msg.answer(
        f"✅ Kalit: <b>{course_key}</b>\n\n"
        f"<b>2-qadam:</b> Kurs nomini kiriting:\n"
        f"<i>(masalan: 📱 Mobil Dasturlash)</i>",
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.waiting_course_description)
async def receive_course_description(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=admin_main_keyboard())
        return
    
    course_name = msg.text.strip()
    if not course_name or len(course_name) < 5:
        await msg.answer("❌ Iltimos, to'liq kurs nomi kiriting:")
        return
    
    await state.update_data(course_name=course_name)
    await state.set_state(AdminStates.waiting_course_price)
    await msg.answer(
        f"✅ Nomi: <b>{course_name}</b>\n\n"
        f"<b>3-qadam:</b> Kurs narxini kiriting:\n"
        f"<i>(masalan: 150,000 so'm/oy, 500,000 so'm)</i>",
        parse_mode="HTML"
    )




@admin_router.message(AdminStates.waiting_course_price)
async def receive_course_price(msg: Message, state: FSMContext):
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌ Bekor qilindi.", reply_markup=admin_main_keyboard())
        return
    
    price = msg.text.strip()
    if not price:
        await msg.answer("❌ Iltimos, kurs narxini kiriting:")
        return
    
    data = await state.get_data()
    course_key = data.get("course_key")
    course_name = data.get("course_name")
    
    description = (
        f"{course_name} kursi.\n\n"
        f"📚 Nima o'rganasiz:\n"
        f"• Kurs bo'yicha ma'lumotlar\n"
        f"• Amaliy mashqlar\n"
        f"• Loyihalar\n\n"
        f"💰 Narxi: {price}"
    )
    
    await create_course(course_key, course_name, description, price)
    
    await state.clear()
    await msg.answer(
        f"✅ <b>Kurs muvaffaqiyatli qo'shildi!</b>\n\n"
        f"🔑 Kalit: <b>{course_key}</b>\n"
        f"📚 Nomi: <b>{course_name}</b>\n"
        f"💰 Narx: <b>{price}</b>\n\n"
        f"Endi kurs narxini o'zgartirishingiz mumkin!",
        parse_mode="HTML",
        reply_markup=admin_back_keyboard()
    )


@admin_router.callback_query(F.data == "admin_delete_course")
async def delete_course_start(cb: CallbackQuery):
    courses = await get_all_courses_from_db()
    if not courses:
        await cb.answer("O'chirish uchun kurs topilmadi!")
        return
    
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.button(
            text=f"🗑 {course['name']}", 
            callback_data=f"delete_confirm_{course['key']}"
        )
    builder.button(text="🔙 Orqaga", callback_data="admin_back")
    builder.adjust(1)
    
    await cb.message.edit_text(
        "🗑 <b>Kurs o'chirish</b>\n\n"
        "O'chirish uchun kursni tanlang:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@admin_router.callback_query(F.data.startswith("delete_confirm_"))
async def delete_course_confirm(cb: CallbackQuery):
    course_key = cb.data.split("_", 2)[2]
    course = COURSES.get(course_key)
    
    if not course:
        await cb.answer("Kurs topilmadi!")
        return
    
    await delete_course(course_key)
    await cb.answer(f"✅ {course['name']} o'chirildi!")
    
    courses = await get_all_courses_from_db()
    if not courses:
        await cb.message.edit_text(
            "🗑 <b>Barcha kurslar o'chirildi!</b>\n\n"
            "Yangi kurs qo'shishingiz mumkin.",
            parse_mode="HTML",
            reply_markup=admin_back_keyboard()
        )
        return
    
    builder = InlineKeyboardBuilder()
    for remaining_course in courses:
        builder.button(
            text=f"🗑 {remaining_course['name']}", 
            callback_data=f"delete_confirm_{remaining_course['key']}"
        )
    builder.button(text="🔙 Orqaga", callback_data="admin_back")
    builder.adjust(1)
    
    await cb.message.edit_text(
        f"✅ <b>{course['name']}</b> o'chirildi!\n\n"
        "Qolgan kurslar:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@admin_router.message(AdminStates.waiting_new_password_confirm)
async def confirm_new_password(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    data = await state.get_data()
    new_pass = data.get("new_password")

    if msg.text.strip() != new_pass:
        if user_id not in password_change_attempts:
            password_change_attempts[user_id] = 0
        password_change_attempts[user_id] += 1

        remaining = 3 - password_change_attempts[user_id]
        if remaining <= 0:
            await state.clear()
            await msg.answer(
                "🚫 <b>Parol o'zgartirish bloklandi!</b>\n\nKo'p marta noto'g'ri kiritildi.",
                parse_mode="HTML",
                reply_markup=admin_back_keyboard()
            )
        else:
            await msg.answer(
                f"❌ Parollar mos kelmadi!\n\n"
                f"⚠️ Qolgan urinish: <b>{remaining}/3</b>\n\n"
                f"Yangi parolni yana kiriting:",
                parse_mode="HTML"
            )
            await state.set_state(AdminStates.waiting_new_password)
        return

    await update_admin_password(new_pass)
    password_change_attempts[user_id] = 0
    await state.clear()
    await msg.answer(
        "✅ <b>Parol muvaffaqiyatli o'zgartirildi!</b>",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard()
    )