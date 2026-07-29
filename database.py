import os
from typing import Optional, List, Dict, Any

import aiosqlite
import asyncpg

from config import DATA_DIR, DB_PATH, DATABASE_URL

if DATABASE_URL is None:
    os.makedirs(DATA_DIR, exist_ok=True)

_db_pool: Optional[asyncpg.Pool] = None


def _use_postgres() -> bool:
    return DATABASE_URL is not None


async def init_db():
    global _db_pool
    if _use_postgres():
        _db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        async with _db_pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS appointments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    phone TEXT,
                    service TEXT NOT NULL,
                    doctor TEXT NOT NULL,
                    date DATE NOT NULL,
                    time TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_appointments_date_time
                ON appointments(date, time, doctor, status)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_appointments_user
                ON appointments(user_id, status)
                """
            )
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
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
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_appointments_date_time
                ON appointments(date, time, doctor, status)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_appointments_user
                ON appointments(user_id, status)
                """
            )
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
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO appointments
                (user_id, username, full_name, phone, service, doctor, date, time)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                user_id,
                username,
                full_name,
                phone,
                service,
                doctor,
                date,
                time,
            )
            return row["id"]

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
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM appointments
                WHERE user_id = $1 AND status = 'active' AND date >= CURRENT_DATE
                ORDER BY date, time
                """,
                user_id,
            )
            return [dict(row) for row in rows]

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
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM appointments WHERE id = $1",
                appointment_id,
            )
            return dict(row) if row else None

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM appointments WHERE id = ?",
            (appointment_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def cancel_appointment(appointment_id: int, user_id: Optional[int] = None) -> bool:
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            if user_id is not None:
                result = await conn.execute(
                    """
                    UPDATE appointments SET status = 'cancelled'
                    WHERE id = $1 AND user_id = $2 AND status = 'active'
                    """,
                    appointment_id,
                    user_id,
                )
            else:
                result = await conn.execute(
                    """
                    UPDATE appointments SET status = 'cancelled'
                    WHERE id = $1 AND status = 'active'
                    """,
                    appointment_id,
                )
            return int(result.split()[-1]) > 0

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
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM appointments
                WHERE doctor = $1 AND date = $2 AND time = $3 AND status = 'active'
                LIMIT 1
                """,
                doctor,
                date,
                time,
            )
            return row is not None

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
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT time FROM appointments
                WHERE doctor = $1 AND date = $2 AND status = 'active'
                """,
                doctor,
                date,
            )
            return [row["time"] for row in rows]

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
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM appointments
                WHERE status = 'active' AND date >= CURRENT_DATE
                ORDER BY date, time
                LIMIT $1
                """,
                limit,
            )
            return [dict(row) for row in rows]

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
    if _use_postgres():
        async with _db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM appointments
                WHERE date = $1 AND status = 'active'
                ORDER BY time
                """,
                date,
            )
            return [dict(row) for row in rows]

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
