import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = "clinic.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                service TEXT NOT NULL,
                doctor TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_date_time 
            ON appointments(date, time, doctor, status)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_user 
            ON appointments(user_id, status)
        """)
        await db.commit()


async def add_appointment(
    user_id: int,
    username: Optional[str],
    full_name: str,
    phone: str,
    service: str,
    doctor: str,
    date: str,
    time: str,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO appointments 
            (user_id, username, full_name, phone, service, doctor, date, time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, full_name, phone, service, doctor, date, time),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_appointments(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM appointments 
            WHERE user_id = ? AND status = 'active' AND date >= date('now')
            ORDER BY date, time
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_appointment_by_id(appointment_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM appointments WHERE id = ?",
            (appointment_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def cancel_appointment(appointment_id: int, user_id: Optional[int] = None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id is not None:
            cursor = await db.execute(
                """
                UPDATE appointments SET status = 'cancelled' 
                WHERE id = ? AND user_id = ? AND status = 'active'
                """,
                (appointment_id, user_id),
            )
        else:
            cursor = await db.execute(
                """
                UPDATE appointments SET status = 'cancelled' 
                WHERE id = ? AND status = 'active'
                """,
                (appointment_id,),
            )
        await db.commit()
        return cursor.rowcount > 0


async def is_slot_taken(doctor: str, date: str, time: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT 1 FROM appointments 
            WHERE doctor = ? AND date = ? AND time = ? AND status = 'active'
            LIMIT 1
            """,
            (doctor, date, time),
        )
        row = await cursor.fetchone()
        return row is not None


async def get_booked_slots(doctor: str, date: str) -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT time FROM appointments 
            WHERE doctor = ? AND date = ? AND status = 'active'
            """,
            (doctor, date),
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_all_active_appointments(limit: int = 50) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM appointments 
            WHERE status = 'active' AND date >= date('now')
            ORDER BY date, time
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_appointments_by_date(date: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM appointments 
            WHERE date = ? AND status = 'active'
            ORDER BY time
            """,
            (date,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
