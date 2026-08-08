import aiosqlite
from typing import Optional, Dict, Any

DB_PATH = "bot_users.sqlite3"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
  telegram_id INTEGER PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  phone_number TEXT NOT NULL,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

class BotDB:
    def __init__(self, path: str = DB_PATH):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(CREATE_TABLE_SQL)
            await db.commit()

    async def upsert_user_tokens(
        self,
        telegram_id: int,
        first_name: str,
        last_name: str,
        phone_number: str,
        access_token: str,
        refresh_token: str,
        updated_at_iso: str,
    ):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO users (telegram_id, first_name, last_name, phone_number, access_token, refresh_token, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                  first_name=excluded.first_name,
                  last_name=excluded.last_name,
                  phone_number=excluded.phone_number,
                  access_token=excluded.access_token,
                  refresh_token=excluded.refresh_token,
                  updated_at=excluded.updated_at
                """,
                (telegram_id, first_name, last_name, phone_number, access_token, refresh_token, updated_at_iso),
            )
            await db.commit()

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def delete_user(self, telegram_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM users WHERE telegram_id=?", (telegram_id,))
            await db.commit()

STAFF_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS staff_sessions (
  telegram_id INTEGER PRIMARY KEY,
  username TEXT NOT NULL,
  full_name TEXT NOT NULL,
  organization_name TEXT NOT NULL,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

async def _staff_init(self):
    async with aiosqlite.connect(self.path) as db:
        await db.execute(STAFF_TABLE_SQL)
        await db.commit()

async def _upsert_staff_session(self, telegram_id, username, full_name, organization_name, access_token, refresh_token, updated_at_iso):
    async with aiosqlite.connect(self.path) as db:
        await db.execute("""
            INSERT INTO staff_sessions (telegram_id, username, full_name, organization_name, access_token, refresh_token, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
              username=excluded.username, full_name=excluded.full_name,
              organization_name=excluded.organization_name,
              access_token=excluded.access_token, refresh_token=excluded.refresh_token,
              updated_at=excluded.updated_at
        """, (telegram_id, username, full_name, organization_name, access_token, refresh_token, updated_at_iso))
        await db.commit()

async def _get_staff_session(self, telegram_id):
    async with aiosqlite.connect(self.path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM staff_sessions WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def _delete_staff_session(self, telegram_id):
    async with aiosqlite.connect(self.path) as db:
        await db.execute("DELETE FROM staff_sessions WHERE telegram_id=?", (telegram_id,))
        await db.commit()

BotDB.staff_init = _staff_init
BotDB.upsert_staff_session = _upsert_staff_session
BotDB.get_staff_session = _get_staff_session
BotDB.delete_staff_session = _delete_staff_session
