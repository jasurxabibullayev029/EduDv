import aiosqlite
import logging
import json
from datetime import datetime
from config import COURSES

DB_PATH = "edubot.db"
logger = logging.getLogger(__name__)


def _extract_price_from_description(description: str) -> str:
    for line in description.split('\n'):
        if '💰 Narxi:' in line:
            return line.split('💰 Narxi:')[1].strip()
    return "50,000 so'm/oy"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                age INTEGER,
                phone TEXT,
                registered_at TEXT DEFAULT (datetime('now')),
                is_banned INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_key TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                activated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, course_key)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER NOT NULL,
                course_key TEXT NOT NULL,
                amount INTEGER DEFAULT 50000,
                check_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                processed_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_state (
                id INTEGER PRIMARY KEY DEFAULT 1,
                password TEXT DEFAULT 'vfx.jasur',
                wrong_attempts INTEGER DEFAULT 0,
                ban_until TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                key TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                videos TEXT DEFAULT '[]'
            )
        """)
        try:
            await db.execute("ALTER TABLE courses ADD COLUMN price TEXT DEFAULT '50,000 so''m/oy'")
        except aiosqlite.OperationalError:
            pass
        await db.execute("""
            INSERT OR IGNORE INTO admin_state (id, password) VALUES (1, 'vfx.jasur')
        """)
        for course_key, course_data in COURSES.items():
            await db.execute(
                "INSERT OR IGNORE INTO courses (key, name, description, price) VALUES (?, ?, ?, ?)",
                (
                    course_key,
                    course_data.get('name', course_key),
                    course_data.get('description', ''),
                    _extract_price_from_description(course_data.get('description', '')),
                )
            )

        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT key, name, description, price FROM courses WHERE is_active=1") as cur:
            rows = await cur.fetchall()
        if rows:
            COURSES.clear()
            for row in rows:
                price = row["price"] or "50,000 so'm/oy"
                desc = row["description"] or ""
                if "💰 Narxi:" not in desc:
                    desc = f"{desc}\n\n💰 Narxi: {price}" if desc else f"💰 Narxi: {price}"
                COURSES[row["key"]] = {
                    "name": row["name"] or row["key"],
                    "description": desc
                }
        await db.commit()
    logger.info("Ma'lumotlar bazasi tayyor ✅")



async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()


async def create_user(user_id: int, username: str, full_name: str, age: int, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, full_name, age, phone) VALUES (?,?,?,?,?)",
            (user_id, username, full_name, age, phone)
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY registered_at DESC") as cur:
            return await cur.fetchall()


async def delete_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM user_courses WHERE user_id=?", (user_id,))
        await db.execute("DELETE FROM payments WHERE user_id=?", (user_id,))
        await db.commit()


async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
        await db.commit()



async def get_user_courses(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_courses WHERE user_id=? AND is_active=1", (user_id,)
        ) as cur:
            return await cur.fetchall()


async def activate_user_course(user_id: int, course_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_courses (user_id, course_key, is_active) VALUES (?,?,1)",
            (user_id, course_key)
        )
        await db.commit()


async def deactivate_user_course(user_id: int, course_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE user_courses SET is_active=0 WHERE user_id=? AND course_key=?",
            (user_id, course_key)
        )
        await db.commit()


async def has_active_course(user_id: int, course_key: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM user_courses WHERE user_id=? AND course_key=? AND is_active=1",
            (user_id, course_key)
        ) as cur:
            return await cur.fetchone() is not None



async def create_payment(user_id: int, course_key: str, check_file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payments (user_id, course_key, check_file_id, status) VALUES (?,?,?,'pending')",
            (user_id, course_key, check_file_id)
        )
        await db.commit()
        return cur.lastrowid


async def get_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)) as cur:
            return await cur.fetchone()


async def update_payment_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status=?, processed_at=datetime('now') WHERE id=?",
            (status, payment_id)
        )
        await db.commit()


async def get_today_revenue():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT SUM(amount) FROM payments WHERE status='approved' AND date(created_at)=date('now')"
        ) as cur:
            result = await cur.fetchone()
            return result[0] or 0


async def get_monthly_revenue():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT COALESCE(SUM(amount), 0) as total 
            FROM payments 
            WHERE status='approved' 
            AND created_at >= date('now', 'start of month')
        """) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def update_course_price(course_key: str, price: str):
    """Update only course price."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE courses SET price=? WHERE key=?",
            (price, course_key)
        )
        await db.commit()


async def get_course_price(course_key: str):
    """Get course price from database"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT price FROM courses WHERE key=?", (course_key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def sync_courses_to_db():
    """Sync all courses from config to database"""
    async with aiosqlite.connect(DB_PATH) as db:
        for course_key, course_data in COURSES.items():
            existing_price = await get_course_price(course_key)
            if not existing_price:
                description = course_data.get('description', '')
                price = "50,000 so'm/oy"
                for line in description.split('\n'):
                    if '💰 Narxi:' in line:
                        price = line.split('💰 Narxi:')[1].strip()
                        break
            else:
                price = existing_price
            
            await db.execute(
                "INSERT OR REPLACE INTO courses (key, name, description, price) VALUES (?, ?, ?, ?)",
                (course_key, course_data.get('name', course_key), 
             course_data.get('description', ''), price)
            )
        await db.commit()


async def create_course(course_key: str, name: str, description: str, price: str):
    """Create new course in database and memory config."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO courses (key, name, description, price) VALUES (?, ?, ?, ?)",
            (course_key, name, description, price)
        )
        await db.commit()
    
    COURSES[course_key] = {
        "name": name,
        "description": description
    }


async def delete_course(course_key: str):
    """Delete course and related links from DB and memory config."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM user_courses WHERE course_key=?", (course_key,))
        await db.execute("DELETE FROM payments WHERE course_key=?", (course_key,))
        await db.execute("DELETE FROM courses WHERE key=?", (course_key,))
        await db.commit()
    
    if course_key in COURSES:
        del COURSES[course_key]


async def get_all_courses_from_db():
    """Get all courses from database"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM courses ORDER BY rowid DESC") as cur:
            return await cur.fetchall()


async def get_course_videos(course_key: str) -> list:
    """Get saved course videos list from DB."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT videos FROM courses WHERE key=?", (course_key,)) as cur:
            row = await cur.fetchone()
    if not row or not row[0]:
        return []
    try:
        return json.loads(row[0])
    except Exception:
        return []


async def get_total_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            result = await cur.fetchone()
            return result[0] or 0


async def get_pending_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC") as cur:
            return await cur.fetchall()



async def get_admin_state():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admin_state WHERE id=1") as cur:
            return await cur.fetchone()


async def update_admin_password(new_password: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE admin_state SET password=? WHERE id=1", (new_password,))
        await db.commit()


async def set_admin_ban(ban_until: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE admin_state SET ban_until=?, wrong_attempts=0 WHERE id=1",
            (ban_until,)
        )
        await db.commit()


async def increment_wrong_attempts():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE admin_state SET wrong_attempts=wrong_attempts+1 WHERE id=1")
        await db.commit()


async def reset_wrong_attempts():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE admin_state SET wrong_attempts=0, ban_until=NULL WHERE id=1")
        await db.commit()
